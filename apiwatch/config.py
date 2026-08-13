"""Load and default the apiwatch.yml configuration."""
from pathlib import Path

import yaml

DEFAULTS = {"state_file": ".apiwatch/state.json", "base_branch": "main"}


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if "apis" not in cfg or not cfg["apis"]:
        raise ValueError("apiwatch.yml must define at least one entry under 'apis'")
    return {**DEFAULTS, **cfg}
