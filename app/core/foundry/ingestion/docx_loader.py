"""
Document ingestion module for RAG pipelines.

Handles plain text file extraction for .txt, .md, .rst, .json, .csv, and similar formats.
"""
import logging
from pathlib import Path

from app.core.foundry.models.ingestion_output import Document

logger = logging.getLogger(__name__)

# Supported text-based file extensions
SUPPORTED_EXTENSIONS: set[str] = {
    ".txt", ".md", ".rst", ".json", ".csv", ".xml", ".yaml", ".yml",
    ".html", ".htm", ".log", ".ini", ".cfg", ".conf", ".py", ".js",
    ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".sql"
}


class DocsIngestor:
    """
    A simple document ingestion class for RAG pipelines.

    Handles plain text files with various extensions. Reads content
    directly with configurable encoding.

    Attributes:
        encoding: File encoding (default: utf-8).
        include_filename: Include filename as header in output.
    """

    def __init__(
        self,
        encoding: str = "utf-8",
        include_filename: bool = False,
    ) -> None:
        """
        Initialize DocsIngestor with extraction options.

        Args:
            encoding: File encoding for reading text files.
            include_filename: Whether to include filename as header in output.
        """
        self.encoding = encoding
        self.include_filename = include_filename

    def process(self, file_path: str | Path) -> Document:
        """
        Main entry point to extract text from a document file.

        Args:
            file_path: Path to the document file.

        Returns:
            Document with content and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is not supported.
            RuntimeError: If extraction fails.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            logger.warning(f"Extension {suffix} not in known list, attempting read anyway")

        logger.info(f"Processing document: {path.name}")

        try:
            content = path.read_text(encoding=self.encoding)

            if self.include_filename:
                content = f"--- File: {path.name} ---\n{content}"

            metadata = {
                "filename": path.name,
                "extension": suffix,
                "size_bytes": path.stat().st_size,
                "char_count": len(content),
            }

            logger.debug(f"Extracted {len(content)} chars from {path.name}")

            return Document(
                content=content,
                metadata=metadata,
                source=str(path.absolute()),
            )

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {path.name}: {e}")
            raise RuntimeError(
                f"Failed to decode {path.name} with encoding '{self.encoding}'. "
                f"Try a different encoding."
            ) from e
        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            raise RuntimeError(f"Failed to extract document: {e}") from e
