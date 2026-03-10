"""
Main document ingestion module for RAG pipelines.

Provides a unified interface for ingesting documents from S3 or local paths.
"""
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

from app.core.foundry.models.document import Document
from app.core.foundry.ingestion.config import SUPPORTED_EXTENSIONS

from dotenv import load_dotenv

load_dotenv()

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

logger = logging.getLogger(__name__)

class Ingestor:
    """
    Unified document ingestion class for RAG pipelines.

    Handles fetching documents from S3 or local filesystem and routing
    to appropriate handlers based on file extension.

    Attributes:
        high_fidelity_pdf: Use docling for PDF extraction (better quality, slower).
        s3_client: Boto3 S3 client for fetching from S3.
    """

    def __init__(
        self,
        high_fidelity_pdf: bool = True,
        s3_client: Optional[boto3.client] = None,
        use_modal_gpu: bool = True,
    ) -> None:
        """
        Initialize Ingestor.

        Args:
            high_fidelity_pdf: Use docling for PDF extraction.
            s3_client: Optional boto3 S3 client. Created lazily if not provided.
            use_modal_gpu: Use Modal GPU for PDF extraction (requires deployed Modal app).
        """
        self.high_fidelity_pdf = high_fidelity_pdf
        self._s3_client = s3_client
        self.use_modal_gpu = use_modal_gpu

        # Lazy-loaded handlers
        self._pdf_handler = None
        self._excel_handler = None
        self._text_handler = None
        self._modal_client = None

    @property
    def s3_client(self):
        """Lazy-load S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client("s3")
        return self._s3_client

    def process(self, source: str) -> Document:
        """
        Process a document from S3 or local path.

        Args:
            source: S3 URI (s3://bucket/key), HTTPS S3 URL, or local file path.

        Returns:
            Document with extracted content and metadata.

        Raises:
            FileNotFoundError: If local file does not exist.
            ValueError: If file extension is not supported.
            RuntimeError: If extraction fails.
        """
        if source.startswith("s3://"):
            return self._process_s3(source)
        elif self._is_s3_https_url(source):
            return self._process_s3_https(source)
        else:
            return self._process_local(source)

    def _is_s3_https_url(self, url: str) -> bool:
        """Check if URL is an HTTPS S3 URL."""
        return url.startswith("https://") and ".s3." in url and "amazonaws.com" in url

    def process_text(self, text: str, source_name: str = "raw_text") -> Document:
        """
        Process raw text directly (no file involved).

        Args:
            text: The raw text content.
            source_name: Identifier for the text source.

        Returns:
            Document with content and metadata.
        """
        metadata = {
            "file_name": source_name,
            "extension": None,
            "size_bytes": len(text.encode("utf-8")),
            "char_count": len(text),
            "source_type": "raw_text",
        }

        return Document(
            content=text,
            metadata=metadata,
            source=source_name,
        )

    def _process_s3(self, s3_uri: str) -> Document:
        """
        Process a document from S3 using s3:// URI.

        Args:
            s3_uri: S3 URI in format s3://bucket/key.

        Returns:
            Document with extracted content and metadata.
        """
        bucket, key = self._parse_s3_uri(s3_uri)
        return self._fetch_from_s3(bucket, key, s3_uri)

    def _process_s3_https(self, https_url: str) -> Document:
        """
        Process a document from S3 using HTTPS URL.

        Args:
            https_url: HTTPS S3 URL in format https://{bucket}.s3.{region}.amazonaws.com/{key}

        Returns:
            Document with extracted content and metadata.
        """
        bucket, key = self._parse_s3_https_url(https_url)
        return self._fetch_from_s3(bucket, key, https_url)

    def _fetch_from_s3(self, bucket: str, key: str, source: str) -> Document:
        """
        Fetch and process a document from S3.

        Args:
            bucket: S3 bucket name.
            key: S3 object key.
            source: Original source string for metadata.

        Returns:
            Document with extracted content and metadata.
        """
        extension = self._get_extension(key)
        filename = Path(key).name

        logger.info(f"Processing from S3: bucket={bucket}, key={key}")

        # For PDFs with Modal: send S3 URI directly (Modal downloads from S3)
        if extension == ".pdf" and self.use_modal_gpu:
            s3_uri = f"s3://{bucket}/{key}"
            content = self._get_modal_client().extract_from_s3(s3_uri)
            metadata = {
                "file_name": filename,
                "extension": extension,
                "char_count": len(content),
                "source_type": "s3",
                "s3_bucket": bucket,
                "s3_key": key,
            }
            return Document(content=content, metadata=metadata, source=source)

        # Standard path: fetch bytes locally then process
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            data = response["Body"].read()
            size_bytes = response["ContentLength"]
        except ClientError as e:
            logger.error(f"S3 fetch failed: {e}")
            raise FileNotFoundError(f"Failed to fetch from S3: {source}") from e

        content = self._extract(data, extension)

        metadata = {
            "file_name": filename,
            "extension": extension,
            "size_bytes": size_bytes,
            "char_count": len(content),
            "source_type": "s3",
            "s3_bucket": bucket,
            "s3_key": key,
        }

        return Document(content=content, metadata=metadata, source=source)

    def _process_local(self, file_path: str) -> Document:
        """
        Process a document from local filesystem.

        Args:
            file_path: Path to local file.

        Returns:
            Document with extracted content and metadata.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = self._get_extension(file_path)
        filename = path.name

        logger.info(f"Reading local file: {filename}")

        data = path.read_bytes()
        content = self._extract(data, extension)

        metadata = {
            "file_name": filename,
            "extension": extension,
            "size_bytes": path.stat().st_size,
            "char_count": len(content),
            "source_type": "local",
        }

        return Document(content=content, metadata=metadata, source=str(path.absolute()))

    def _extract(self, data: bytes, extension: str) -> str:
        """
        Route to appropriate handler based on extension.

        Args:
            data: File content as bytes.
            extension: File extension (e.g., ".pdf").

        Returns:
            Extracted text content.
        """
        handler_type = SUPPORTED_EXTENSIONS.get(extension)

        if handler_type is None:
            raise ValueError(
                f"Unsupported extension: {extension}. "
                f"Supported: {list(SUPPORTED_EXTENSIONS.keys())}"
            )

        if handler_type == "pdf":
            if self.use_modal_gpu:
                return self._get_modal_client().extract_from_bytes(data)
            return self._get_pdf_handler().extract(data, self.high_fidelity_pdf)
        elif handler_type == "excel":
            return self._get_excel_handler().extract(data, extension)
        elif handler_type == "text":
            return self._get_text_handler().extract(data)
        else:
            raise ValueError(f"Unknown handler type: {handler_type}")

    def _get_extension(self, path: str) -> str:
        """Extract lowercase extension from path."""
        return Path(path).suffix.lower()

    def _parse_s3_uri(self, s3_uri: str) -> tuple[str, str]:
        """
        Parse S3 URI into bucket and key.

        Args:
            s3_uri: S3 URI in format s3://bucket/key.

        Returns:
            Tuple of (bucket, key).
        """
        # Remove s3:// prefix
        path = s3_uri[5:]
        parts = path.split("/", 1)

        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI: {s3_uri}")

        return parts[0], parts[1]

    def _parse_s3_https_url(self, https_url: str) -> tuple[str, str]:
        """
        Parse HTTPS S3 URL into bucket and key.

        Args:
            https_url: HTTPS S3 URL in format https://{bucket}.s3.{region}.amazonaws.com/{key}

        Returns:
            Tuple of (bucket, key).
        """
        # Format: https://{bucket}.s3.{region}.amazonaws.com/{key}
        # Example: https://prophitai-s3-bucket.s3.us-east-1.amazonaws.com/pdfs/pdf_one.pdf

        # Remove https:// prefix
        url = https_url[8:]

        # Split into host and path
        parts = url.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 HTTPS URL: {https_url}")

        host, key = parts

        # Extract bucket from host (bucket.s3.region.amazonaws.com)
        bucket = host.split(".s3.")[0]

        if not bucket or not key:
            raise ValueError(f"Invalid S3 HTTPS URL: {https_url}")

        # URL-decode the key (handles %2C -> comma, + -> space, etc.)
        key = unquote_plus(key)

        return bucket, key

    async def process_batch_s3(self, s3_uris: list[str]) -> list[Document | None]:
        """
        Process multiple S3 PDFs in a single Modal batch call.

        Args:
            s3_uris: List of S3 URIs (s3://bucket/key format).

        Returns:
            List of Documents (or None for failed extractions) in same order as input.
        """
        if not s3_uris:
            return []

        # Filter to only PDFs that should use Modal
        pdf_uris = [uri for uri in s3_uris if self._get_extension(uri) == ".pdf"]

        if not pdf_uris:
            logger.warning("No PDF URIs provided for batch processing")
            return [None] * len(s3_uris)

        logger.info(f"Batch processing {len(pdf_uris)} PDFs via Modal")
        results = await self._get_modal_client().extract_batch_from_s3(pdf_uris)

        # Build Documents from results, preserving order
        documents: list[Document | None] = []
        result_map = {r["s3_uri"]: r for r in results}

        for uri in s3_uris:
            result = result_map.get(uri)
            if result is None or result.get("error"):
                error_msg = result.get("error", "URI not in results") if result else "URI not processed"
                logger.error(f"Failed to extract {uri}: {error_msg}")
                documents.append(None)
                continue

            bucket, key = self._parse_s3_uri(uri)
            documents.append(Document(
                content=result["content"],
                metadata={
                    "file_name": Path(key).name,
                    "extension": ".pdf",
                    "char_count": result.get("char_count", len(result["content"])),
                    "source_type": "s3",
                    "s3_bucket": bucket,
                    "s3_key": key,
                },
                source=uri,
            ))

        return documents

    def move_s3_to_embedded(self, s3_uri: str) -> bool:
        """
        Move an S3 object from not_embedded to embedded folder.

        Example:
            s3://bucket/pdfs/clerk_123/not_embedded/doc.pdf
            -> s3://bucket/pdfs/clerk_123/embedded/doc.pdf

        Args:
            s3_uri: S3 URI (s3://bucket/key) or HTTPS S3 URL.

        Returns:
            True if move succeeded, False otherwise.
        """
        try:
            if s3_uri.startswith("s3://"):
                bucket, key = self._parse_s3_uri(s3_uri)
            elif self._is_s3_https_url(s3_uri):
                bucket, key = self._parse_s3_https_url(s3_uri)
            else:
                logger.warning(f"Cannot move non-S3 URI: {s3_uri}")
                return False

            if "/not_embedded/" not in key:
                logger.warning(f"Path doesn't contain /not_embedded/: {key}")
                return False

            new_key = key.replace("/not_embedded/", "/embedded/")

            logger.info(f"Moving S3 object: {key} -> {new_key}")

            # Copy to embedded folder
            self.s3_client.copy_object(
                Bucket=bucket,
                Key=new_key,
                CopySource={"Bucket": bucket, "Key": key},
            )

            # Delete from not_embedded after successful copy
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Successfully moved to: s3://{bucket}/{new_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to move S3 object {s3_uri}: {e}")
            return False

    # Lazy handler getters
    def _get_modal_client(self):
        if self._modal_client is None:
            from app.core.foundry.ingestion.modal_ops.client import ModalPDFClient
            self._modal_client = ModalPDFClient()
        return self._modal_client

    def _get_pdf_handler(self):
        if self._pdf_handler is None:
            from app.core.foundry.ingestion.doc_loaders.pdf_loader import PDFHandler
            self._pdf_handler = PDFHandler()
        return self._pdf_handler

    def _get_excel_handler(self):
        if self._excel_handler is None:
            from app.core.foundry.ingestion.doc_loaders.excel_loader import ExcelHandler
            self._excel_handler = ExcelHandler()
        return self._excel_handler

    def _get_text_handler(self):
        if self._text_handler is None:
            from app.core.foundry.ingestion.doc_loaders.text_loader import TextHandler
            self._text_handler = TextHandler()
        return self._text_handler


