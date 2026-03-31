"""Trading rules — execution-layer guards for BacktestEngine and LiveRunner."""

from prophitai_algo_trading.rules.advanced_base import AdvancedRuleTemplate
from prophitai_algo_trading.rules.base import TradingRule
from prophitai_algo_trading.rules.engine import RuleEngine
from prophitai_algo_trading.rules.library import (
    ConsecutiveLossRule,
    CooldownRule,
    EarningsProximityRule,
    MaxDailyLossRule,
    MaxDrawdownRule,
    MaxHoldingPeriodRule,
    QualityGateRule,
    StopLossRule,
    TakeProfitRule,
    TimeOfDayRule,
    TrailingStopRule,
)

__all__ = [
    "TradingRule",
    "AdvancedRuleTemplate",
    "RuleEngine",
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
