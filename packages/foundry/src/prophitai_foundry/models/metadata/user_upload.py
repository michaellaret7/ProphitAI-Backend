"""
Metadata model for user-uploaded documents.

Simple metadata that tracks user ownership for filtering.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from prophitai_foundry.models.metadata.utils import sanitize_for_vector_id


class UserUploadMetadata(BaseModel):
    """
    Metadata for user-uploaded documents.

    Tracks user_id for filtering so users only access their own documents.

    Usage:
        meta = UserUploadMetadata.from_s3_uri(
            s3_uri="s3://bucket/pdfs/user_uploads/clerk_123/report.pdf",
            user_id="clerk_123",
        )
        chunks = chunker.chunk(content, metadata=meta.to_chunk_metadata())
    """

    user_id: str = Field(..., description="Clerk user ID who uploaded the document")
    file_name: str = Field(..., description="Original file name without extension")
    file_extension: str = Field(default="pdf", description="File extension")
    s3_key: Optional[str] = Field(None, description="Full S3 object key")

    @computed_field
    @property
    def doc_id(self) -> str:
        """Unique document identifier combining user_id and file_name."""
        safe_name = sanitize_for_vector_id(self.file_name)
        return f"user_upload:{self.user_id}:{safe_name}:{uuid.uuid4().hex[:8]}"

    @classmethod
    def from_s3_uri(cls, s3_uri: str, user_id: str) -> "UserUploadMetadata":
        """
        Extract metadata from an S3 URI for user uploads.

        Args:
            s3_uri: Full S3 URI (s3://bucket/pdfs/user_uploads/{user_id}/file.pdf).
            user_id: The Clerk user ID.

        Returns:
            UserUploadMetadata instance.
        """
        # Parse S3 URI: s3://bucket/key
        path = s3_uri.replace("s3://", "")
        parts = path.split("/", 1)
        s3_key = parts[1] if len(parts) > 1 else ""

        # Extract filename
        file_path = s3_key.split("/")[-1]
        if "." in file_path:
            name_parts = file_path.rsplit(".", 1)
            file_name = name_parts[0]
            file_extension = name_parts[1]
        else:
            file_name = file_path
            file_extension = "pdf"

        return cls(
            user_id=user_id,
            file_name=file_name,
            file_extension=file_extension,
            s3_key=s3_key,
        )

    def to_chunk_metadata(self) -> dict:
        """
        Convert to metadata dict for chunker.

        Returns:
            Dict with fields needed for chunk metadata and filtering.
        """
        return {
            "doc_id": self.doc_id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "document_type": "user_upload",
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
