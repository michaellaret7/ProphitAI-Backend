"""Ticker analysis tools for Atlas agents.

This module provides ticker-specific analysis tools including:
- Factor calculations (growth, value, momentum, quality, volatility)
- Performance and risk metrics
- Technical indicators
- Weekly returns analysis
"""

from .factors import (
    CALCULATE_TICKER_FACTORS_TOOL,
    calculate_ticker_factors,
    SECTOR_ETF_MAP,
)

from .performance import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
    get_ticker_performance_and_risk,
    SINGLE_TICKER_METRIC_GROUPS,
)

from .technicals import (
    TECHNICALS_TOOL,
    run_technicals,
)

from .weekly_returns import (
    GET_WEEKLY_RETURNS_TOOL,
    get_weekly_returns,
)

__all__ = [
    # Factor tools
    'CALCULATE_TICKER_FACTORS_TOOL',
    'calculate_ticker_factors',
    'SECTOR_ETF_MAP',
    # Performance tools
    'GET_TICKER_PERFORMANCE_AND_RISK_TOOL',
    'get_ticker_performance_and_risk',
    'SINGLE_TICKER_METRIC_GROUPS',
    # Technical tools
    'TECHNICALS_TOOL',
    'run_technicals',
    # Weekly returns tools
    'GET_WEEKLY_RETURNS_TOOL',
    'get_weekly_returns',
]
