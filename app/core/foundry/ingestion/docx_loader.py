"""
Document ingestion module for RAG pipelines.

Handles plain text file extraction for .rst, .json, .csv, .xml, .yaml, and similar formats.
"""
import logging

logger = logging.getLogger(__name__)


class DocsHandler:
    """
    Document extraction handler for RAG pipelines.

    Accepts bytes and decodes to text string for various text-based formats.

    Attributes:
        encoding: File encoding for decoding bytes.
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        """
        Initialize DocsHandler.

        Args:
            encoding: File encoding for decoding bytes.
        """
        self.encoding = encoding

    def extract(self, data: bytes) -> str:
        """
        Extract text from bytes.

        Args:
            data: Document file content as bytes.

        Returns:
            Decoded text content.

        Raises:
            RuntimeError: If decoding fails.
        """
        try:
            content = data.decode(self.encoding)
            logger.debug(f"Decoded {len(content)} chars using {self.encoding}")
            return content

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error: {e}")
            raise RuntimeError(
                f"Failed to decode with encoding '{self.encoding}'. "
                f"Try a different encoding."
            ) from e
