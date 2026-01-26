"""
Controller for document operations (upload, etc.).

Handles business logic for document uploads to S3.
"""

import os
import logging
from typing import Dict, Any
from fastapi import HTTPException, UploadFile

import boto3
from botocore.exceptions import ClientError

from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors
from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "prophitai-s3-bucket")

# Allowed file types for upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
}
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _get_s3_client():
    """Get boto3 S3 client."""
    return boto3.client("s3")


@handle_controller_errors
async def upload_pdf_controller(
    *,
    file: UploadFile,
    clerk_id: str,
) -> Dict[str, Any]:
    """
    Upload a PDF file to S3.

    Uploads to: s3://{bucket}/pdfs/user_uploads/{user_id}/{filename}

    Args:
        file: The uploaded file.
        clerk_id: The authenticated user's Clerk ID.

    Returns:
        Response with S3 URI and upload metadata.

    Raises:
        ValueError: If file type is invalid or file is too large.
        HTTPException: If S3 upload fails.
    """
    # Validate content type
    content_type = file.content_type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Invalid file type: {content_type}. Only PDF files are allowed."
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File too large: {file_size / (1024 * 1024):.1f}MB. "
            f"Maximum allowed: {MAX_FILE_SIZE_MB}MB."
        )

    if file_size == 0:
        raise ValueError("File is empty.")

    # Build S3 key: pdfs/user_uploads/{user_id}/{filename}
    original_filename = file.filename or "document.pdf"
    # Sanitize filename (remove path separators)
    safe_filename = original_filename.replace("/", "_").replace("\\", "_")
    s3_key = f"pdfs/user_uploads/{clerk_id}/{safe_filename}"

    # Upload to S3
    s3_client = _get_s3_client()
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            Metadata={
                "user_id": clerk_id,
                "original_name": safe_filename,
            },
        )
        logger.info(f"Uploaded PDF to S3: s3://{S3_BUCKET}/{s3_key}")
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload file to storage.",
        )

    s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
    uploaded_at = get_current_utc_time().isoformat() + "Z"

    return ok_envelope(
        message="PDF uploaded successfully",
        kind="documents#uploadResult",
        resource_id=safe_filename,
        self_link=f"/api/documents/upload",
        payload={
            "s3Uri": s3_uri,
            "fileName": safe_filename,
            "fileSize": file_size,
            "contentType": content_type,
            "uploadedAt": uploaded_at,
        },
    )
