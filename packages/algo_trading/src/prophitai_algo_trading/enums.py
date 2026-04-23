"""Shared enums used across the package.

Kept in a small neutral module so broker/portfolio/live layers don't form
an import cycle through portfolio.py.
"""

from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    """Trade direction."""

    LONG = "long"
    SHORT = "short"
