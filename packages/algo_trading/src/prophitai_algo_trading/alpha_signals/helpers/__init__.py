"""Shared computational primitives for alpha signals.

Pure-numeric helpers used by multiple alphas — true range, signed
streak series, etc. Each helper supports both per-symbol Series/DataFrame
inputs (event-driven path) and panel-wide DataFrame inputs (vector path)
through the same call surface.
"""

from prophitai_algo_trading.alpha_signals.helpers.streak import streak_series
from prophitai_algo_trading.alpha_signals.helpers.true_range import (
    true_range_panel,
    true_range_series,
)


__all__ = [
    "streak_series",
    "true_range_panel",
    "true_range_series",
]
