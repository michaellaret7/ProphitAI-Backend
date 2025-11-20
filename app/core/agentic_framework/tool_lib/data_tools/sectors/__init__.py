"""Sector-level data tools.

This module provides tools for analyzing GICS sector data including:
- Sector hierarchy and ticker grouping
- Historical P/E ratios for valuation analysis
- Historical performance data for trend analysis
"""

from .hierarchy import (
    GET_GROUP_TICKERS_TOOL,
    GET_SECTOR_INDUSTRIES_TOOL,
    get_group_tickers,
    get_sector_industries,
)

from .pe_ratios import (
    GET_SECTOR_PE_TOOL,
    get_sector_pe,
)

from .performance import (
    GET_SECTOR_PERFORMANCE_TOOL,
    get_sector_performance,
)

from .mappings import (
    SECTOR_MAPPING,
    FMP_TO_EQUITY_SECTOR,
)

__all__ = [
    # Tools
    'GET_GROUP_TICKERS_TOOL',
    'GET_SECTOR_INDUSTRIES_TOOL',
    'GET_SECTOR_PE_TOOL',
    'GET_SECTOR_PERFORMANCE_TOOL',

    # Functions
    'get_group_tickers',
    'get_sector_industries',
    'get_sector_pe',
    'get_sector_performance',

    # Constants
    'SECTOR_MAPPING',
    'FMP_TO_EQUITY_SECTOR',
]