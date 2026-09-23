"""Core data types shared by watcher, mapper, and patcher."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChangeEntry:
    api: str
    version: str
    title: str
    description: str
    breaking: bool
    symbols: tuple[str, ...]
    url: str
    # API resources the change applies to (e.g. "Discount"); when set, only
    # files mentioning one of them count as affected.
    resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class CallSite:
    file: str
    line: int
    snippet: str
    symbol: str
