"""One-time helper: materializes a small public sample dataset (a CIFAR-10
subset) into the ImageFolder layout the rest of the pipeline expects
(`raw_dir/<class_name>/*.png`).

This script is NOT part of the reusable training pipeline — `dataset.py`
works against any ImageFolder-structured `raw_dir`. This is only here to
make Phase 1 runnable end-to-end without a real dataset on hand yet. Swap
`dataset.raw_dir` in the config to a real dataset directory in the same
layout and this script is no longer needed.

Per constraints.md rule 1, the materialized images are written under
`ml/data/raw/`, which is git-ignored — only this script and the config are
committed.

Usage:
    python -m ml.data.prepare_sample_dataset --config ml/configs/train_config.yaml --per-class 120
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from torchvision.datasets import CIFAR10

from ml.config import load_config


def materialize_cifar10_subset(raw_dir: Path, classes: list[str], per_class: int) -> None:
    """Downloads CIFAR-10 (once, cached) and writes `per_class` images per
    configured class into `raw_dir/<class_name>/`, skipping any class
    directory that's already populated so re-runs are cheap and idempotent.
    """
    download_dir = raw_dir.parent / ".cifar10_cache"
    download_dir.mkdir(parents=True, exist_ok=True)

    # CIFAR-10's fixed label order — the index a raw CIFAR-10 sample's label
    # refers to. This is CIFAR-10-specific and has nothing to do with the
    # project's own class list beyond matching names to indices below.
    cifar10_label_names = [
        "airplane", "automobile", "bird", "cat", "deer",
        "dog", "frog", "horse", "ship", "truck",
    ]
    missing = set(classes) - set(cifar10_label_names)
    if missing:
        raise ValueError(
            f"prepare_sample_dataset only knows how to source these classes "
            f"from CIFAR-10: {cifar10_label_names}. Unknown classes in "
            f"config: {sorted(missing)}"
        )

    dataset = CIFAR10(root=str(download_dir), train=True, download=True)

    per_class_counts = {name: 0 for name in classes}
    wanted_indices = {cifar10_label_names.index(name) for name in classes}

    for image, label_idx in dataset:
        class_name = cifar10_label_names[label_idx]
        if class_name not in per_class_counts:
            continue
        if per_class_counts[class_name] >= per_class:
            continue

        class_dir = raw_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        out_path = class_dir / f"{class_name}_{per_class_counts[class_name]:04d}.png"
        image.save(out_path)
        per_class_counts[class_name] += 1

        if all(count >= per_class for count in per_class_counts.values()):
            break

    shutil.rmtree(download_dir, ignore_errors=True)

    for class_name, count in per_class_counts.items():
        if count < per_class:
            raise RuntimeError(
                f"Only found {count}/{per_class} images for class "
                f"'{class_name}' — CIFAR-10 subset exhausted."
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("ml/configs/train_config.yaml")
    )
    parser.add_argument(
        "--per-class",
        type=int,
        default=120,
        help="Number of sample images to materialize per class.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    raw_dir = Path(config["dataset"]["raw_dir"])
    classes = config["dataset"]["classes"]

    already_populated = raw_dir.is_dir() and any(raw_dir.iterdir())
    if already_populated:
        print(f"{raw_dir} already has content — skipping. Delete it to regenerate.")
        return

    raw_dir.mkdir(parents=True, exist_ok=True)
    materialize_cifar10_subset(raw_dir, classes, args.per_class)
    print(f"Wrote {args.per_class} images per class for {len(classes)} classes to {raw_dir}")


if __name__ == "__main__":
    main()
