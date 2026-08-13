"""Source loading and change filtering shared across watched APIs."""
import re
import urllib.request

from apiwatch.models import ChangeEntry


def html_to_text(html: str) -> str:
    """Minimal HTML -> markdown-ish conversion: enough structure for parsing."""
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def load_source(source: str) -> str:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return html_to_text(raw) if "<html" in raw[:2000].lower() else raw
    with open(source, encoding="utf-8") as f:
        return f.read()


def new_breaking_changes(entries: list[ChangeEntry], last_version: str | None) -> list[ChangeEntry]:
    return [
        e for e in entries
        if e.breaking and (last_version is None or e.version > last_version)
    ]
