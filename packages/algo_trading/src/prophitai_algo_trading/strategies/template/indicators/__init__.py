"""Indicator composition helpers for the strategy scaffold."""

from prophitai_algo_trading.strategies.template.indicators.custom import (
    add_template_indicator_features,
)
from prophitai_algo_trading.strategies.template.indicators.suite import (
    TemplateIndicatorSuite,
)

__all__ = [
    "TemplateIndicatorSuite",
    "add_template_indicator_features",
]
