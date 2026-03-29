"""
SnapTrade Utility Functions
Pure helpers for symbol conversion and response extraction.
"""

import re
from typing import Any

# Reason: SnapTrade requires 21-character OCC format (6-char padded root + 15-char suffix)
_OSI_SPLIT = re.compile(r"^([A-Z0-9.\-]+)(\d{6}[CP]\d{8})$")


def osi_to_occ(osi_symbol: str) -> str:
    """
    Convert Alpaca OSI symbol to 21-char OCC format by padding the root to 6 chars.

    Args:
        osi_symbol: OSI option symbol (e.g. 'CRWV260327C00120000')

    Returns:
        OCC-formatted symbol (e.g. 'CRWV  260327C00120000', 21 chars)
    """
    m = _OSI_SPLIT.match(osi_symbol)
    if not m:
        raise ValueError(f"Cannot parse OSI symbol: {osi_symbol}")
    root, suffix = m.groups()
    return f"{root:<6}{suffix}"


def extract_body(response: Any) -> Any:
    """Unwrap .body from SDK responses consistently."""
    return getattr(response, "body", response)
