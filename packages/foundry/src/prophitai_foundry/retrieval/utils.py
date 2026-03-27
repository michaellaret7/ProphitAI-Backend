"""
Shared utilities for retrieval operations.

Common functions used across VectorSearch and HybridSearch classes.
"""

from typing import Any, Optional


def build_metadata_filter(
    valid_keys: Optional[set[str]] = None,
    **filters: Any,
) -> Optional[dict]:
    """
    Build a Pinecone metadata filter dict from keyword arguments.

    Supports single values or lists. Lists use Pinecone's $in operator.

    Args:
        valid_keys: Optional set of valid metadata keys for validation.
            If provided, raises ValueError for any filter key not in the set.
        **filters: Arbitrary filter parameters as keyword arguments.
            Each key should match a metadata field name in Pinecone.
            Values can be single items or lists.

    Returns:
        Dict of filters for Pinecone, or None if no filters provided.

    Raises:
        ValueError: If valid_keys is provided and a filter key is not valid.

    Examples:
        # Single values
        build_metadata_filter(ticker="AAPL", fiscal_year=2025)
        # -> {"ticker": "AAPL", "fiscal_year": 2025}

        # Multiple values (uses $in operator)
        build_metadata_filter(ticker=["AAPL", "GOOGL"], fiscal_year=[2024, 2025])
        # -> {"ticker": {"$in": ["AAPL", "GOOGL"]}, "fiscal_year": {"$in": [2024, 2025]}}

        # With validation
        build_metadata_filter(
            valid_keys={"ticker", "fiscal_year"},
            ticker="AAPL",
            invalid_field="test"  # Raises ValueError
        )
    """
    if not filters:
        return None

    # Reason: Filter out None values to allow optional kwargs
    active_filters = {k: v for k, v in filters.items() if v is not None}

    if not active_filters:
        return None

    if valid_keys:
        invalid_keys = set(active_filters.keys()) - valid_keys
        if invalid_keys:
            raise ValueError(
                f"Invalid filter keys: {invalid_keys}. "
                f"Valid keys are: {valid_keys}"
            )

    result = {}
    for key, value in active_filters.items():
        if isinstance(value, list):
            result[key] = {"$in": value}
        else:
            result[key] = value

    return result


def validate_filter_keys(
    filter_keys: set[str],
    valid_keys: set[str],
) -> None:
    """
    Validate that all filter keys exist in the valid keys set.

    Args:
        filter_keys: Set of keys to validate.
        valid_keys: Set of valid metadata keys.

    Raises:
        ValueError: If any filter key is not in valid_keys.
    """
    invalid_keys = filter_keys - valid_keys
    if invalid_keys:
        raise ValueError(
            f"Invalid filter keys: {invalid_keys}. "
            f"Valid keys for this namespace are: {valid_keys}"
        )
