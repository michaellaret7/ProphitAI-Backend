"""
Document routes for file uploads and ingestion.

Provides endpoints for uploading documents (PDFs) to S3 and ingesting them
into the RAG pipeline.
"""

from typing import List

from fastapi import APIRouter, File, UploadFile, Depends, Query

from app.api.controller.foundry.document import upload_and_ingest_controller
from app.api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["Documents"])


@router.post("/documents/upload-and-ingest")
async def upload_and_ingest(
    files: List[UploadFile] = File(..., description="One or more PDF files to upload"),
    clerk_id: str = Depends(get_clerk_user_id),
    delete_after_ingestion: bool = Query(
        default=True,
        description="Delete S3 documents after successful ingestion",
    ),
):
    """
    Upload documents to S3 and immediately ingest into the RAG pipeline.

    Unified endpoint that combines upload and ingestion in a single operation.
    Files are uploaded to S3, then processed through the pipeline into Pinecone.

    Returns upload metadata and ingestion results.
    """
    return await upload_and_ingest_controller(
        files=files,
        clerk_id=clerk_id,
        delete_after_ingestion=delete_after_ingestion,
    )
