"""Single helper for loading the training config — used by every ml/
script so the config file (ml/configs/train_config.yaml by default) stays
the one source of truth for dataset/split/training settings
(constraints.md rule 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("ml/configs/train_config.yaml")


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(config_path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r") as f:
        config = yaml.safe_load(f)

    ratios = config["dataset"]["split_ratios"]
    total = round(sum(ratios.values()), 6)
    if total != 1.0:
        raise ValueError(f"dataset.split_ratios must sum to 1.0, got {total}")

    return config
