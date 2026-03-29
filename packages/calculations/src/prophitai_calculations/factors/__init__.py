"""Factor calculation module.

Provides ticker-level factor exposures (momentum, value, quality, growth,
volatility, size). Portfolio-level factor exposure analysis lives in
portfolio_analytics/factor_exposures.py.
"""

from prophitai_calculations.factors.calc_all import calc_all_factors

__all__ = [
    'calc_all_factors',
]
