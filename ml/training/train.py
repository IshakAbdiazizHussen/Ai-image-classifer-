"""Training entrypoint. Trains the configured backbone against the
persisted split, and writes a checkpoint plus the exact run config used to
produce it (constraints.md rule 6) into a versioned run directory under
`checkpoints_dir`.

This script produces trained checkpoints only — no export, no serving.
See ml/export/ (Phase 2) for turning a checkpoint into a served model.

Usage:
    python -m ml.training.train --config ml/configs/train_config.yaml
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.config import load_config
from ml.training.dataset import build_dataloaders
from ml.training.model import build_model, resolve_device


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.mps.manual_seed(seed) if torch.backends.mps.is_available() else None
    torch.cuda.manual_seed_all(seed) if torch.cuda.is_available() else None


def run_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: str,
    optimizer: torch.optim.Optimizer | None = None,
) -> tuple[float, float]:
    """Runs one pass over `dataloader`. Trains (backprop) if `optimizer` is
    given, otherwise evaluates in inference mode. Returns (avg_loss, accuracy)."""
    is_train = optimizer is not None
    model.train(is_train)

    total_loss = 0.0
    correct = 0
    total = 0

    context = torch.enable_grad() if is_train else torch.no_grad()
    with context:
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)

            if is_train:
                optimizer.zero_grad()

            outputs = model(images)
            loss = criterion(outputs, labels)

            if is_train:
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * images.size(0)
            correct += (outputs.argmax(dim=1) == labels).sum().item()
            total += images.size(0)

    return total_loss / total, correct / total


def train(config: dict, config_path: Path) -> Path:
    set_seed(config["seed"])

    dataloaders, manifest = build_dataloaders(config)
    device = resolve_device(config["training"]["device"])

    model = build_model(num_classes=len(manifest.classes), config=config).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config["training"]["learning_rate"]
    )

    epochs = config["training"]["epochs"]
    history = []
    for epoch in range(1, epochs + 1):
        train_loss, train_acc = run_epoch(
            model, dataloaders["train"], criterion, device, optimizer
        )
        val_loss, val_acc = run_epoch(model, dataloaders["val"], criterion, device)
        print(
            f"epoch {epoch}/{epochs} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
            }
        )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(config["checkpoints_dir"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "classes": manifest.classes,
            "backbone": config["model"]["backbone"],
            "image_size": config["dataset"]["image_size"],
        },
        run_dir / "checkpoint.pt",
    )

    # Record the exact config used for this run, alongside its metrics —
    # any checkpoint can be traced back to the settings that produced it.
    shutil.copy(config_path, run_dir / "config.yaml")
    with (run_dir / "metrics.json").open("w") as f:
        json.dump({"history": history, "final_val_acc": history[-1]["val_acc"]}, f, indent=2)

    print(f"Saved checkpoint to {run_dir}")
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("ml/configs/train_config.yaml")
    )
    args = parser.parse_args()

    config = load_config(args.config)
    train(config, args.config)


if __name__ == "__main__":
    main()
