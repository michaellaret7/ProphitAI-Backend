"""
Controller for document operations (upload, ingestion).

Handles business logic for document uploads to S3 and ingestion into the RAG pipeline.
"""

import os
import logging
from typing import Dict, Any, List

from fastapi import HTTPException, UploadFile
import boto3
from botocore.exceptions import ClientError

from app.api.response_envelope import ok_envelope
from app.core.foundry.pipeline import Pipeline
from app.utils.decorators.api_decorators import handle_controller_errors
from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "prophitai-s3-bucket")
USER_UPLOADS_PREFIX = "pdfs/user_uploads"
USER_UPLOADS_NAMESPACE = "user_uploads"

# Allowed file types for upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
}
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _get_s3_client():
    """Get boto3 S3 client."""
    return boto3.client("s3")


def _list_user_s3_documents(clerk_id: str) -> List[Dict[str, Any]]:
    """
    List all S3 documents for a user.

    Args:
        clerk_id: The authenticated user's Clerk ID.

    Returns:
        List of dicts with uri and metadata for each document.
    """
    s3_client = _get_s3_client()
    prefix = f"{USER_UPLOADS_PREFIX}/{clerk_id}/"

    s3_uris = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Skip the directory marker itself
            if key == prefix:
                continue
            s3_uris.append({
                "uri": f"s3://{S3_BUCKET}/{key}",
                "metadata": {"user_id": clerk_id},
            })

    return s3_uris


async def _upload_single_pdf(
    file: UploadFile,
    clerk_id: str,
    s3_client,
) -> Dict[str, Any]:
    """
    Upload a single PDF file to S3.

    Args:
        file: The uploaded file.
        clerk_id: The authenticated user's Clerk ID.
        s3_client: Boto3 S3 client instance.

    Returns:
        Dict with upload metadata for this file.

    Raises:
        ValueError: If file type is invalid or file is too large.
        HTTPException: If S3 upload fails.
    """
    content_type = file.content_type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Invalid file type for '{file.filename}': {content_type}. Only PDF files are allowed."
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
    safe_filename = original_filename.replace("/", "_").replace("\\", "_")
    s3_key = f"pdfs/user_uploads/{clerk_id}/{safe_filename}"

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
        "fileName": safe_filename,
        "fileSize": file_size,
        "contentType": content_type,
    }


@handle_controller_errors
async def upload_pdfs_controller(
    *,
    files: List[UploadFile],
    clerk_id: str,
) -> Dict[str, Any]:
    """
    Upload one or more PDF files to S3.

    Uploads to: s3://{bucket}/pdfs/user_uploads/{clerk_id}/{filename}

    Args:
        files: List of uploaded files.
        clerk_id: The authenticated user's Clerk ID.

    Returns:
        Response with S3 URIs and upload metadata for all files.

    Raises:
        ValueError: If any file type is invalid or file is too large.
        HTTPException: If S3 upload fails.
    """
    if not files:
        raise ValueError("No files provided.")

    s3_client = _get_s3_client()
    uploaded_at = get_current_utc_time().isoformat() + "Z"

    uploaded_files = []
    for file in files:
        result = await _upload_single_pdf(file, clerk_id, s3_client)
        result["uploadedAt"] = uploaded_at
        uploaded_files.append(result)

    file_count = len(uploaded_files)
    message = f"{file_count} PDF{'s' if file_count > 1 else ''} uploaded successfully"

    return ok_envelope(
        message=message,
        kind="documents#bulkUploadResult",
        resource_id=None,
        self_link="/api/documents/upload",
        payload={
            "uploadedFiles": uploaded_files,
            "totalCount": file_count,
        },
    )


@handle_controller_errors
def ingest_user_documents_controller(
    *,
    clerk_id: str,
    delete_after_ingestion: bool = True,
) -> Dict[str, Any]:
    """
    Ingest all uploaded documents for a user into the RAG pipeline.

    Lists all PDFs in s3://{bucket}/pdfs/user_uploads/{clerk_id}/ and
    processes them through the foundry pipeline into Pinecone.

    Documents are embedded into the 'user_uploads' namespace with user_id
    metadata for filtering.

    Args:
        clerk_id: The authenticated user's Clerk ID.
        delete_after_ingestion: Delete S3 documents after successful ingestion.

    Returns:
        Response with ingestion results.

    Raises:
        ValueError: If no documents found for user.
    """
    s3_uris = _list_user_s3_documents(clerk_id)

    if not s3_uris:
        raise ValueError(f"No documents found for user {clerk_id}. Upload documents first.")

    logger.info(f"Ingesting {len(s3_uris)} documents for user {clerk_id}")

    pipeline = Pipeline(
        namespace=USER_UPLOADS_NAMESPACE,
        doc_type="user_upload",
        chunker_type="semantic",
        delete_s3_after_success=delete_after_ingestion,
    )

    vectors_upserted = pipeline.run(s3_uris=s3_uris)

    logger.info(f"Ingested {vectors_upserted} vectors for user {clerk_id}")

    return ok_envelope(
        message=f"Successfully ingested {len(s3_uris)} documents ({vectors_upserted} vectors)",
        kind="documents#ingestionResult",
        resource_id=None,
        self_link="/api/documents/ingest",
        payload={
            "documentsProcessed": len(s3_uris),
            "vectorsUpserted": vectors_upserted,
            "namespace": USER_UPLOADS_NAMESPACE,
        },
    )
