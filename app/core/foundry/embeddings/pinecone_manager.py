"""
Pinecone vector store manager for RAG pipelines.

Provides a unified interface for Pinecone vector operations including
CRUD, namespace management, and statistics.

Reference: https://docs.pinecone.io/reference/python-sdk
"""

import os
from typing import Any, Optional

from dotenv import load_dotenv
from pinecone import Pinecone

from app.core.foundry.models.chunk import Chunk
from app.core.foundry.models.vector import IndexStats, QueryResult, VectorRecord

load_dotenv()


class PineconeManager:
    """
    Manager for Pinecone vector database operations.

    Handles vector CRUD, namespace operations, and statistics retrieval.

    Attributes:
        client: Pinecone client instance.
        index: Current Pinecone index instance (set after connect_index).
        index_name: Name of the connected index.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Pinecone manager.

        Args:
            api_key: Pinecone API key. If not provided, reads from
                PINECONE_API_KEY environment variable.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        api_key = api_key or os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")

        self.client = Pinecone(api_key=api_key)
        self.index = None
        self.index_name: Optional[str] = None

    def connect_index(self, name: str) -> None:
        """
        Connect to an existing index for vector operations.

        Args:
            name: Index name to connect to.
        """
        self.index = self.client.Index(name)
        self.index_name = name

    # =========================================================================
    # Vector Operations
    # =========================================================================

    def _ensure_index(self) -> Any:
        """Ensure an index is connected and return it."""
        if self.index is None:
            raise RuntimeError("No index connected. Call connect_index() first.")
        return self.index

    def upsert(
        self,
        vectors: list[VectorRecord],
        namespace: Optional[str] = None,
        batch_size: int = 100,
    ) -> int:
        """
        Insert or update vectors in the index.

        Args:
            vectors: List of VectorRecord objects to upsert.
            namespace: Target namespace. Default uses default namespace.
            batch_size: Vectors per batch. Default 100.

        Returns:
            Number of vectors upserted.
        """
        index = self._ensure_index()

        pinecone_vectors = []
        for v in vectors:
            vec_dict = {"id": v.id, "values": v.values, "metadata": v.metadata}
            if v.sparse_values:
                vec_dict["sparse_values"] = v.sparse_values
            pinecone_vectors.append(vec_dict)

        total_upserted = 0
        for i in range(0, len(pinecone_vectors), batch_size):
            batch = pinecone_vectors[i : i + batch_size]
            index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)

        return total_upserted

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        namespace: Optional[str] = None,
        batch_size: int = 100,
    ) -> int:
        """
        Upsert embedded Chunk objects to Pinecone.

        Vector IDs are generated from chunk metadata in the format:
        {ticker}_{doc_type}_{doc_name}_{chunk_index}

        Args:
            chunks: List of Chunk objects with embeddings. Each chunk's metadata
                must contain: ticker, doc_type, doc_name, chunk_index.
            namespace: Target namespace.
            batch_size: Vectors per batch. Default 100.

        Returns:
            Number of vectors upserted.

        Raises:
            ValueError: If any chunk is missing an embedding or required metadata.
        """
        self._ensure_index()

        vectors = []
        for i, chunk in enumerate(chunks):
            if chunk.embedding is None:
                raise ValueError(f"Chunk at index {i} has no embedding")

            metadata = chunk.metadata
            required_fields = ["ticker", "doc_type", "doc_name", "chunk_index"]
            missing = [f for f in required_fields if f not in metadata]
            if missing:
                raise ValueError(
                    f"Chunk at index {i} missing required metadata: {missing}"
                )

            vec_id = (
                f"{metadata['ticker']}_{metadata['doc_type']}_"
                f"{metadata['doc_name']}_{metadata['chunk_index']}"
            )

            flat_metadata = self._flatten_metadata(metadata)
            flat_metadata["text"] = chunk.text[:1000]

            vectors.append(
                VectorRecord(
                    id=vec_id,
                    values=chunk.embedding,
                    metadata=flat_metadata,
                )
            )

        return self.upsert(vectors, namespace=namespace, batch_size=batch_size)

    def query(
        self,
        vector: list[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter: Optional[dict] = None,
        include_values: bool = False,
        include_metadata: bool = True,
    ) -> list[QueryResult]:
        """
        Query the index for similar vectors.

        Args:
            vector: Query vector.
            top_k: Number of results to return. Default 10.
            namespace: Namespace to search. Default searches default namespace.
            filter: Metadata filter expression.
            include_values: Include vector values in results. Default False.
            include_metadata: Include metadata in results. Default True.

        Returns:
            List of QueryResult objects sorted by similarity.
        """
        index = self._ensure_index()

        response = index.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_values=include_values,
            include_metadata=include_metadata,
        )

        return [
            QueryResult(
                id=match.id,
                score=match.score,
                values=match.values if include_values else None,
                metadata=match.metadata or {},
            )
            for match in response.matches
        ]

    def fetch(
        self,
        ids: list[str],
        namespace: Optional[str] = None,
    ) -> dict[str, VectorRecord]:
        """
        Fetch specific vectors by ID.

        Args:
            ids: List of vector IDs to fetch.
            namespace: Namespace to fetch from.

        Returns:
            Dict mapping IDs to VectorRecord objects.
        """
        index = self._ensure_index()

        response = index.fetch(ids=ids, namespace=namespace)

        result = {}
        for vec_id, vec_data in response.vectors.items():
            result[vec_id] = VectorRecord(
                id=vec_id,
                values=vec_data.values,
                metadata=vec_data.metadata or {},
            )
        return result

    def update(
        self,
        id: str,
        values: Optional[list[float]] = None,
        set_metadata: Optional[dict] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """
        Update an existing vector.

        Args:
            id: Vector ID to update.
            values: New vector values (optional).
            set_metadata: Metadata to merge with existing (optional).
            namespace: Namespace containing the vector.
        """
        index = self._ensure_index()

        index.update(
            id=id,
            values=values,
            set_metadata=set_metadata,
            namespace=namespace,
        )

    def delete(
        self,
        ids: Optional[list[str]] = None,
        delete_all: bool = False,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """
        Delete vectors from the index.

        Use one of: ids, delete_all, or filter (mutually exclusive).

        Args:
            ids: Specific vector IDs to delete.
            delete_all: Delete all vectors in namespace. Default False.
            filter: Metadata filter for selective deletion.
            namespace: Target namespace.
        """
        index = self._ensure_index()

        index.delete(
            ids=ids,
            delete_all=delete_all,
            filter=filter,
            namespace=namespace,
        )

    def list_vectors(
        self,
        prefix: str = "",
        limit: int = 100,
        namespace: Optional[str] = None,
    ) -> list[str]:
        """
        List vector IDs in the index.

        Args:
            prefix: ID prefix to filter by.
            limit: Maximum IDs to return. Default 100.
            namespace: Namespace to list from.

        Returns:
            List of vector IDs.
        """
        index = self._ensure_index()

        all_ids: list[str] = []
        pagination_token = None

        while True:
            response = index.list_paginated(
                prefix=prefix,
                limit=min(limit - len(all_ids), 100),
                pagination_token=pagination_token,
                namespace=namespace,
            )

            if response.vectors:
                all_ids.extend([v.id for v in response.vectors])

            if not response.pagination or len(all_ids) >= limit:
                break
            pagination_token = response.pagination.next

        return all_ids[:limit]

    # =========================================================================
    # Namespace Operations
    # =========================================================================

    def list_namespaces(self) -> list[str]:
        """
        List all namespaces in the connected index.

        Returns:
            List of namespace names.
        """
        index = self._ensure_index()
        stats = index.describe_index_stats()
        return list(stats.namespaces.keys())

    def delete_namespace(self, namespace: str) -> None:
        """
        Delete an entire namespace and all its vectors.

        Args:
            namespace: Namespace to delete.
        """
        index = self._ensure_index()
        index.delete(delete_all=True, namespace=namespace)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self, filter: Optional[dict] = None) -> IndexStats:
        """
        Get index statistics.

        Args:
            filter: Optional metadata filter to scope statistics.

        Returns:
            IndexStats with dimension, counts, and namespace breakdown.
        """
        index = self._ensure_index()

        stats = index.describe_index_stats(filter=filter)

        namespace_counts = {}
        for ns_name, ns_data in stats.namespaces.items():
            namespace_counts[ns_name] = ns_data.vector_count

        return IndexStats(
            dimension=stats.dimension,
            total_vector_count=stats.total_vector_count,
            namespaces=namespace_counts,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _flatten_metadata(self, metadata: dict) -> dict:
        """
        Flatten nested metadata for Pinecone compatibility.

        Pinecone only supports flat metadata with primitive types.

        Args:
            metadata: Original metadata dict (may be nested).

        Returns:
            Flattened metadata dict.
        """
        flat = {}
        for key, value in metadata.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    flat[f"{key}_{nested_key}"] = nested_value
            elif isinstance(value, (str, int, float, bool)):
                flat[key] = value
            elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                flat[key] = value
            else:
                flat[key] = str(value)
        return flat


if __name__ == "__main__":
    from app.core.foundry.chunking.semantic import SemanticChunker
    from app.repositories.transcripts_data import get_latest_transcript

    transcript = get_latest_transcript("CRWV")

    chunker = SemanticChunker()
    chunks = chunker.chunk(
        transcript["content"],
        doc_type="transcript",
        metadata={
            "ticker": "CRWV",
            "doc_name": f"{transcript['period']}_{transcript['year']}",
            "quarter": transcript["period"],
            "year": transcript["year"],
            "date": transcript["date"],
        }
    )

    for chunk in chunks:
        print(chunk.metadata)

