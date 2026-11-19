"""Paths printed in generated documents must never be machine-specific."""
from __future__ import annotations

from pathlib import Path


def _display_path(value: str) -> str:
    """Show repo-relative paths in generated docs, never a local absolute path."""
    path = Path(value)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name
