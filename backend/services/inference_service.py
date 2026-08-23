"""Loads the promoted ONNX model once (at app startup, held on
`app.state`) and serves predictions from it — never per-request loading
(constraints.md rule 17). onnxruntime sessions are safe to call
concurrently, so a single instance is reused across all requests.

Preprocessing is delegated to `ml.preprocessing.apply_preprocessing` using
the spec recorded in the artifact's own `metadata.json` — the same
function evaluate.py used, byte-for-byte (constraints.md rule 10). This
module has no torch/torchvision dependency, only onnxruntime + PIL/numpy.
"""

from __future__ import annotations

import io
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime
from PIL import Image, UnidentifiedImageError

from ml.preprocessing import apply_preprocessing

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    predicted_label: str
    confidence: float
    probabilities: dict[str, float]
    inference_latency_ms: float


class InferenceService:
    def __init__(self, artifacts_dir: str, model_version: str) -> None:
        artifact_dir = Path(artifacts_dir) / model_version
        metadata_path = artifact_dir / "metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"No model artifact found for MODEL_VERSION={model_version!r} "
                f"at {artifact_dir} — export it first (see ml/export/export.py)."
            )
        with metadata_path.open("r") as f:
            self.metadata = json.load(f)

        self.model_version = model_version
        self.classes: list[str] = self.metadata["classes"]
        self.preprocessing_spec = self.metadata["preprocessing"]
        self.session = onnxruntime.InferenceSession(str(artifact_dir / "model.onnx"))
        self.input_name = self.session.get_inputs()[0].name

        # constraints.md rule 8: "a failing export is never wired in" — an
        # unenforced version of that rule is really just documentation, so
        # this checks the artifact's own evaluation_report.json (if
        # export/evaluate.py produced one) and makes the result loud and
        # visible (startup log + /healthz's model_promotable field)
        # instead of silent. It does not refuse to start: for a demo/dev
        # deployment serving a known sub-threshold model can be a
        # deliberate choice — the point is that choice must be visible,
        # never quiet.
        self.meets_threshold: bool | None = self._load_promotion_status(artifact_dir)

    def _load_promotion_status(self, artifact_dir: Path) -> bool | None:
        report_path = artifact_dir / "evaluation_report.json"
        if not report_path.is_file():
            logger.warning(
                "no evaluation_report.json found for this model version — "
                "promotion status unknown (was ml/export/evaluate.py ever run?)",
                extra={"model_version": self.model_version},
            )
            return None

        with report_path.open("r") as f:
            report = json.load(f)
        meets_threshold = bool(report.get("meets_threshold"))

        if not meets_threshold:
            logger.warning(
                "serving a model version that did NOT clear its own "
                "accuracy threshold — this is allowed but must not be silent",
                extra={
                    "model_version": self.model_version,
                    "test_accuracy": report.get("test_accuracy"),
                    "min_test_accuracy": report.get("min_test_accuracy"),
                },
            )
        return meets_threshold

    def predict(self, image_bytes: bytes) -> PredictionResult:
        start = time.perf_counter()

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Uploaded file is not a readable image.") from exc

        array = apply_preprocessing(image, self.preprocessing_spec)
        batch = array[np.newaxis, ...].astype(np.float32)
        logits = self.session.run(None, {self.input_name: batch})[0][0]

        probabilities = _softmax(logits)
        predicted_idx = int(np.argmax(probabilities))

        return PredictionResult(
            predicted_label=self.classes[predicted_idx],
            confidence=float(probabilities[predicted_idx]),
            probabilities={
                name: float(p) for name, p in zip(self.classes, probabilities)
            },
            inference_latency_ms=(time.perf_counter() - start) * 1000,
        )


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / exp.sum()
