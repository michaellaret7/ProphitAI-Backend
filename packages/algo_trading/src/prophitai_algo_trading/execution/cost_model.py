"""Transaction cost model for the execution layer.

Centralizes all transaction cost math: sizing, outlay, proceeds.
Used by both event-driven and vectorized engines for consistent cost handling.
"""


class CostModel:
    """Transaction cost calculator.

    Args:
        ptc: Proportional transaction cost (e.g. 0.001 = 0.1%).
        ftc: Fixed transaction cost per trade (e.g. 5.0 = $5).
    """

    def __init__(self, ptc: float = 0.0, ftc: float = 0.0):
        self.ptc = ptc
        self.ftc = ftc

    def cost_for_trade(self, price: float, units: float) -> float:
        """Total transaction cost for a trade.

        Args:
            price: Price per unit.
            units: Number of units traded (always positive).
        """
        return abs(units) * price * self.ptc + self.ftc

    def max_units(self, price: float, cash: float) -> float:
        """Maximum units affordable given cash and costs.

        Derivation: total_outlay = units * price * (1 + ptc) + ftc = cash
        So: units = (cash - ftc) / (price * (1 + ptc))

        Args:
            price: Price per unit.
            cash: Available cash balance.
        """
        if price <= 0:
            return 0.0
        available = cash - self.ftc
        if available <= 0:
            return 0.0
        return available / (price * (1 + self.ptc))

    def net_proceeds(self, price: float, units: float) -> float:
        """Cash received from selling units after costs.

        Args:
            price: Price per unit.
            units: Number of units sold (always positive).
        """
        return abs(units) * price - self.cost_for_trade(price, units)

    def total_outlay(self, price: float, units: float) -> float:
        """Total cash required to buy units including costs.

        Args:
            price: Price per unit.
            units: Number of units bought (always positive).
        """
        return abs(units) * price + self.cost_for_trade(price, units)
