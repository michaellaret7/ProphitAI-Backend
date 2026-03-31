"""Portfolio tracker entrypoint class."""

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import PositionState, Trade
from prophitai_algo_trading.execution.portfolio_tracker.execution import (
    PortfolioTrackerExecutionMixin,
)
from prophitai_algo_trading.execution.portfolio_tracker.hydration import (
    PortfolioTrackerHydrationMixin,
)
from prophitai_algo_trading.execution.portfolio_tracker.reporting import (
    PortfolioTrackerReportingMixin,
)
from prophitai_algo_trading.execution.portfolio_tracker.valuation import (
    PortfolioTrackerValuationMixin,
)
from prophitai_algo_trading.sizing import BasePositionSizer


class PortfolioTracker(
    PortfolioTrackerHydrationMixin,
    PortfolioTrackerValuationMixin,
    PortfolioTrackerExecutionMixin,
    PortfolioTrackerReportingMixin,
):
    """Portfolio tracker with full position, trade, and equity tracking."""

    def __init__(
        self,
        initial_capital: float,
        sizer: BasePositionSizer,
        cost_model: CostModel | None = None,
        broker=None,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self._cost_model = cost_model or CostModel()
        self._sizer = sizer
        self._broker = broker
        self._positions: dict[str, PositionState] = {}
        self._equity_history: list[dict] = []
        self._trades: list[Trade] = []
        self._latest_prices: dict[str, float] = {}
        self._peak_equity = initial_capital
