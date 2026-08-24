"""Evaluates an exported ONNX artifact against the held-out test split
ONLY (constraints.md rule 9 — never train/val), using the preprocessing
spec recorded in the artifact's own metadata.json (rule 10 — not
recomputed independently, so evaluation can never silently drift from what
export.py actually shipped).

Writes `evaluation_report.json` into the artifact directory and reports
whether the model clears `evaluation.min_test_accuracy` from the config —
i.e. whether it's promotable for serving (constraints.md rule 8). This
script does not promote the model itself; promotion means pointing the
backend's `MODEL_VERSION` at this version, which is an explicit later
step.

Usage:
    python -m ml.export.evaluate --version <version> --config ml/configs/train_config.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime
from PIL import Image

from ml.config import load_config
from ml.preprocessing import apply_preprocessing
from ml.training.dataset import Manifest, SplitEntry


def load_test_entries(splits_dir: Path) -> tuple[list[SplitEntry], list[str]]:
    """Loads ONLY the test split from the persisted manifest — train/val
    are never read here."""
    manifest_path = Path(splits_dir) / "manifest.json"
    with manifest_path.open("r") as f:
        manifest = Manifest.from_json(json.load(f))
    return manifest.splits["test"], manifest.classes


def load_metadata(artifact_dir: Path) -> dict[str, Any]:
    with (artifact_dir / "metadata.json").open("r") as f:
        return json.load(f)


def compute_metrics_from_confusion(
    confusion: np.ndarray,
    classes: list[str],
    version: str,
    min_test_accuracy: float,
) -> dict[str, Any]:
    """Pure metrics/threshold-gating logic, kept separate from the
    onnxruntime/file I/O in `evaluate()` so it can be unit tested with a
    hand-built confusion matrix (constraints.md rule 24)."""
    total = int(confusion.sum())
    correct = int(np.trace(confusion))
    accuracy = correct / total if total else 0.0

    precision_per_class = {}
    recall_per_class = {}
    f1_per_class = {}
    for idx, class_name in enumerate(classes):
        predicted_positive = confusion[:, idx].sum()
        actual_positive = confusion[idx, :].sum()
        true_positive = confusion[idx, idx]
        precision = float(true_positive / predicted_positive) if predicted_positive else 0.0
        recall = float(true_positive / actual_positive) if actual_positive else 0.0
        precision_per_class[class_name] = precision
        recall_per_class[class_name] = recall
        f1_per_class[class_name] = (
            2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        )

    macro_f1 = sum(f1_per_class.values()) / len(f1_per_class) if f1_per_class else 0.0

    return {
        "version": version,
        "num_test_samples": total,
        "test_accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "precision_per_class": precision_per_class,
        "recall_per_class": recall_per_class,
        "f1_per_class": f1_per_class,
        "confusion_matrix": confusion.tolist(),
        "classes": classes,
        "min_test_accuracy": min_test_accuracy,
        "meets_threshold": bool(accuracy >= min_test_accuracy),
    }


def evaluate(artifact_dir: Path, splits_dir: Path, min_test_accuracy: float) -> dict[str, Any]:
    metadata = load_metadata(artifact_dir)
    classes = metadata["classes"]
    class_to_idx = {name: idx for idx, name in enumerate(classes)}
    preprocessing_spec = metadata["preprocessing"]

    test_entries, manifest_classes = load_test_entries(splits_dir)
    if manifest_classes != classes:
        raise ValueError(
            "The split manifest's class list doesn't match the exported "
            "model's class list — evaluating against the wrong dataset/model."
        )
    if not test_entries:
        raise ValueError("Test split is empty — nothing to evaluate.")

    session = onnxruntime.InferenceSession(str(artifact_dir / "model.onnx"))
    input_name = session.get_inputs()[0].name

    num_classes = len(classes)
    confusion = np.zeros((num_classes, num_classes), dtype=np.int64)

    for entry in test_entries:
        with Image.open(entry.path) as img:
            array = apply_preprocessing(img, preprocessing_spec)
        batch = array[np.newaxis, ...]  # add batch dim
        logits = session.run(None, {input_name: batch})[0]
        predicted_idx = int(np.argmax(logits[0]))
        true_idx = class_to_idx[entry.label]
        confusion[true_idx, predicted_idx] += 1

    report = compute_metrics_from_confusion(
        confusion, classes, metadata["version"], min_test_accuracy
    )

    with (artifact_dir / "evaluation_report.json").open("w") as f:
        json.dump(report, f, indent=2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=str, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("ml/configs/train_config.yaml")
    )
    args = parser.parse_args()

    config = load_config(args.config)
    artifact_dir = Path(config["artifacts_dir"]) / args.version
    splits_dir = Path(config["dataset"]["splits_dir"])
    min_test_accuracy = config["evaluation"]["min_test_accuracy"]

    report = evaluate(artifact_dir, splits_dir, min_test_accuracy)

    status = "PROMOTABLE" if report["meets_threshold"] else "NOT PROMOTABLE"
    print(
        f"version={report['version']} "
        f"test_accuracy={report['test_accuracy']:.4f} "
        f"macro_f1={report['macro_f1']:.4f} "
        f"threshold={min_test_accuracy:.4f} -> {status}"
    )
    sys.exit(0 if report["meets_threshold"] else 1)


if __name__ == "__main__":
    main()
