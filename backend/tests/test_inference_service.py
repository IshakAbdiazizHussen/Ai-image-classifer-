"""Unit tests for services/inference_service.py — against the real
promoted model artifact, per Phase 3's QA requirement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.core.config import settings
from backend.services.inference_service import InferenceService


@pytest.fixture(scope="module")
def inference_service() -> InferenceService:
    return InferenceService(settings.artifacts_dir, settings.model_version)


def test_predict_known_sample_image(inference_service: InferenceService) -> None:
    sample_path = next(Path("ml/data/raw/cat").glob("*.png"))
    result = inference_service.predict(sample_path.read_bytes())

    assert result.predicted_label == "cat"
    assert 0.0 <= result.confidence <= 1.0
    assert set(result.probabilities) == set(inference_service.classes)
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-4


def test_predict_rejects_non_image_bytes(inference_service: InferenceService) -> None:
    with pytest.raises(ValueError):
        inference_service.predict(b"definitely not an image")


def test_missing_artifact_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        InferenceService(settings.artifacts_dir, "version-that-does-not-exist")


def test_meets_threshold_reflects_the_real_evaluation_report(
    inference_service: InferenceService,
) -> None:
    # Cross-check against the actual file on disk rather than hardcoding
    # true/false — this artifact's real Phase 2 result was NOT
    # PROMOTABLE, and that must surface here, not be silently dropped.
    report_path = Path(settings.artifacts_dir) / settings.model_version / "evaluation_report.json"
    expected = json.loads(report_path.read_text())["meets_threshold"]
    assert inference_service.meets_threshold is expected


def test_meets_threshold_is_none_without_an_evaluation_report(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts" / "v-no-report"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "metadata.json").write_text(
        json.dumps(
            {
                "classes": ["cat", "dog"],
                "preprocessing": {"resize": 8, "center_crop": 8, "mean": [0, 0, 0], "std": [1, 1, 1]},
            }
        )
    )
    # A minimal valid ONNX model isn't needed — the constructor fails at
    # `onnxruntime.InferenceSession(...)` before reaching promotion-status
    # loading, so this only exercises `_load_promotion_status` directly.
    from backend.services.inference_service import InferenceService as _IS

    instance = object.__new__(_IS)
    instance.model_version = "v-no-report"
    assert instance._load_promotion_status(artifact_dir) is None
