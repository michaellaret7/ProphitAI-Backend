"""
Helper modules for foundry document controllers.

Provides reusable utilities for validation, S3 operations, and pipeline execution.
"""

from app.api.controller.foundry.helpers.validation import (
    validate_upload_file,
    sanitize_filename,
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_MB,
    MAX_FILE_SIZE_BYTES,
)
from app.api.controller.foundry.helpers.s3_upload import (
    get_s3_client,
    build_s3_key,
    upload_single_pdf,
    S3_BUCKET,
    USER_UPLOADS_PREFIX,
)
from app.api.controller.foundry.helpers.pipeline_runner import (
    list_user_s3_documents,
    run_user_pipeline,
    USER_UPLOADS_NAMESPACE,
)

__all__ = [
    # Validation
    "validate_upload_file",
    "sanitize_filename",
    "ALLOWED_CONTENT_TYPES",
    "MAX_FILE_SIZE_MB",
    "MAX_FILE_SIZE_BYTES",
    # S3 Upload
    "get_s3_client",
    "build_s3_key",
    "upload_single_pdf",
    "S3_BUCKET",
    "USER_UPLOADS_PREFIX",
    # Pipeline
    "list_user_s3_documents",
    "run_user_pipeline",
    "USER_UPLOADS_NAMESPACE",
]
