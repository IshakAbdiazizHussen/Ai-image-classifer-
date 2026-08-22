"""Unit tests for the split-generation logic in ml/training/dataset.py.

Covers constraints.md rules 2 (deterministic, leakage-free splits) and 3
(augmentation on train only), per Phase 1's QA requirements.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ml.training.dataset import SPLIT_NAMES, build_split, get_transforms

CLASSES = ["cat", "dog"]
RATIOS = {"train": 0.6, "val": 0.2, "test": 0.2}
SEED = 42


def _make_raw_dir(tmp_path: Path, per_class: int = 20) -> Path:
    raw_dir = tmp_path / "raw"
    for class_name in CLASSES:
        class_dir = raw_dir / class_name
        class_dir.mkdir(parents=True)
        for i in range(per_class):
            img = Image.new("RGB", (8, 8), color=(i, i, i))
            img.save(class_dir / f"{class_name}_{i}.png")
    return raw_dir


def _all_paths(manifest) -> list[str]:
    return [entry.path for entries in manifest.splits.values() for entry in entries]


def test_no_image_appears_in_more_than_one_split(tmp_path: Path) -> None:
    raw_dir = _make_raw_dir(tmp_path)
    manifest = build_split(raw_dir, CLASSES, RATIOS, SEED)

    seen = set()
    for split_name in SPLIT_NAMES:
        split_paths = {entry.path for entry in manifest.splits[split_name]}
        assert not (split_paths & seen), f"overlap found involving split '{split_name}'"
        seen |= split_paths

    # every valid image was assigned to exactly one split
    assert len(seen) == len(CLASSES) * 20


def test_same_seed_produces_identical_manifest(tmp_path: Path) -> None:
    raw_dir = _make_raw_dir(tmp_path)

    manifest_a = build_split(raw_dir, CLASSES, RATIOS, SEED)
    manifest_b = build_split(raw_dir, CLASSES, RATIOS, SEED)

    for split_name in SPLIT_NAMES:
        entries_a = [(e.path, e.label) for e in manifest_a.splits[split_name]]
        entries_b = [(e.path, e.label) for e in manifest_b.splits[split_name]]
        assert entries_a == entries_b


def test_different_seed_can_produce_different_order(tmp_path: Path) -> None:
    raw_dir = _make_raw_dir(tmp_path)

    manifest_a = build_split(raw_dir, CLASSES, RATIOS, seed=1)
    manifest_b = build_split(raw_dir, CLASSES, RATIOS, seed=2)

    order_a = [e.path for e in manifest_a.splits["train"]]
    order_b = [e.path for e in manifest_b.splits["train"]]
    assert order_a != order_b


def test_malformed_file_is_excluded_and_reported(tmp_path: Path) -> None:
    raw_dir = _make_raw_dir(tmp_path, per_class=5)
    corrupt_path = raw_dir / "cat" / "cat_corrupt.png"
    corrupt_path.write_bytes(b"not a real image")

    manifest = build_split(raw_dir, CLASSES, RATIOS, SEED)

    assert str(corrupt_path) in manifest.skipped_files
    assert str(corrupt_path) not in _all_paths(manifest)


def test_stratified_split_keeps_ratio_per_class(tmp_path: Path) -> None:
    raw_dir = _make_raw_dir(tmp_path, per_class=10)
    manifest = build_split(raw_dir, CLASSES, RATIOS, SEED)

    for class_name in CLASSES:
        train_count = sum(
            1 for e in manifest.splits["train"] if e.label == class_name
        )
        assert train_count == 6  # 60% of 10


def test_train_transform_includes_augmentation() -> None:
    train_tf = get_transforms(image_size=224, split="train")
    transform_names = [type(t).__name__ for t in train_tf.transforms]
    assert "RandomHorizontalFlip" in transform_names
    assert "RandomResizedCrop" in transform_names


def test_val_and_test_transforms_have_no_augmentation() -> None:
    val_tf = get_transforms(image_size=224, split="val")
    test_tf = get_transforms(image_size=224, split="test")

    for tf in (val_tf, test_tf):
        transform_names = [type(t).__name__ for t in tf.transforms]
        assert "RandomHorizontalFlip" not in transform_names
        assert "RandomResizedCrop" not in transform_names
        assert "ColorJitter" not in transform_names

    val_names = [type(t).__name__ for t in val_tf.transforms]
    test_names = [type(t).__name__ for t in test_tf.transforms]
    assert val_names == test_names  # identical, deterministic preprocessing
