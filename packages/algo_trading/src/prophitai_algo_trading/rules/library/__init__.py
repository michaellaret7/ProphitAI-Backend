"""Standard library of trading rules."""

from prophitai_algo_trading.rules.library.consecutive_loss import ConsecutiveLossRule
from prophitai_algo_trading.rules.library.cooldown import CooldownRule
from prophitai_algo_trading.rules.library.earnings_proximity import EarningsProximityRule
from prophitai_algo_trading.rules.library.max_daily_loss import MaxDailyLossRule
from prophitai_algo_trading.rules.library.max_drawdown import MaxDrawdownRule
from prophitai_algo_trading.rules.library.max_holding_period import MaxHoldingPeriodRule
from prophitai_algo_trading.rules.library.quality_gate import QualityGateRule
from prophitai_algo_trading.rules.library.stop_loss import StopLossRule
from prophitai_algo_trading.rules.library.take_profit import TakeProfitRule
from prophitai_algo_trading.rules.library.time_of_day import TimeOfDayRule
from prophitai_algo_trading.rules.library.trailing_stop import TrailingStopRule

__all__ = [
    "ConsecutiveLossRule",
    "CooldownRule",
    "EarningsProximityRule",
    "MaxDailyLossRule",
    "MaxDrawdownRule",
    "MaxHoldingPeriodRule",
    "QualityGateRule",
    "StopLossRule",
    "TakeProfitRule",
    "TimeOfDayRule",
    "TrailingStopRule",
]
