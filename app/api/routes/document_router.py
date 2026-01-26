"""
Document routes for file uploads and ingestion.

Provides endpoints for uploading documents (PDFs) to S3 and ingesting them
into the RAG pipeline.
"""

from typing import List

from fastapi import APIRouter, File, UploadFile, Depends, Query

from app.api.controller.foundry.document import (
    upload_pdfs_controller,
    ingest_user_documents_controller,
)
from app.api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["Documents 📄"])


@router.post("/documents/upload")
async def upload_pdfs(
    files: List[UploadFile] = File(..., description="One or more PDF files to upload"),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """
    Upload one or more PDF documents to S3.

    Requires authentication. Files are stored at:
    s3://bucket/pdfs/user_uploads/{clerk_id}/{filename}

    Returns S3 URIs for all uploaded files.
    """
    return await upload_pdfs_controller(files=files, clerk_id=clerk_id)


@router.post("/documents/ingest")
def ingest_documents(
    clerk_id: str = Depends(get_clerk_user_id),
    delete_after_ingestion: bool = Query(
        default=True,
        description="Delete S3 documents after successful ingestion",
    ),
):
    """
    Ingest uploaded documents into the RAG pipeline.

    Processes all PDFs previously uploaded by this user from S3 and embeds
    them into Pinecone. Documents are stored in the 'user_uploads' namespace
    with user_id metadata for filtering.

    Query your documents using the search API with user_id filter.
    """
    return ingest_user_documents_controller(
        clerk_id=clerk_id,
        delete_after_ingestion=delete_after_ingestion,
    )
