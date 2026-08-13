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


@dataclass(frozen=True)
class CallSite:
    file: str
    line: int
    snippet: str
    symbol: str
