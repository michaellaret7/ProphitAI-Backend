"""
Default metadata model for unrecognized document types.

Extracts basic info (file_name, doc_type) from S3 URI when no specific
metadata extractor exists for the doc_type.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

from app.core.foundry.models.metadata.utils import sanitize_for_vector_id


class DefaultMetadata(BaseModel):
    """
    Default metadata for documents without a specialized metadata extractor.

    Extracts file_name from S3 URI and uses the provided doc_type.
    Used as a fallback when doc_type doesn't match earnings_call, user_upload, etc.

    Usage:
        meta = DefaultMetadata.from_s3_uri(
            s3_uri="s3://bucket/pdfs/taxes/not_embedded/report.pdf",
            doc_type="tax_doc",
        )
        chunks = chunker.chunk(content, metadata=meta.to_chunk_metadata())
    """

    doc_type: str = Field(..., description="Document type (e.g., tax_doc, generic)")
    file_name: str = Field(..., description="Original file name without extension")
    file_extension: str = Field(default="pdf", description="File extension")
    s3_key: Optional[str] = Field(None, description="Full S3 object key")

    _doc_hash: str = PrivateAttr(default="")

    def model_post_init(self, _context) -> None:
        """Generate unique hash after model initialization."""
        self._doc_hash = uuid.uuid4().hex[:8]

    @property
    def doc_id(self) -> str:
        """Unique document identifier combining doc_type and file_name."""
        safe_name = sanitize_for_vector_id(self.file_name)
        return f"{self.doc_type}:{safe_name}:{self._doc_hash}"

    @classmethod
    def from_s3_uri(cls, s3_uri: str, doc_type: str) -> "DefaultMetadata":
        """
        Extract metadata from an S3 URI.

        Args:
            s3_uri: Full S3 URI (s3://bucket/path/to/file.pdf).
            doc_type: Document type to assign.

        Returns:
            DefaultMetadata instance.
        """
        # Parse S3 URI: s3://bucket/key
        path = s3_uri.replace("s3://", "")
        parts = path.split("/", 1)
        s3_key = parts[1] if len(parts) > 1 else ""

        # Extract filename from the path
        file_path = s3_key.split("/")[-1]
        if "." in file_path:
            name_parts = file_path.rsplit(".", 1)
            file_name = name_parts[0]
            file_extension = name_parts[1]
        else:
            file_name = file_path
            file_extension = "pdf"

        return cls(
            doc_type=doc_type,
            file_name=file_name,
            file_extension=file_extension,
            s3_key=s3_key,
        )

    @classmethod
    def from_text(cls, source_name: str, doc_type: str) -> "DefaultMetadata":
        """
        Create metadata for raw text input (non-S3).

        Args:
            source_name: Name/identifier for the text source.
            doc_type: Document type to assign.

        Returns:
            DefaultMetadata instance.
        """
        return cls(
            doc_type=doc_type,
            file_name=source_name,
            file_extension="txt",
            s3_key=None,
        )

    def to_chunk_metadata(self) -> dict:
        """
        Convert to metadata dict for chunker.

        Returns:
            Dict with fields needed for chunk metadata and filtering.
        """
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "file_name": self.file_name,
        }

    def build_chunk_id(self, chunk_index: int) -> str:
        """
        Build a unique chunk ID from the doc_id and chunk index.

        Args:
            chunk_index: 0-based index of the chunk.

        Returns:
            Chunk ID in format doc_id#NNNN.
        """
        return f"{self.doc_id}#{chunk_index:04d}"
