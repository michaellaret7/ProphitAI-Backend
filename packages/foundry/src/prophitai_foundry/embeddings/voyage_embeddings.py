"""
Voyage AI embeddings generator for RAG pipelines.

Generates embeddings from text chunks using Voyage AI's finance-optimized model.
"""

from __future__ import annotations

import math
import os
from typing import Optional, TYPE_CHECKING

import voyageai  # type: ignore[import-untyped]
import voyageai.error as voyage_error  # type: ignore[import-untyped]
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
VOYAGE_TOKEN_BUFFER = int(os.getenv("VOYAGE_EMBED_TOKEN_BUFFER", "35000"))
VOYAGE_TOKEN_ESTIMATE_MULTIPLIER = float(os.getenv("VOYAGE_EMBED_TOKEN_ESTIMATE_MULTIPLIER", "1.35"))
VOYAGE_CHUNK_OVERHEAD_TOKENS = int(os.getenv("VOYAGE_EMBED_CHUNK_OVERHEAD_TOKENS", "32"))


def _estimate_chunk_tokens(chunk: Chunk) -> int:
    """Inflate local token estimates to better match Voyage's server-side counting."""
    base_tokens = chunk.token_count or 0
    inflated_tokens = math.ceil(base_tokens * VOYAGE_TOKEN_ESTIMATE_MULTIPLIER) if base_tokens > 0 else 0
    char_floor_tokens = math.ceil(len(chunk.text) / 3) if chunk.text else 0
    return max(inflated_tokens, char_floor_tokens) + VOYAGE_CHUNK_OVERHEAD_TOKENS


def _sum_estimated_tokens(chunks: list[Chunk]) -> int:
    """Return the estimated token total for a batch of chunks."""
    return sum(_estimate_chunk_tokens(chunk) for chunk in chunks)


def _batch_chunks_by_tokens(
    chunks: list[Chunk],
    max_tokens: int = VOYAGE_MAX_TOKENS - VOYAGE_TOKEN_BUFFER,
) -> list[list[Chunk]]:
    """Group chunks into batches that respect token limits."""
    batches: list[list[Chunk]] = []
    current_batch: list[Chunk] = []
    current_tokens = 0

    for chunk in chunks:
        chunk_tokens = _estimate_chunk_tokens(chunk)

        if current_tokens + chunk_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(chunk)
        current_tokens += chunk_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def _is_batch_token_limit_error(exc: Exception) -> bool:
    """Return True when Voyage rejected a request for exceeding the batch token cap."""
    if not isinstance(exc, voyage_error.InvalidRequestError):
        return False

    error_text = str(exc).lower()
    return (
        "max allowed tokens per submitted batch" in error_text
        or "lower the number of tokens in the batch" in error_text
    )


def _split_batch(chunks: list[Chunk]) -> tuple[list[Chunk], list[Chunk]]:
    """Split a batch into two smaller batches near the halfway token mark."""
    if len(chunks) < 2:
        raise ValueError("Cannot split a batch with fewer than two chunks")

    target_tokens = _sum_estimated_tokens(chunks) / 2
    running_tokens = 0
    split_index = len(chunks) // 2

    for idx, chunk in enumerate(chunks, start=1):
        running_tokens += _estimate_chunk_tokens(chunk)
        if running_tokens >= target_tokens:
            split_index = idx
            break

    split_index = min(max(split_index, 1), len(chunks) - 1)
    return chunks[:split_index], chunks[split_index:]


def _embed_batch(
    client: voyageai.Client,
    batch: list[Chunk],
    *,
    model: str,
) -> list[list[float]]:
    """Embed one batch and recursively split if Voyage still rejects it."""
    texts = [chunk.text for chunk in batch]

    try:
        response = client.embed(
            texts=texts,
            model=model,
            input_type="document",
        )
    except voyage_error.InvalidRequestError as exc:
        if not _is_batch_token_limit_error(exc):
            raise

        if len(batch) == 1:
            chunk = batch[0]
            chunk_id = chunk.metadata.get("chunk_id", "<unknown>")
            estimated_tokens = _estimate_chunk_tokens(chunk)
            raise ValueError(
                "Voyage rejected a single chunk after client-side batching. "
                f"chunk_id={chunk_id}, estimated_tokens={estimated_tokens}"
            ) from exc

        left_batch, right_batch = _split_batch(batch)
        estimated_tokens = _sum_estimated_tokens(batch)
        print(
            "Voyage batch exceeded token limit; "
            f"retrying {len(batch)} chunks (~{estimated_tokens} estimated tokens) "
            f"as {len(left_batch)} + {len(right_batch)} chunks"
        )
        return _embed_batch(client, left_batch, model=model) + _embed_batch(client, right_batch, model=model)

    if len(response.embeddings) != len(batch):
        raise RuntimeError(
            f"Voyage returned {len(response.embeddings)} embeddings for {len(batch)} chunks"
        )

    return [[float(x) for x in embedding] for embedding in response.embeddings]


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
        all_embeddings.extend(_embed_batch(client, batch, model=model))

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

