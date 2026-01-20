"""
Shared utilities for text chunking.

Contains preprocessing functions and helpers used across chunker implementations.
"""

import re


def preprocess_text(text: str) -> str:
    """
    Preprocess text to handle abbreviations that break sentence detection.

    Removes periods from common abbreviations (U.S., Inc., etc.) to prevent
    sentence splitters from incorrectly detecting sentence boundaries.

    Args:
        text: Raw input text.

    Returns:
        Text with abbreviation periods removed.
    """
    # Reason: These abbreviations contain periods that get mistakenly
    # treated as sentence boundaries, splitting sentences mid-phrase
    abbreviations = [
        (r"U\.S\.", "US"),
        (r"Inc\.", "Inc"),
        (r"Corp\.", "Corp"),
        (r"Ltd\.", "Ltd"),
        (r"Co\.", "Co"),
        (r"Mr\.", "Mr"),
        (r"Mrs\.", "Mrs"),
        (r"Ms\.", "Ms"),
        (r"Dr\.", "Dr"),
        (r"vs\.", "vs"),
        (r"etc\.", "etc"),
        (r"i\.e\.", "ie"),
        (r"e\.g\.", "eg"),
        (r"a\.m\.", "am"),
        (r"p\.m\.", "pm"),
        (r"No\.", "No"),
        (r"Vol\.", "Vol"),
        (r"Rev\.", "Rev"),
        (r"Est\.", "Est"),
        (r"Ave\.", "Ave"),
        (r"St\.", "St"),
    ]
    for pattern, replacement in abbreviations:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
