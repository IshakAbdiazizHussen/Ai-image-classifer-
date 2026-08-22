"""Model architecture: a pretrained torchvision backbone with its
classification head replaced to match the configured class count.

Only `mobilenet_v3_small` is wired up for now — it's small and fast enough
to train on CPU/MPS for the sample-dataset smoke run. Swapping backbones
later just means adding another branch in `build_model`.
"""

from __future__ import annotations

from typing import Any

import torch.nn as nn
from torchvision.models import (
    MobileNet_V3_Small_Weights,
    mobilenet_v3_small,
)


def build_model(num_classes: int, config: dict[str, Any]) -> nn.Module:
    backbone_name = config["model"]["backbone"]
    pretrained = config["model"]["pretrained"]

    if backbone_name != "mobilenet_v3_small":
        raise ValueError(
            f"Unknown backbone '{backbone_name}'. Only 'mobilenet_v3_small' "
            f"is currently supported."
        )

    weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    model = mobilenet_v3_small(weights=weights)

    # Replace the final classifier layer to match the configured class
    # count; every earlier layer keeps its (optionally pretrained) weights.
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)

    return model


def resolve_device(device_config: str) -> str:
    import torch

    if device_config != "auto":
        return device_config
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
