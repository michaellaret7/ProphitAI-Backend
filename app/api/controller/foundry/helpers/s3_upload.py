"""
S3 upload helpers for document operations.

Provides utilities for uploading files to S3.
"""

import os
import logging
from typing import Dict, Any

from fastapi import UploadFile, HTTPException
import boto3
from botocore.exceptions import ClientError

from app.api.controller.foundry.helpers.validation import validate_upload_file


logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "prophitai-s3-bucket")
USER_UPLOADS_PREFIX = "pdfs/user_uploads"


def get_s3_client():
    """Get boto3 S3 client."""
    return boto3.client("s3")


def build_s3_key(clerk_id: str, filename: str) -> str:
    """
    Build the S3 key for a user upload (goes to not_embedded folder).

    Args:
        clerk_id: The authenticated user's Clerk ID.
        filename: Sanitized filename.

    Returns:
        Full S3 key path: pdfs/user_uploads/{clerk_id}/not_embedded/{filename}
    """
    return f"{USER_UPLOADS_PREFIX}/{clerk_id}/not_embedded/{filename}"


async def upload_single_pdf(
    file: UploadFile,
    clerk_id: str,
    s3_client=None,
) -> Dict[str, Any]:
    """
    Upload a single PDF file to S3 after validation.

    Args:
        file: The uploaded file.
        clerk_id: The authenticated user's Clerk ID.
        s3_client: Optional boto3 S3 client instance. Creates one if not provided.

    Returns:
        Dict with upload metadata for this file.

    Raises:
        ValueError: If file validation fails.
        HTTPException: If S3 upload fails.
    """
    if s3_client is None:
        s3_client = get_s3_client()

    file_content, safe_filename = await validate_upload_file(file)
    file_size = len(file_content)
    content_type = file.content_type

    s3_key = build_s3_key(clerk_id, safe_filename)

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
        logger.error(f"S3 upload failed for '{file.filename}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload '{file.filename}' to storage.",
        )

    return {
        "s3Uri": f"s3://{S3_BUCKET}/{s3_key}",
        "s3Key": s3_key,
        "fileName": safe_filename,
        "fileSize": file_size,
        "contentType": content_type,
    }
