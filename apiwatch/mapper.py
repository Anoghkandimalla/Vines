"""Find usages of changed API symbols in the target repo.

Symbols are split into two tiers: snake_case attribute names (primary) are real
evidence of API usage, while CapitalCase resource names (secondary) only count in
files that already contain a primary match — avoiding false positives on an app's
own domain models. If only secondary symbols are given, they are treated as primary.
"""
import re
from pathlib import Path
from typing import Sequence

from apiwatch.models import CallSite

SKIP_DIRS = {".git", ".apiwatch", "node_modules", "venv", ".venv", "__pycache__"}
MIN_SYMBOL_LEN = 3


def _is_primary(symbol: str) -> bool:
    return symbol.islower() or "_" in symbol


def scan_repo(
    root: Path,
    symbols: Sequence[str],
    extensions: tuple[str, ...] = (".py",),
    api_name: str | None = None,
) -> list[CallSite]:
    root = Path(root)
    usable = [s for s in symbols if len(s) >= MIN_SYMBOL_LEN]
    primary = [s for s in usable if _is_primary(s)]
    secondary = [s for s in usable if not _is_primary(s)]
    if not primary:
        primary, secondary = secondary, []
    patterns = {s: re.compile(rf"\b{re.escape(s)}\b") for s in primary + secondary}
    sites: list[CallSite] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in extensions:
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts[:-1]):
            continue
        text = path.read_text(errors="replace")
        if api_name and api_name.lower() not in text.lower():
            continue
        if not any(patterns[s].search(text) for s in primary):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
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
