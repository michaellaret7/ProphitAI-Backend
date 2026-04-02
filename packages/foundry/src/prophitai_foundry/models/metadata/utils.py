"""Shared utilities for metadata models."""

from pathlib import Path
import re
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


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """
    Parse an S3 URI into bucket and key components.

    Args:
        s3_uri: S3 URI in format ``s3://bucket/key``.

    Returns:
        Tuple of ``(bucket, key)``.
    """
    path = s3_uri.replace("s3://", "", 1)
    parts = path.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return parts[0], parts[1]


def split_file_name(file_path: str) -> tuple[str, str]:
    """
    Split a file path into stem and extension.

    Args:
        file_path: Full file path or file name.

    Returns:
        Tuple of ``(file_name_without_extension, extension_without_dot)``.
    """
    path = Path(file_path)
    file_name = path.stem
    file_extension = path.suffix.lstrip(".") or "pdf"
    return file_name, file_extension


def infer_source_id(file_name: str) -> str | None:
    """
    Infer a stable external source identifier from a file name.

    Supports common research-paper naming patterns like
    ``arxiv_2312.15730_*`` and ``ssrn_5278107_*``.

    Args:
        file_name: File name without extension.

    Returns:
        Stable source identifier such as ``arxiv:2312.15730`` or
        ``ssrn:5278107`` if recognized, otherwise ``None``.
    """
    lowered = file_name.lower()

    arxiv_match = re.match(r"^arxiv[_:-]?(\d{4}\.\d{4,5}(?:v\d+)?)\b", lowered)
    if arxiv_match:
        return f"arxiv:{arxiv_match.group(1)}"

    ssrn_match = re.match(r"^ssrn[_:-]?(\d+)\b", lowered)
    if ssrn_match:
        return f"ssrn:{ssrn_match.group(1)}"

    return None
