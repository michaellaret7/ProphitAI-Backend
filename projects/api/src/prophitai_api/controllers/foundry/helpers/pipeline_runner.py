"""
Pipeline execution helpers for document ingestion.

Provides utilities for running the RAG pipeline on user documents.
"""

import asyncio
import logging
from typing import Dict, Any, List

from prophitai_api.controllers.foundry.helpers.s3_upload import (
    get_s3_client,
    S3_BUCKET,
    USER_UPLOADS_PREFIX,
)
from prophitai_foundry.pipeline import Pipeline


logger = logging.getLogger(__name__)

USER_UPLOADS_NAMESPACE = "user_uploads"

def list_user_s3_documents(clerk_id: str, folder: str = "not_embedded") -> List[Dict[str, Any]]:
    """
    List all S3 documents in a user's folder.

    Args:
        clerk_id: The authenticated user's Clerk ID.
        folder: The folder to list documents from ("not_embedded" or "embedded").

    Returns:
        List of dicts with uri, metadata, filename, and size for each document.
    """
    s3_client = get_s3_client()
    prefix = f"{USER_UPLOADS_PREFIX}/{clerk_id}/{folder}/"

    documents = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Skip the directory marker itself
            if key == prefix:
                continue

            filename = key.split("/")[-1]
            documents.append({
                "uri": f"s3://{S3_BUCKET}/{key}",
                "key": key,
                "filename": filename,
                "size_bytes": obj.get("Size", 0),
                "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
                "metadata": {"user_id": clerk_id},
            })

    return documents

async def run_user_pipeline(
    clerk_id: str,
    s3_uris: List[Dict[str, Any]] | None = None,
    move_to_embedded: bool = True,
) -> Dict[str, Any]:
    """
    Run the RAG pipeline for a user's documents.

    Args:
        clerk_id: The authenticated user's Clerk ID.
        s3_uris: Optional list of S3 URIs to process. If None, lists all user docs from not_embedded folder.
        move_to_embedded: Move S3 documents from not_embedded to embedded folder after successful ingestion.

    Returns:
        Dict with pipeline results (documents_processed, vectors_upserted, namespace).

    Raises:
        ValueError: If no documents found for user.
    """
    if s3_uris is None:
        s3_uris = await asyncio.to_thread(list_user_s3_documents, clerk_id)

    if not s3_uris:
        raise ValueError(
            f"No documents found for user {clerk_id}. Upload documents first."
        )

    logger.info(f"Running pipeline for {len(s3_uris)} documents for user {clerk_id}")

    pipeline = Pipeline(
        namespace=USER_UPLOADS_NAMESPACE,
        doc_type="user_upload",
        chunker_type="semantic",
        move_to_embedded_after_success=move_to_embedded,
    )

    vectors_upserted = await pipeline.run(s3_uris=s3_uris)

    logger.info(f"Ingested {vectors_upserted} vectors for user {clerk_id}")

    return {
        "documents_processed": len(s3_uris),
        "vectors_upserted": vectors_upserted,
        "namespace": USER_UPLOADS_NAMESPACE,
    }
