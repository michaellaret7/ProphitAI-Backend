"""
Voyage AI embeddings generator for RAG pipelines.

Generates embeddings from text chunks using Voyage AI's finance-optimized model.
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

import voyageai  # type: ignore[import-untyped]
from dotenv import load_dotenv

from pydantic import BaseModel

from app.core.foundry.models.chunk import Chunk

if TYPE_CHECKING:
    from app.core.foundry.embeddings.sparse_encoder import SparseEncoder

load_dotenv()

def embed_chunks(
    chunks: list[Chunk],
    model: str = "voyage-finance-2",
    sparse_encoder: Optional[SparseEncoder] = None,
    batch_size: int = 512,
) -> list[Chunk]:
    """
    Embed a list of chunks using Voyage AI.

    Populates the embedding field on each Chunk object. Optionally generates
    sparse embeddings for hybrid search when a sparse_encoder is provided.

    Args:
        chunks: List of Chunk objects from the chunking pipeline.
        model: Voyage AI model. Default "voyage-finance-2".
            Options: voyage-finance-2, voyage-3, voyage-3-lite.
        sparse_encoder: Optional SparseEncoder for generating BM25 sparse vectors.
        batch_size: Texts per API call. Default 512.

    Returns:
        List of Chunk objects with embedding (and optionally sparse_embedding) populated.

    Raises:
        ValueError: If VOYAGE_API_KEY is not set.
    """
    if not chunks:
        return []

    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise ValueError("VOYAGE_API_KEY environment variable not set")

    client = voyageai.Client(api_key=api_key)
    texts = [chunk.text for chunk in chunks]

    # Reason: Process in batches to respect API limits
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embed(
            texts=batch,
            model=model,
            input_type="document",
        )
        # Reason: Cast to float to satisfy type checker
        for emb in response.embeddings:
            all_embeddings.append([float(x) for x in emb])

    # Reason: Generate sparse embeddings if encoder provided
    sparse_embeddings: list[dict | None] = []
    if sparse_encoder is not None:
        for chunk in chunks:
            sparse_embeddings.append(sparse_encoder.encode(chunk.text))
    else:
        sparse_embeddings = [None] * len(chunks)

    # Reason: Return new Chunk objects with embeddings populated
    return [
        Chunk(
            text=chunk.text,
            start_index=chunk.start_index,
            end_index=chunk.end_index,
            token_count=chunk.token_count,
            metadata=chunk.metadata,
            embedding=embedding,
            sparse_embedding=sparse_emb,
        )
        for chunk, embedding, sparse_emb in zip(chunks, all_embeddings, sparse_embeddings)
    ]

class QueryEmbedding(BaseModel):
    """Result of embedding a query for hybrid search."""

    dense: list[float]
    sparse: Optional[dict] = None

def embed_query(
    text: str,
    model: str = "voyage-finance-2",
    sparse_encoder: Optional[SparseEncoder] = None,
) -> QueryEmbedding:
    """
    Embed a query string for similarity search.

    Uses input_type="query" which Voyage recommends for search queries
    (vs "document" for content being indexed). Optionally generates a sparse
    vector for hybrid search when a sparse_encoder is provided.

    Args:
        text: Query text to embed.
        model: Voyage AI model. Default "voyage-finance-2".
        sparse_encoder: Optional SparseEncoder for generating BM25 sparse query vector.

    Returns:
        QueryEmbedding with dense vector and optionally sparse vector.

    Raises:
        ValueError: If VOYAGE_API_KEY is not set.
    """
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise ValueError("VOYAGE_API_KEY environment variable not set")

    client = voyageai.Client(api_key=api_key)
    response = client.embed(
        texts=[text],
        model=model,
        input_type="query",
    )
    dense = [float(x) for x in response.embeddings[0]]

    sparse = None
    if sparse_encoder is not None:
        sparse = sparse_encoder.encode_query(text)

    return QueryEmbedding(dense=dense, sparse=sparse)



