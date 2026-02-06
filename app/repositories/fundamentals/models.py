"""Data models for the fundamentals repository."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


@dataclass
class FundamentalsResult:
    """Container for fundamental datasets fetched from the database."""

    ticker: str
    income_statements: List[Any]
    balance_sheets: List[Any]
    cash_flow_statements: List[Any]
    financial_ratios: List[Any]
    analyst_estimates: List[Any]
