"""Shared utilities for metadata models."""

import unicodedata


def sanitize_for_vector_id(name: str) -> str:
    """
    Sanitize a string for use in Pinecone vector IDs.

    Pinecone requires ASCII-only vector IDs. This normalizes Unicode
    (e.g., smart quotes → ASCII quotes), replaces spaces/slashes with
    underscores, and drops any remaining non-ASCII characters.

    Args:
        name: Raw string (file name, provider, etc.).

    Returns:
        ASCII-safe string suitable for vector IDs.
    """
    # Reason: NFKD decomposes characters like 'e' + combining accent,
    # and maps smart quotes/dashes to their ASCII equivalents.
    normalized = unicodedata.normalize("NFKD", name)
    ascii_safe = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_safe.replace(" ", "_").replace("/", "_")
