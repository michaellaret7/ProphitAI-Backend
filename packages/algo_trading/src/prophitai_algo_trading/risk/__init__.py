"""Risk management — one folder, one rule per concept.

Every rule is a self-contained ``RiskManagementModel`` (Stage 3 of the
Algorithm pipeline). Drop rules straight into ``Algorithm`` or compose
several via ``CompositeRiskModel`` — no bridge/wrapper classes.

Per-symbol rules (operate on individual positions):
    StopLossExit, TrailingStopExit, TimeStop, ProfitTargetExit,
    ReentryCooldown

Portfolio-wide rules (block/gate all symbols at once):
    DailyLossLimit, PortfolioDrawdownLimit, ConsecutiveLossCooldown,
    TradingWindow

Target-list transformations (don't fit the per-symbol hook shape):
    MaxDrawdownRiskModel   — delever on drawdown breach
    MaxGrossExposureRiskModel — cap portfolio gross notional

Composition:
    CompositeRiskModel     — sequence multiple models
"""

from prophitai_algo_trading.risk.base import (
    PeakEquityTracker,
    RiskContext,
    RiskRule,
)
from prophitai_algo_trading.risk.composite import CompositeRiskModel
from prophitai_algo_trading.risk.cooldowns import (
    ConsecutiveLossCooldown,
    ReentryCooldown,
)
from prophitai_algo_trading.risk.drawdown import MaxDrawdownRiskModel
from prophitai_algo_trading.risk.gross_cap import MaxGrossExposureRiskModel
from prophitai_algo_trading.risk.limits import (
    DailyLossLimit,
    PortfolioDrawdownLimit,
)
from prophitai_algo_trading.risk.stops import (
    ProfitTargetExit,
    StopLossExit,
    TimeStop,
    TrailingStopExit,
)
from prophitai_algo_trading.risk.windows import TradingWindow

__all__ = [
    # Base
    "RiskContext",
    "RiskRule",
    "PeakEquityTracker",
    # Stops / exits
    "ProfitTargetExit",
    "StopLossExit",
    "TimeStop",
    "TrailingStopExit",
    # Cooldowns
    "ConsecutiveLossCooldown",
    "ReentryCooldown",
    # Portfolio limits
    "DailyLossLimit",
    "PortfolioDrawdownLimit",
    # Windows
    "TradingWindow",
    # Target-list models
    "MaxDrawdownRiskModel",
    "MaxGrossExposureRiskModel",
    # Composition
    "CompositeRiskModel",
]
