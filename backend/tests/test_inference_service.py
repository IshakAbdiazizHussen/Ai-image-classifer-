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


def test_predict_returns_a_well_formed_result(inference_service: InferenceService) -> None:
    """Structural correctness of a single prediction — not which label it
    picks. The real model has 78.2% test accuracy (see
    ml/artifacts/<version>/evaluation_report.json), so asserting one
    specific image predicts one specific class is inherently brittle: a
    hard example on the model's weakest class (cat, F1 0.647) can
    legitimately be wrong without anything being broken. See
    `test_predict_is_reasonably_accurate_across_a_sample` below for the
    "the model actually works" check this test used to also try to be."""
    sample_path = next(Path("ml/data/raw/cat").glob("*.png"))
    result = inference_service.predict(sample_path.read_bytes())

    assert result.predicted_label in inference_service.classes
    assert 0.0 <= result.confidence <= 1.0
    assert set(result.probabilities) == set(inference_service.classes)
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-4


def test_predict_is_reasonably_accurate_across_a_sample(
    inference_service: InferenceService,
) -> None:
    """A genuine sanity check that the whole inference pipeline
    (preprocessing, forward pass, label mapping) is wired up correctly —
    without coupling to any single image's specific outcome. Samples a
    few images per class and asserts a clear majority are classified
    correctly, allowing for the model's known ~78% accuracy rather than
    demanding 100%."""
    samples_per_class = 3
    sample_paths = [
        path
        for class_dir in sorted(Path("ml/data/raw").iterdir())
        if class_dir.is_dir()
        for path in sorted(class_dir.glob("*.png"))[:samples_per_class]
    ]
    assert sample_paths, "no sample images found under ml/data/raw"

    correct = sum(
        1
        for path in sample_paths
        if inference_service.predict(path.read_bytes()).predicted_label == path.parent.name
    )
    accuracy = correct / len(sample_paths)

    # Comfortably below the model's real ~78% test accuracy (avoids
    # flakiness from small-sample variance) but far above the 10%
    # random-chance baseline for 10 classes — this is a "the pipeline
    # isn't broken" check, not a re-measurement of model quality.
    assert accuracy >= 0.5, (
        f"only {correct}/{len(sample_paths)} correct ({accuracy:.0%}) — "
        f"expected a clear majority given the model's real test accuracy"
    )


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
