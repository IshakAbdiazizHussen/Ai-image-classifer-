"""Dataset split generation/loading and the PyTorch Dataset used for
training, validation, and test.

Split behaviour (constraints.md rules 1-5):
  - The split is generated once per config (keyed by dataset dir, class
    list, ratios, and seed) and persisted as a manifest under
    `dataset.splits_dir`. Re-running against the same config reuses the
    existing manifest instead of regenerating it, so the same image never
    silently moves between splits across runs.
  - Splitting is stratified per class and shuffled with the configured
    seed, so it's deterministic and reproducible.
  - Malformed files (unreadable as an image) are excluded from the split
    and reported, never silently included.
  - Augmentation transforms are only ever applied to the train split;
    val/test use identical, deterministic preprocessing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Any

import torch
from PIL import Image, UnidentifiedImageError
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from ml.preprocessing import IMAGENET_MEAN, IMAGENET_STD, build_preprocessing_spec

SPLIT_NAMES = ("train", "val", "test")


@dataclass
class SplitEntry:
    path: str
    label: str


@dataclass
class Manifest:
    seed: int
    classes: list[str]
    split_ratios: dict[str, float]
    splits: dict[str, list[SplitEntry]]
    skipped_files: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "classes": self.classes,
            "split_ratios": self.split_ratios,
            "splits": {
                name: [{"path": e.path, "label": e.label} for e in entries]
                for name, entries in self.splits.items()
            },
            "skipped_files": self.skipped_files,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Manifest":
        return Manifest(
            seed=data["seed"],
            classes=data["classes"],
            split_ratios=data["split_ratios"],
            splits={
                name: [SplitEntry(**e) for e in entries]
                for name, entries in data["splits"].items()
            },
            skipped_files=data.get("skipped_files", []),
        )


def _manifest_path(splits_dir: Path) -> Path:
    return Path(splits_dir) / "manifest.json"


def _is_readable_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except (UnidentifiedImageError, OSError):
        return False


def _discover_class_files(raw_dir: Path, classes: list[str]) -> dict[str, list[Path]]:
    files_by_class: dict[str, list[Path]] = {}
    for class_name in classes:
        class_dir = raw_dir / class_name
        if not class_dir.is_dir():
            raise FileNotFoundError(
                f"Configured class '{class_name}' has no directory at {class_dir}"
            )
        files_by_class[class_name] = sorted(
            p for p in class_dir.iterdir() if p.is_file()
        )
    return files_by_class


def build_split(
    raw_dir: Path,
    classes: list[str],
    split_ratios: dict[str, float],
    seed: int,
) -> Manifest:
    """Generates a stratified, deterministic train/val/test split from
    `raw_dir` (ImageFolder layout: raw_dir/<class_name>/*). Every image is
    assigned to exactly one split; malformed images are excluded and
    reported in `manifest.skipped_files`."""
    files_by_class = _discover_class_files(raw_dir, classes)
    rng = Random(seed)

    splits: dict[str, list[SplitEntry]] = {name: [] for name in SPLIT_NAMES}
    skipped_files: list[str] = []

    for class_name, files in files_by_class.items():
        valid_files = []
        for path in files:
            if _is_readable_image(path):
                valid_files.append(path)
            else:
                skipped_files.append(str(path))

        rng.shuffle(valid_files)

        n = len(valid_files)
        n_train = int(n * split_ratios["train"])
        n_val = int(n * split_ratios["val"])
        # remainder goes to test so every valid file is assigned exactly once
        class_splits = {
            "train": valid_files[:n_train],
            "val": valid_files[n_train : n_train + n_val],
            "test": valid_files[n_train + n_val :],
        }
        for split_name, split_files in class_splits.items():
            splits[split_name].extend(
                SplitEntry(path=str(p), label=class_name) for p in split_files
            )

    # Shuffle within each split so batches aren't grouped by class.
    for split_name in SPLIT_NAMES:
        rng.shuffle(splits[split_name])

    return Manifest(
        seed=seed,
        classes=classes,
        split_ratios=split_ratios,
        splits=splits,
        skipped_files=skipped_files,
    )


def build_or_load_split(config: dict[str, Any]) -> Manifest:
    """Loads the persisted manifest if one already exists for this project;
    otherwise generates it and persists it. This is what makes the split
    "created once" (constraints.md rule 2) rather than regenerated on
    every training run."""
    splits_dir = Path(config["dataset"]["splits_dir"])
    manifest_path = _manifest_path(splits_dir)

    if manifest_path.is_file():
        with manifest_path.open("r") as f:
            return Manifest.from_json(json.load(f))

    manifest = build_split(
        raw_dir=Path(config["dataset"]["raw_dir"]),
        classes=config["dataset"]["classes"],
        split_ratios=config["dataset"]["split_ratios"],
        seed=config["seed"],
    )

    if manifest.skipped_files:
        print(
            f"WARNING: skipped {len(manifest.skipped_files)} unreadable file(s) "
            f"while building the split — see manifest.json's 'skipped_files'."
        )

    splits_dir.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w") as f:
        json.dump(manifest.to_json(), f, indent=2)

    return manifest


def get_transforms(image_size: int, split: str) -> transforms.Compose:
    """Train gets augmentation; val/test get identical, deterministic
    preprocessing only (constraints.md rule 3)."""
    normalize = transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)

    if split == "train":
        return transforms.Compose(
            [
                transforms.RandomResizedCrop(image_size, scale=(0.8, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
                transforms.ToTensor(),
                normalize,
            ]
        )
    if split in ("val", "test"):
        spec = build_preprocessing_spec(image_size)
        return transforms.Compose(
            [
                transforms.Resize(spec["resize"]),
                transforms.CenterCrop(spec["center_crop"]),
                transforms.ToTensor(),
                normalize,
            ]
        )
    raise ValueError(f"Unknown split '{split}', expected one of {SPLIT_NAMES}")


class ImageClassificationDataset(Dataset):
    def __init__(
        self,
        entries: list[SplitEntry],
        classes: list[str],
        transform: transforms.Compose,
    ) -> None:
        self.entries = entries
        self.class_to_idx = {name: idx for idx, name in enumerate(classes)}
        self.transform = transform

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        entry = self.entries[index]
        with Image.open(entry.path) as img:
            image = img.convert("RGB")
        tensor = self.transform(image)
        label_idx = self.class_to_idx[entry.label]
        return tensor, label_idx


def build_dataloaders(config: dict[str, Any]) -> tuple[dict[str, DataLoader], Manifest]:
    manifest = build_or_load_split(config)
    image_size = config["dataset"]["image_size"]
    batch_size = config["training"]["batch_size"]
    num_workers = config["training"]["num_workers"]

    dataloaders: dict[str, DataLoader] = {}
    for split_name in SPLIT_NAMES:
        dataset = ImageClassificationDataset(
            entries=manifest.splits[split_name],
            classes=manifest.classes,
            transform=get_transforms(image_size, split_name),
        )
        dataloaders[split_name] = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=(split_name == "train"),
            num_workers=num_workers,
        )

    return dataloaders, manifest
