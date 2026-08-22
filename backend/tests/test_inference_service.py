"""Unit tests for services/inference_service.py — against the real
promoted model artifact, per Phase 3's QA requirement."""

from __future__ import annotations

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
