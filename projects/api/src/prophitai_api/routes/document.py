"""
Document routes for file uploads and ingestion.

Provides endpoints for uploading documents (PDFs) to S3 and ingesting them
into the RAG pipeline.
"""

from typing import List

from fastapi import APIRouter, File, UploadFile, Depends, Query

from prophitai_api.controllers.foundry.document import (
    upload_and_ingest_controller,
    get_user_documents_controller,
)
from prophitai_api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["Documents"])


@router.post("/documents/upload-and-ingest")
async def upload_and_ingest(
    files: List[UploadFile] = File(..., description="One or more PDF files to upload"),
    clerk_id: str = Depends(get_clerk_user_id),
    move_to_embedded: bool = Query(
        default=True,
        description="Move S3 documents from not_embedded to embedded folder after successful ingestion",
    ),
):
    """
    Upload documents to S3 and immediately ingest into the RAG pipeline.

    Unified endpoint that combines upload and ingestion in a single operation.
    Files are uploaded to S3 (not_embedded folder), then processed through the pipeline into Pinecone.
    After successful ingestion, files are moved to the embedded folder.

    Returns upload metadata and ingestion results.
    """
    return await upload_and_ingest_controller(
        files=files,
        clerk_id=clerk_id,
        move_to_embedded=move_to_embedded,
    )


@router.get("/documents/user")
async def get_user_documents(
    clerk_id: str = Depends(get_clerk_user_id),
):
    """
    Get all embedded documents for the authenticated user.

    Returns a list of documents that have been successfully embedded from the user's S3 folder.
    """
    return await get_user_documents_controller(clerk_id=clerk_id)
