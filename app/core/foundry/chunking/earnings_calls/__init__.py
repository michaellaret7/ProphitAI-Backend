"""
Earnings call transcript chunking module.

Provides structurally-aware chunking for earnings call transcripts,
preserving high-level structure (operator intro, prepared remarks,
Q&A turns, media Q&A, closing).
"""

from .chunker import EarningsCallChunker
from .models import Turn, Unit
from .patterns import (
    CLOSING_RE,
    MEDIA_START_RE,
    OP_Q_INTRO_RE,
    QNA_START_RE,
    QUESTIONER_RE,
    SAFE_HARBOR_RE,
    SPEAKER_LINE_RE,
)
from .utils import mk_recursive_level

__all__ = [
    # Main chunker
    "EarningsCallChunker",
    # Data models
    "Turn",
    "Unit",
    # Patterns (for external use/testing)
    "SPEAKER_LINE_RE",
    "OP_Q_INTRO_RE",
    "QNA_START_RE",
    "MEDIA_START_RE",
    "CLOSING_RE",
    "SAFE_HARBOR_RE",
    "QUESTIONER_RE",
    # Utils
    "mk_recursive_level",
]
