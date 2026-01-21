"""
Shared utilities for retrieval operations.

Common functions used across VectorSearch and HybridSearch classes.
"""

from typing import Optional, Union


def build_metadata_filter(
    ticker: Optional[Union[str, list[str]]] = None,
    fiscal_quarter: Optional[Union[str, list[str]]] = None,
    fiscal_year: Optional[Union[int, list[int]]] = None,
) -> Optional[dict]:
    """
    Build a Pinecone metadata filter dict from optional search parameters.

    Supports single values or lists. Lists use Pinecone's $in operator.

    Args:
        ticker: Filter by ticker(s). Single string or list of strings.
        fiscal_quarter: Filter by quarter(s). Single string or list (e.g., ["2025Q3", "2025Q4"]).
        fiscal_year: Filter by year(s). Single int or list (e.g., [2024, 2025]).

    Returns:
        Dict of filters for Pinecone, or None if all parameters are None.

    Examples:
        # Single values
        build_metadata_filter(ticker="AAPL", fiscal_year=2025)
        # -> {"ticker": "AAPL", "fiscal_year": 2025}

        # Multiple values (uses $in operator)
        build_metadata_filter(ticker=["AAPL", "GOOGL"], fiscal_year=[2024, 2025])
        # -> {"ticker": {"$in": ["AAPL", "GOOGL"]}, "fiscal_year": {"$in": [2024, 2025]}}
    """
    filters = {}

    for key, value in (
        ("ticker", ticker),
        ("fiscal_quarter", fiscal_quarter),
        ("fiscal_year", fiscal_year),
    ):
        if value is None:
            continue
        if isinstance(value, list):
            filters[key] = {"$in": value}
        else:
            filters[key] = value

    return filters if filters else None
