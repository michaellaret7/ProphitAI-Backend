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

from prophitai_foundry.models.chunk import Chunk

if TYPE_CHECKING:
    from prophitai_foundry.embeddings.sparse_encoder import SparseEncoder

load_dotenv()

class QueryEmbedding(BaseModel):
    """Result of embedding a query for hybrid search."""

    dense: list[float]
    sparse: Optional[dict] = None

VOYAGE_MAX_TOKENS = 120_000
VOYAGE_TOKEN_BUFFER = 20_000  # Safety buffer


def _batch_chunks_by_tokens(
    chunks: list[Chunk],
    max_tokens: int = VOYAGE_MAX_TOKENS - VOYAGE_TOKEN_BUFFER,
) -> list[list[Chunk]]:
    """Group chunks into batches that respect token limits."""
    batches: list[list[Chunk]] = []
    current_batch: list[Chunk] = []
    current_tokens = 0

    for chunk in chunks:
        chunk_tokens = chunk.token_count or len(chunk.text) // 4  # Fallback estimate

        if current_tokens + chunk_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(chunk)
        current_tokens += chunk_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def embed_chunks(
    chunks: list[Chunk],
    model: str = "voyage-finance-2",
    sparse_encoder: Optional[SparseEncoder] = None,
) -> list[Chunk]:
    """
    Embed a list of chunks using Voyage AI.

    Batches by token count to respect Voyage's 120k token limit per request.

    Args:
        chunks: List of Chunk objects from the chunking pipeline.
        model: Voyage AI model. Default "voyage-finance-2".
        sparse_encoder: Optional SparseEncoder for generating BM25 sparse vectors.

    Returns:
        List of Chunk objects with embedding (and optionally sparse_embedding) populated.
    """
    if not chunks:
        return []

    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise ValueError("VOYAGE_API_KEY environment variable not set")

    client = voyageai.Client(api_key=api_key)

    # Batch by token count to stay under Voyage's 120k limit
    batches = _batch_chunks_by_tokens(chunks)

    all_embeddings: list[list[float]] = []
    for batch in batches:
        texts = [chunk.text for chunk in batch]
        response = client.embed(
            texts=texts,
            model=model,
            input_type="document",
        )
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



