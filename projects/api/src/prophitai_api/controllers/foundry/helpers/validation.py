"""
Validation helpers for document uploads.

Provides file validation and sanitization utilities.
"""

from typing import Tuple

from fastapi import UploadFile


# Allowed file types for upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
}
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing path separators and non-ASCII characters.

    Args:
        filename: Original filename from upload.

    Returns:
        Sanitized filename safe for S3 keys and metadata (ASCII-only).
    """
    sanitized = filename.replace("/", "_").replace("\\", "_")
    # Reason: S3 metadata only accepts ASCII characters — encode to ASCII,
    # replacing non-ASCII chars (e.g. curly quotes) with closest ASCII equivalents
    sanitized = sanitized.encode("ascii", errors="ignore").decode("ascii")
    return sanitized


async def validate_upload_file(file: UploadFile) -> Tuple[bytes, str]:
    """
    Validate an uploaded file for type, size, and content.

    Args:
        file: The uploaded file to validate.

    Returns:
        Tuple of (file_content, safe_filename).

    Raises:
        ValueError: If file type is invalid, file is too large, or file is empty.
    """
    content_type = file.content_type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Invalid file type for '{file.filename}': {content_type}. "
            "Only PDF files are allowed."
        )

    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File '{file.filename}' too large: {file_size / (1024 * 1024):.1f}MB. "
            f"Maximum allowed: {MAX_FILE_SIZE_MB}MB."
        )

    if file_size == 0:
        raise ValueError(f"File '{file.filename}' is empty.")

    original_filename = file.filename or "document.pdf"
    safe_filename = sanitize_filename(original_filename)

    return file_content, safe_filename
