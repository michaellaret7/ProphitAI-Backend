"""Generic utility helpers for LLM backends."""

from __future__ import annotations

from typing import Any


def _strip_json_wrappers(text: str) -> str:
    """Remove markdown code fences from JSON text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            stripped = "\n".join(lines[1:-1]).strip()
    return stripped


def _compact_kwargs(**kwargs: Any) -> dict[str, Any]:
    """Return only kwargs whose values are not None."""
    return {key: value for key, value in kwargs.items() if value is not None}
