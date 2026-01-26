"""
Pipeline execution helpers for document ingestion.

Provides utilities for running the RAG pipeline on user documents.
"""

import logging
from typing import Dict, Any, List

from app.api.controller.foundry.helpers.s3_upload import (
    get_s3_client,
    S3_BUCKET,
    USER_UPLOADS_PREFIX,
)
from app.core.foundry.pipeline import Pipeline


logger = logging.getLogger(__name__)

USER_UPLOADS_NAMESPACE = "user_uploads"

def list_user_s3_documents(clerk_id: str) -> List[Dict[str, Any]]:
    """
    List all S3 documents for a user.

    Args:
        clerk_id: The authenticated user's Clerk ID.

    Returns:
        List of dicts with uri and metadata for each document.
    """
    s3_client = get_s3_client()
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

def run_user_pipeline(
    clerk_id: str,
    s3_uris: List[Dict[str, Any]] | None = None,
    delete_after_ingestion: bool = True,
) -> Dict[str, Any]:
    """
    Run the RAG pipeline for a user's documents.

    Args:
        clerk_id: The authenticated user's Clerk ID.
        s3_uris: Optional list of S3 URIs to process. If None, lists all user docs.
        delete_after_ingestion: Delete S3 documents after successful ingestion.

    Returns:
        Dict with pipeline results (documents_processed, vectors_upserted, namespace).

    Raises:
        ValueError: If no documents found for user.
    """
    if s3_uris is None:
        s3_uris = list_user_s3_documents(clerk_id)

    if not s3_uris:
        raise ValueError(
            f"No documents found for user {clerk_id}. Upload documents first."
        )

    logger.info(f"Running pipeline for {len(s3_uris)} documents for user {clerk_id}")

    pipeline = Pipeline(
        namespace=USER_UPLOADS_NAMESPACE,
        doc_type="user_upload",
        chunker_type="semantic",
        delete_s3_after_success=delete_after_ingestion,
    )

    vectors_upserted = pipeline.run(s3_uris=s3_uris)

    logger.info(f"Ingested {vectors_upserted} vectors for user {clerk_id}")

    return {
        "documents_processed": len(s3_uris),
        "vectors_upserted": vectors_upserted,
        "namespace": USER_UPLOADS_NAMESPACE,
    }
