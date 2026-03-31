"""Signal resolution logic shared by all engine types.

Translates raw entry/exit boolean signals into position targets (1/0/-1)
for both vectorized (batch) and event-driven (bar-by-bar) modes.
"""

import numpy as np

from prophitai_algo_trading.execution.models import Direction

# ================================
# --> Constants
# ================================

REASON_TO_DIRECTION: dict[str, Direction] = {
    "open_long": Direction.LONG,
    "close_long": Direction.LONG,
    "open_short": Direction.SHORT,
    "close_short": Direction.SHORT,
}

# ================================
# --> Helper funcs
# ================================


def is_entry_instruction(instruction: dict) -> bool:
    """Return True if the instruction opens a new position."""
    return instruction["reason"].startswith("open_")


def resolve_positions(
    long_entry: np.ndarray,
    long_exit: np.ndarray,
    short_entry: np.ndarray,
    short_exit: np.ndarray,
) -> np.ndarray:
    """Convert entry/exit signals into a position array (1/0/-1).

    Single forward pass over numpy arrays. This loop is unavoidable because
    position at bar N depends on bar N-1, but numpy int8 indexing is ~100x
    faster than itertuples + on_bar().

    Args:
        long_entry: Boolean array — True where a long entry signal fires.
        long_exit: Boolean array — True where a long exit signal fires.
        short_entry: Boolean array — True where a short entry signal fires.
        short_exit: Boolean array — True where a short exit signal fires.

    Returns:
        int8 array of positions: 1 (long), -1 (short), 0 (flat).
    """
    n = len(long_entry)
    positions = np.zeros(n, dtype=np.int8)

    for i in range(1, n):
        prev = positions[i - 1]

        # Reason: exits take priority — protect capital before considering new entries
        if prev == 1 and long_exit[i]:
            positions[i] = 0
        elif prev == -1 and short_exit[i]:
            positions[i] = 0
        elif long_entry[i]:
            positions[i] = 1
        elif short_entry[i]:
            positions[i] = -1
        else:
            positions[i] = prev

    return positions


def resolve_signal(
    long_entry: bool,
    long_exit: bool,
    short_entry: bool,
    short_exit: bool,
    current_position: int,
) -> int:
    """Single-bar signal resolution for event-driven mode.

    Applies the same priority logic as resolve_positions() but for a
    single bar: entries > exits > hold.

    Args:
        long_entry: Whether a long entry signal fires on this bar.
        long_exit: Whether a long exit signal fires on this bar.
        short_entry: Whether a short entry signal fires on this bar.
        short_exit: Whether a short exit signal fires on this bar.
        current_position: Current position state (1, 0, or -1).

    Returns:
        Target position: 1 (long), -1 (short), or 0 (flat).
    """
    # Reason: exits take priority — protect capital before considering new entries
    if current_position == 1 and long_exit:
        return 0
    if current_position == -1 and short_exit:
        return 0
    if long_entry:
        return 1
    if short_entry:
        return -1
    return current_position
