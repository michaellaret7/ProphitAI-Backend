"""
Voyage AI embeddings generator for RAG pipelines.

Generates embeddings from text chunks using Voyage AI's finance-optimized model.
"""

import os

import voyageai  # type: ignore[import-untyped]
from dotenv import load_dotenv

from app.core.foundry.models.chunk import Chunk

load_dotenv()


def embed_chunks(
    chunks: list[Chunk],
    model: str = "voyage-finance-2",
    batch_size: int = 512,
) -> list[Chunk]:
    """
    Embed a list of chunks using Voyage AI.

    Populates the embedding field on each Chunk object.

    Args:
        chunks: List of Chunk objects from the chunking pipeline.
        model: Voyage AI model. Default "voyage-finance-2".
            Options: voyage-finance-2, voyage-3, voyage-3-lite.
        batch_size: Texts per API call. Default 128 (Voyage max).

    Returns:
        List of Chunk objects with embedding field populated.

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

    # Reason: Return new Chunk objects with embedding populated
    return [
        Chunk(
            text=chunk.text,
            start_index=chunk.start_index,
            end_index=chunk.end_index,
            token_count=chunk.token_count,
            metadata=chunk.metadata,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, all_embeddings)
    ]


def embed_query(
    text: str,
    model: str = "voyage-finance-2",
) -> list[float]:
    """
    Embed a query string for similarity search.

    Uses input_type="query" which Voyage recommends for search queries
    (vs "document" for content being indexed).

    Args:
        text: Query text to embed.
        model: Voyage AI model. Default "voyage-finance-2".

    Returns:
        Embedding vector as list of floats.

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
    return [float(x) for x in response.embeddings[0]]



