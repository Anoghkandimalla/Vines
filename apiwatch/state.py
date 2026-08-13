"""Per-API watermark state: which changelog version was last seen."""
import json
from pathlib import Path


def load_state(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
