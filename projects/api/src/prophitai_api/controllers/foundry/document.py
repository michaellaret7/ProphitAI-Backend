"""
Controller for document operations (upload and ingestion).

Handles business logic for document uploads to S3 and ingestion into the RAG pipeline.
"""

import logging
from typing import Dict, Any, List

from fastapi import UploadFile

from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_api.controllers.foundry.helpers.s3_upload import (
    get_s3_client,
    upload_single_pdf,
)
from prophitai_api.controllers.foundry.helpers.pipeline_runner import (
    run_user_pipeline,
    list_user_s3_documents,
)
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_shared.time_utils import get_current_utc_time


logger = logging.getLogger(__name__)


@handle_controller_errors
async def upload_and_ingest_controller(
    *,
    files: List[UploadFile],
    clerk_id: str,
    move_to_embedded: bool = True,
) -> Dict[str, Any]:
    """
    Upload documents to S3 and immediately ingest into the RAG pipeline.

    Unified endpoint that combines upload and ingestion in a single operation.
    Files are uploaded to S3 (not_embedded folder), then the pipeline processes them into Pinecone.
    After successful ingestion, files are moved to the embedded folder.

    Args:
        files: List of uploaded files.
        clerk_id: The authenticated user's Clerk ID.
        move_to_embedded: Move S3 documents from not_embedded to embedded folder after successful ingestion.

    Returns:
        Response with upload and ingestion results.

    Raises:
        ValueError: If no files provided or file validation fails.
        HTTPException: If S3 upload or pipeline fails.
    """
    if not files:
        raise ValueError("No files provided.")

    s3_client = get_s3_client()
    uploaded_at = get_current_utc_time().isoformat() + "Z"

    # Step 1: Upload all files to S3 (not_embedded folder)
    uploaded_files = []
    s3_uris = []

    for file in files:
        result = await upload_single_pdf(file, clerk_id, s3_client)
        result["uploadedAt"] = uploaded_at
        uploaded_files.append(result)

        # Build S3 URI for pipeline
        s3_uris.append({
            "uri": result["s3Uri"],
            "metadata": {"user_id": clerk_id},
        })

    logger.info(f"Uploaded {len(uploaded_files)} files for user {clerk_id}")

    # Step 2: Run pipeline on uploaded documents
    pipeline_result = await run_user_pipeline(
        clerk_id=clerk_id,
        s3_uris=s3_uris,
        move_to_embedded=move_to_embedded,
    )

    file_count = len(uploaded_files)

    return ok_envelope(
        message=f"Uploaded and ingested {file_count} document{'s' if file_count > 1 else ''} "
                f"({pipeline_result['vectors_upserted']} vectors)",
        kind="documents#uploadAndIngestResult",
        resource_id=None,
        self_link="/api/documents/upload-and-ingest",
        payload={
            "uploadedFiles": uploaded_files,
            "totalFilesUploaded": file_count,
            "documentsProcessed": pipeline_result["documents_processed"],
            "vectorsUpserted": pipeline_result["vectors_upserted"],
            "namespace": pipeline_result["namespace"],
        },
    )


@handle_controller_errors
async def get_user_documents_controller(
    *,
    clerk_id: str,
) -> Dict[str, Any]:
    """
    Get all embedded documents for a user from S3.

    Args:
        clerk_id: The authenticated user's Clerk ID.

    Returns:
        Response with list of embedded documents.
    """
    documents = list_user_s3_documents(clerk_id, folder="embedded")

    return ok_envelope(
        message=f"Found {len(documents)} embedded document{'s' if len(documents) != 1 else ''}",
        kind="documents#userDocuments",
        resource_id=None,
        self_link="/api/documents/user",
        payload={
            "documents": documents,
            "totalDocuments": len(documents),
        },
    )
