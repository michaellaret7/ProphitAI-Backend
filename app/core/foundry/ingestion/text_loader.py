"""
Text document ingestion module for RAG pipelines.

Handles plain text files (.txt, .md) with metadata extraction.
"""
import logging
from pathlib import Path

from app.core.foundry.models.ingestion_output import Document

logger = logging.getLogger(__name__)

class TextIngestor:
    """
    Loader for plain text documents (.txt, .md).

    Extracts text content and basic metadata from text files.

    Attributes:
        encoding: File encoding for reading text files.
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        """
        Initialize TextIngestor.

        Args:
            encoding: File encoding for reading text files.
        """
        self.encoding = encoding

    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".txt", ".md"]

    def process(self, source: Path | str) -> Document:
        """
        Load a text document from file.

        Args:
            source: Path to the text file.

        Returns:
            Document with content and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file extension is not supported.
            RuntimeError: If extraction fails.
        """
        path = Path(source)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")

        if path.suffix.lower() not in self.supported_extensions():
            raise ValueError(
                f"Unsupported extension: {path.suffix}. "
                f"Supported: {self.supported_extensions()}"
            )

        logger.info(f"Loading text document: {path.name}")

        try:
            content = path.read_text(encoding=self.encoding)

            metadata = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "char_count": len(content),
            }

            logger.debug(f"Loaded {len(content)} chars from {path.name}")

            return Document(
                content=content,
                metadata=metadata,
                source=str(path.absolute()),
            )

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {path.name}: {e}")
            raise RuntimeError(
                f"Failed to decode {path.name} with encoding '{self.encoding}'."
            ) from e
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise RuntimeError(f"Failed to load text document: {e}") from e

    def process_text(self, text: str, source_name: str = "raw_text") -> Document:
        """
        Create a Document from raw text string.

        Args:
            text: The raw text content.
            source_name: Identifier for the text source.

        Returns:
            Document with content and metadata.
        """
        logger.info(f"Processing raw text: {source_name}")

        metadata = {
            "filename": source_name,
            "extension": None,
            "size_bytes": len(text.encode(self.encoding)),
            "char_count": len(text),
        }

        return Document(
            content=text,
            metadata=metadata,
            source=source_name,
        )


if __name__ == "__main__":
    from app.repositories.transcripts_data import get_latest_transcript
    transcript = get_latest_transcript("AAPL")

    ingestor = TextIngestor()
    document = ingestor.process_text(transcript["content"], 'AAPL_MOST_RECENT_TRANSCRIPT')
    print(document.metadata)