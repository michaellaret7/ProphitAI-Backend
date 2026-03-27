"""
Data structures for earnings call transcript parsing and chunking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Turn:
    """
    Represents a single speaker turn in a transcript.

    Attributes:
        speaker: The name/label of the speaker.
        text: The content of what the speaker said.
        start: Start character index in processed transcript.
        end: End character index in processed transcript (exclusive).
    """
    speaker: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Unit:
    """
    Atomic-ish unit we prefer to keep intact when chunking.

    Example units: a prepared-remarks block, one analyst Q&A turn, one media Q&A turn.

    Attributes:
        unit_type: Type of unit (prepared | qna | operator | closing | misc).
        text: The text content of this unit.
        start: Start character index.
        end: End character index.
        meta: Metadata dictionary for this unit.
    """
    unit_type: str
    text: str
    start: int
    end: int
    meta: dict[str, Any]
