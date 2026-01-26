"""
Document routes for file uploads.

Provides endpoints for uploading documents (PDFs) to S3.
"""

from fastapi import APIRouter, File, UploadFile, Depends

from app.api.controller.document import upload_pdf_controller
from app.api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["Documents 📄"])


@router.post("/documents/upload")
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """
    Upload a PDF document to S3.

    Requires authentication. The file is stored at:
    s3://bucket/pdfs/user_uploads/{clerk_id}/{filename}

    Returns the S3 URI which can be used for ingestion.
    """
    return await upload_pdf_controller(file=file, clerk_id=clerk_id)
