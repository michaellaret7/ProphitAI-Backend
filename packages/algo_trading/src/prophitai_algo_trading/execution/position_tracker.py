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

    def hydrate(self, position: int) -> None:
        """Set the position state directly for live startup hydration.

        Args:
            position: Target state (1=long, -1=short, 0=flat).

        Raises:
            ValueError: If position is not -1, 0, or 1.
        """
        if position not in (-1, 0, 1):
            raise ValueError(f"Invalid hydration position: {position}. Must be -1, 0, or 1.")
        self.position = position

    def plan_transition(
        self,
        signal: int,
        price: float,
        timestamp: datetime,
    ) -> list[dict]:
        """Plan instructions for a target signal without mutating state.

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

        return instructions

    def apply_instruction(self, instruction: dict) -> None:
        """Advance internal position state after a successful execution."""
        reason = instruction["reason"]
        if reason == "open_long":
            self.position = 1
        elif reason == "open_short":
            self.position = -1
        elif reason in ("close_long", "close_short"):
            self.position = 0
        else:
            raise ValueError(f"Unknown trade reason: {reason}")

    def update(self, signal: int, price: float, timestamp: datetime) -> list[dict]:
        """Convert a signal into trade instructions and apply them locally.

        This preserves the legacy mutation behavior for callers that expect
        ``update()`` to immediately advance state.
        """
        instructions = self.plan_transition(signal, price, timestamp)
        for instr in instructions:
            self.apply_instruction(instr)
        return instructions
