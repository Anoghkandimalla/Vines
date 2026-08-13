"""Find usages of changed API symbols in the target repo."""
import re
from pathlib import Path
from typing import Sequence

from apiwatch.models import CallSite

SKIP_DIRS = {".git", ".apiwatch", "node_modules", "venv", ".venv", "__pycache__"}
MIN_SYMBOL_LEN = 3


def scan_repo(
    root: Path,
    symbols: Sequence[str],
    extensions: tuple[str, ...] = (".py",),
) -> list[CallSite]:
    root = Path(root)
    patterns = {
        s: re.compile(rf"\b{re.escape(s)}\b")
        for s in symbols
        if len(s) >= MIN_SYMBOL_LEN
    }
    sites: list[CallSite] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in extensions:
            continue
        if SKIP_DIRS & set(p.name for p in path.parents):
            continue
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for sym, pat in patterns.items():
                if pat.search(line):
                    sites.append(
                        CallSite(
                            file=str(path.relative_to(root)),
                            line=lineno,
                            snippet=line.strip(),
                            symbol=sym,
                        )
                    )
    return sites
