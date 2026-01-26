"""
Document routes for file uploads.

Provides endpoints for uploading documents (PDFs) to S3.
"""

from typing import List

from fastapi import APIRouter, File, UploadFile, Depends

from app.api.controller.foundry.document import upload_pdfs_controller
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
