"""Transaction cost model."""

from __future__ import annotations


class CostModel:
    """Proportional + fixed transaction costs.

    Args:
        ptc: Proportional cost as a fraction (0.001 = 10 bps).
        ftc: Fixed cost per trade in dollars.
    """

    def __init__(self, ptc: float = 0.0, ftc: float = 0.0):
        self.ptc = ptc
        self.ftc = ftc

    def cost(self, price: float, shares: float) -> float:
        """Total transaction cost for a trade of ``shares`` at ``price``."""
        return abs(shares) * price * self.ptc + self.ftc

    def max_shares(self, price: float, cash: float) -> float:
        """Max shares affordable given ``cash`` after costs."""
        if price <= 0:
            return 0.0

        available = cash - self.ftc

        if available <= 0:
            return 0.0

        return available / (price * (1.0 + self.ptc))
