"""Parse Stripe's prose changelog (API upgrades page) into structured entries.

Stripe has no machine-readable changelog, so this extracts structure from the
markdown-ish document: one `## <version>` heading per API version, with
`### Breaking changes` / other subsections containing bullet entries.
"""
import re

from apiwatch.models import ChangeEntry

_VERSION_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^-\s+(.+?)(?=^-\s|\Z)", re.MULTILINE | re.DOTALL)
_SYMBOL_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")


def extract_symbols(text: str) -> tuple[str, ...]:
    seen: list[str] = []
    for sym in _SYMBOL_RE.findall(text):
        if sym not in seen:
            seen.append(sym)
    return tuple(seen)


def parse_changelog(text: str, url: str = "") -> list[ChangeEntry]:
    entries: list[ChangeEntry] = []
    versions = list(_VERSION_RE.finditer(text))
    for i, vm in enumerate(versions):
        version = vm.group(1)
        end = versions[i + 1].start() if i + 1 < len(versions) else len(text)
        body = text[vm.end():end]
        sections = list(_SECTION_RE.finditer(body))
        for j, sm in enumerate(sections):
            heading = sm.group(1)
            s_end = sections[j + 1].start() if j + 1 < len(sections) else len(body)
            breaking = "breaking" in heading.lower()
            for bm in _BULLET_RE.finditer(body[sm.end():s_end]):
                desc = " ".join(bm.group(1).split())
                entries.append(
                    ChangeEntry(
                        api="stripe",
                        version=version,
                        title=desc[:80],
                        description=desc,
                        breaking=breaking,
                        symbols=extract_symbols(desc),
                        url=f"{url}#{version}" if url else "",
                    )
                )
    return entries
