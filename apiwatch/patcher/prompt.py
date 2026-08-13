"""Build the instruction handed to the coding agent."""
from apiwatch.models import CallSite, ChangeEntry


def build_prompt(change: ChangeEntry, sites: list[CallSite]) -> str:
    site_lines = "\n".join(f"- {s.file}:{s.line}  `{s.snippet}`" for s in sites)
    files = sorted({s.file for s in sites})
    return f"""You are patching this repository for a breaking change in the {change.api} API.

## The breaking change ({change.api} API version {change.version})

{change.description}

Changelog: {change.url}

## Affected call sites found in this repo

{site_lines}

## Your task

Edit the affected code so it works correctly with {change.api} API version {change.version}.

Rules:
- Only edit these files: {", ".join(files)}.
- Make the minimal change required; do not reformat, rename, or refactor unrelated code.
- Do not add new dependencies.
- Do not create, delete, or move files.
- Preserve existing behavior for everything the breaking change does not affect.
"""
