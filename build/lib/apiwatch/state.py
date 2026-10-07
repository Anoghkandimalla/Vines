"""Per-API watermark state: which changelog version was last seen."""
import json
from pathlib import Path


def load_state(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        # A corrupt state file must be an error, never treated as "no state":
        # an empty state would re-trigger first-run behavior.
        raise ValueError(f"corrupt apiwatch state file {path}: {exc}") from exc


def save_state(path: Path, state: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
