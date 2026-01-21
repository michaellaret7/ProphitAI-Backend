"""
Shared utilities for retrieval operations.

Common functions used across VectorSearch and HybridSearch classes.
"""

from typing import Optional


def build_metadata_filter(
    ticker: Optional[str] = None,
    fiscal_quarter: Optional[str] = None,
    fiscal_year: Optional[int] = None,
) -> Optional[dict]:
    """
    Build a Pinecone metadata filter dict from optional search parameters.

    Args:
        ticker: Filter by company ticker symbol.
        fiscal_quarter: Filter by fiscal quarter (e.g., "2025Q3").
        fiscal_year: Filter by fiscal year.

    Returns:
        Dict of non-None filters, or None if all parameters are None.
    """
    filters = {
        key: value
        for key, value in (
            ("ticker", ticker),
            ("fiscal_quarter", fiscal_quarter),
            ("fiscal_year", fiscal_year),
        )
        if value is not None
    }
    return filters if filters else None
