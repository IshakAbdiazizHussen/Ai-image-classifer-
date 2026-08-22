"""Unit tests for ml/export/{export,evaluate}.py.

Covers Phase 2's required QA: export rejects a checkpoint/config
mismatch, exported artifacts are never overwritten, and evaluation reads
only the test split.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

import numpy as np

from ml.export.export import export_model, validate_checkpoint_matches_config
from ml.export.evaluate import compute_metrics_from_confusion, load_test_entries
from ml.preprocessing import apply_preprocessing, build_preprocessing_spec
from ml.training.model import build_model
from PIL import Image


def _base_config(tmp_path: Path) -> dict:
    return {
        "dataset": {"classes": ["cat", "dog"], "image_size": 224},
        "model": {"backbone": "mobilenet_v3_small", "pretrained": False},
        "artifacts_dir": str(tmp_path / "artifacts"),
    }


def _make_checkpoint(tmp_path: Path, config: dict) -> Path:
    model = build_model(num_classes=len(config["dataset"]["classes"]), config=config)
    checkpoint_path = tmp_path / "checkpoint.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "classes": config["dataset"]["classes"],
            "backbone": config["model"]["backbone"],
            "image_size": config["dataset"]["image_size"],
        },
        checkpoint_path,
    )
    return checkpoint_path


def test_validate_rejects_class_mismatch(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    checkpoint = {
        "classes": ["cat", "dog", "bird"],  # doesn't match config's 2 classes
        "backbone": "mobilenet_v3_small",
    }
    with pytest.raises(ValueError, match="class list"):
        validate_checkpoint_matches_config(checkpoint, config)


def test_validate_rejects_backbone_mismatch(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    checkpoint = {"classes": ["cat", "dog"], "backbone": "resnet18"}
    with pytest.raises(ValueError, match="backbone"):
        validate_checkpoint_matches_config(checkpoint, config)


def test_validate_accepts_matching_checkpoint(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    checkpoint = {"classes": ["cat", "dog"], "backbone": "mobilenet_v3_small"}
    validate_checkpoint_matches_config(checkpoint, config)  # should not raise


def test_export_writes_versioned_artifact_and_never_overwrites(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    checkpoint_path = _make_checkpoint(tmp_path, config)

    artifact_dir = export_model(checkpoint_path, config, version="v1")
    assert (artifact_dir / "model.onnx").is_file()
    assert (artifact_dir / "metadata.json").is_file()

    metadata = json.loads((artifact_dir / "metadata.json").read_text())
    assert metadata["version"] == "v1"
    assert metadata["classes"] == ["cat", "dog"]
    assert metadata["preprocessing"] == build_preprocessing_spec(224)

    with pytest.raises(FileExistsError):
        export_model(checkpoint_path, config, version="v1")  # re-export, same version

    # A different version is a separate artifact, not a collision.
    artifact_dir_v2 = export_model(checkpoint_path, config, version="v2")
    assert artifact_dir_v2 != artifact_dir
    assert (artifact_dir_v2 / "model.onnx").is_file()


def test_evaluate_reads_only_test_split(tmp_path: Path) -> None:
    manifest = {
        "seed": 1,
        "classes": ["cat", "dog"],
        "split_ratios": {"train": 0.6, "val": 0.2, "test": 0.2},
        "splits": {
            "train": [{"path": "train_1.png", "label": "cat"}],
            "val": [{"path": "val_1.png", "label": "dog"}],
            "test": [
                {"path": "test_1.png", "label": "cat"},
                {"path": "test_2.png", "label": "dog"},
            ],
        },
        "skipped_files": [],
    }
    splits_dir = tmp_path / "splits"
    splits_dir.mkdir()
    (splits_dir / "manifest.json").write_text(json.dumps(manifest))

    entries, classes = load_test_entries(splits_dir)

    assert classes == ["cat", "dog"]
    returned_paths = {e.path for e in entries}
    assert returned_paths == {"test_1.png", "test_2.png"}
    assert "train_1.png" not in returned_paths
    assert "val_1.png" not in returned_paths


def test_metrics_meets_threshold_on_perfect_confusion_matrix() -> None:
    # Every prediction correct: confusion matrix is diagonal.
    confusion = np.array([[5, 0], [0, 5]])
    report = compute_metrics_from_confusion(
        confusion, classes=["cat", "dog"], version="v1", min_test_accuracy=0.55
    )
    assert report["test_accuracy"] == 1.0
    assert report["meets_threshold"] is True
    assert report["precision_per_class"] == {"cat": 1.0, "dog": 1.0}
    assert report["recall_per_class"] == {"cat": 1.0, "dog": 1.0}


def test_metrics_fails_threshold_on_poor_confusion_matrix() -> None:
    # Every "cat" misclassified as "dog"; "dog" all correct.
    confusion = np.array([[0, 5], [0, 5]])
    report = compute_metrics_from_confusion(
        confusion, classes=["cat", "dog"], version="v1", min_test_accuracy=0.55
    )
    assert report["test_accuracy"] == 0.5
    assert report["meets_threshold"] is False
    assert report["recall_per_class"]["cat"] == 0.0
    assert report["precision_per_class"]["dog"] == 0.5


def test_apply_preprocessing_output_shape_and_range(tmp_path: Path) -> None:
    image = Image.new("RGB", (32, 32), color=(120, 60, 200))
    spec = build_preprocessing_spec(image_size=224)

    array = apply_preprocessing(image, spec)

    assert array.shape == (3, 224, 224)
    assert array.dtype.name == "float32"
    # normalized around ImageNet mean/std, so values should be roughly in
    # a small range rather than raw [0, 255] or unnormalized [0, 1]
    assert array.min() > -5.0
    assert array.max() < 5.0
