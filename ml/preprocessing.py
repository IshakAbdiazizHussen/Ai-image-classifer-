"""Single source of truth for inference-time preprocessing
(constraints.md rule 10).

Used by three places, all reading the same spec so none of them can drift:
  - ml/training/dataset.py's val/test transform (imports the constants and
    the same resize/crop formula the spec below encodes).
  - ml/export/evaluate.py, which loads this exact spec back out of an
    exported model's metadata.json rather than recomputing it.
  - the backend's inference_service (Phase 3) — this module has no torch/
    torchvision dependency, only PIL/numpy, so it's cheap to reuse at
    serving time without pulling in the training stack.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_preprocessing_spec(image_size: int) -> dict[str, Any]:
    return {
        "resize": int(image_size * 1.14),
        "center_crop": image_size,
        "mean": IMAGENET_MEAN,
        "std": IMAGENET_STD,
    }


def apply_preprocessing(image: Image.Image, spec: dict[str, Any]) -> np.ndarray:
    """Resize (shorter edge) -> center crop -> scale to [0,1] -> normalize
    -> CHW float32. Mirrors torchvision's
    Resize(int)/CenterCrop/ToTensor/Normalize pipeline exactly, so a
    prediction from the exported ONNX model matches what the original
    PyTorch checkpoint would have produced on the same image."""
    image = image.convert("RGB")
    resize_size = spec["resize"]
    crop_size = spec["center_crop"]

    w, h = image.size
    if w <= h:
        new_w, new_h = resize_size, round(h * resize_size / w)
    else:
        new_h, new_w = resize_size, round(w * resize_size / h)
    image = image.resize((new_w, new_h), Image.BILINEAR)

    left = (new_w - crop_size) // 2
    top = (new_h - crop_size) // 2
    image = image.crop((left, top, left + crop_size, top + crop_size))

    array = np.asarray(image).astype(np.float32) / 255.0
    mean = np.array(spec["mean"], dtype=np.float32)
    std = np.array(spec["std"], dtype=np.float32)
    array = (array - mean) / std
    return array.transpose(2, 0, 1)  # HWC -> CHW
