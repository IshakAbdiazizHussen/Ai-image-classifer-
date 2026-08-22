"""Exports a trained checkpoint to a versioned ONNX artifact.

Produces `ml/artifacts/<version>/model.onnx` and `metadata.json`
(constraints.md rule 7 — versioned, never overwritten). The checkpoint's
recorded classes/backbone are validated against the current config before
conversion is attempted (fails loudly on a mismatch rather than silently
exporting a broken model).

This script only exports — it does not evaluate or promote the result for
serving. See ml/export/evaluate.py for gating promotion on the accuracy
threshold.

Usage:
    python -m ml.export.export --checkpoint ml/checkpoints/<run_id>/checkpoint.pt \\
        --config ml/configs/train_config.yaml
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from ml.config import load_config
from ml.preprocessing import build_preprocessing_spec
from ml.training.model import build_model


def validate_checkpoint_matches_config(checkpoint: dict[str, Any], config: dict[str, Any]) -> None:
    """Fails loudly if the checkpoint doesn't match what the config
    currently expects — a stale/mismatched checkpoint is never silently
    exported."""
    expected_classes = config["dataset"]["classes"]
    expected_backbone = config["model"]["backbone"]

    if checkpoint["classes"] != expected_classes:
        raise ValueError(
            f"Checkpoint's class list {checkpoint['classes']} does not match "
            f"the current config's class list {expected_classes}. Refusing "
            f"to export — the exported model's label indices would be wrong."
        )
    if checkpoint["backbone"] != expected_backbone:
        raise ValueError(
            f"Checkpoint was trained with backbone '{checkpoint['backbone']}' "
            f"but config specifies '{expected_backbone}'. Refusing to export."
        )


def export_model(
    checkpoint_path: Path,
    config: dict[str, Any],
    version: str | None = None,
) -> Path:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    validate_checkpoint_matches_config(checkpoint, config)

    classes = checkpoint["classes"]
    image_size = checkpoint["image_size"]
    backbone = checkpoint["backbone"]

    model = build_model(num_classes=len(classes), config=config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    version = version or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(config["artifacts_dir"]) / version
    if artifact_dir.exists():
        raise FileExistsError(
            f"Artifact version '{version}' already exists at {artifact_dir} "
            f"— versions are never overwritten. Use a different version."
        )
    artifact_dir.mkdir(parents=True)

    dummy_input = torch.randn(1, 3, image_size, image_size)
    onnx_path = artifact_dir / "model.onnx"
    batch_dim = torch.export.Dim("batch")
    torch.onnx.export(
        model,
        (dummy_input,),
        str(onnx_path),
        input_names=["image"],
        output_names=["logits"],
        dynamic_shapes=({0: batch_dim},),
        opset_version=18,
    )

    metadata = {
        "version": version,
        "source_checkpoint": str(checkpoint_path),
        "classes": classes,
        "backbone": backbone,
        "image_size": image_size,
        "preprocessing": build_preprocessing_spec(image_size),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    with (artifact_dir / "metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Exported {onnx_path}")
    return artifact_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("ml/configs/train_config.yaml")
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Artifact version name. Defaults to a UTC export timestamp.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    export_model(args.checkpoint, config, version=args.version)


if __name__ == "__main__":
    main()
