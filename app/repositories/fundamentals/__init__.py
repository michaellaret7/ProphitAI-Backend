"""Fundamentals data repository package.

Provides access to fundamental financial data including income statements,
balance sheets, cash flow statements, financial ratios, and analyst estimates.
"""

from app.repositories.fundamentals.models import FundamentalsResult
from app.repositories.fundamentals.fetchers import get_fundamentals_raw, get_bulk_fundamentals
from app.repositories.fundamentals.statements import (
    get_fundamental_data,
    get_analyst_estimates,
    get_all_fundamentals,
    get_all_columns_fundamentals,
)

__all__ = [
    "FundamentalsResult",
    "get_fundamentals_raw",
    "get_bulk_fundamentals",
    "get_fundamental_data",
    "get_analyst_estimates",
    "get_all_fundamentals",
    "get_all_columns_fundamentals",
]
