"""Position tracker — stateless signal-to-trade translator.

Converts raw strategy signals (1=long, -1=short, 0=flat) into concrete
trade instructions with direction-aware reasons. Used by engines to
bridge signal resolution and portfolio execution.
"""

from datetime import datetime


class PositionTracker:
    """Translates signal changes into trade instructions.

    Tracks current position state (flat/long/short) and emits
    trade instruction dicts that downstream execution can route.

    Attributes:
        position: Current position state (0=flat, 1=long, -1=short).
    """

    def __init__(self):
        self.position: int = 0

    def update(self, signal: int, price: float, timestamp: datetime) -> list[dict]:
        """Convert a signal into trade instructions.

        Args:
            signal: Target position (1=long, -1=short, 0=flat).
            price: Current asset price.
            timestamp: Bar timestamp for the trade log.

        Returns:
            List of trade dicts with keys: side, reason, price, timestamp.
            Empty list if no transition needed.
        """
        if signal not in (-1, 0, 1):
            raise ValueError(f"Invalid signal: {signal}. Must be -1, 0, or 1.")

        if signal == self.position:
            return []

        instructions: list[dict] = []

        # Reason: close existing position before opening a new one
        if self.position == 1:
            instructions.append({
                "side": "sell",
                "reason": "close_long",
                "price": price,
                "timestamp": timestamp,
            })
        elif self.position == -1:
            instructions.append({
                "side": "buy",
                "reason": "close_short",
                "price": price,
                "timestamp": timestamp,
            })

        # Open new position
        if signal == 1:
            instructions.append({
                "side": "buy",
                "reason": "open_long",
                "price": price,
                "timestamp": timestamp,
            })
        elif signal == -1:
            instructions.append({
                "side": "sell",
                "reason": "open_short",
                "price": price,
                "timestamp": timestamp,
            })

        self.position = signal
        return instructions
