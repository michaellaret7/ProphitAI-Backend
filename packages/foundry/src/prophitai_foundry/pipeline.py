"""
Efficient batch ingestion pipeline for RAG.

Processes multiple texts and S3 documents in a single pass:
1. Ingest all (parallel S3 fetches)
2. Chunk all → collect all chunks
3. Embed all chunks in one batch call
4. Upsert all vectors in one batch call
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from functools import partial
from typing import Callable

from dotenv import load_dotenv

from prophitai_foundry.chunking.earnings_calls import EarningsCallChunker
from prophitai_foundry.chunking.recursive import RecursiveChunker
from prophitai_foundry.chunking.semantic import SemanticChunker
from prophitai_foundry.embeddings.pinecone_manager import PineconeManager
from prophitai_foundry.embeddings.sparse_encoder import SparseEncoder
from prophitai_foundry.embeddings.voyage_embeddings import embed_chunks
from prophitai_foundry.ingestion import Ingestor
from prophitai_foundry.models.chunk import Chunk
from prophitai_foundry.models.document import Document
from prophitai_foundry.models.metadata import (
    DefaultMetadata,
    EarningsCallMetadata,
    ResearchDocumentMetadata,
    TradingStrategyMetadata,
    UserUploadMetadata,
)

load_dotenv()

METADATA_KIND_BY_DOC_TYPE = {
    "earnings_call": "earnings_call",
    "user_upload": "user_upload",
    "macro_research": "research",
    "equity_research": "research",
    "ticker_research": "research",
    "credit": "research",
    "credit_research": "research",
    "strategy_research": "strategy",
    "trading_strategy_research": "strategy",
}

CANONICAL_DOC_TYPES = {
    "trading_strategy_research": "strategy_research",
}

@dataclass
class IngestedDoc:
    """Document with its associated metadata."""
    document: Document
    metadata: dict
    doc_id: str
    earnings_meta: EarningsCallMetadata | None = None
    research_meta: ResearchDocumentMetadata | None = None
    strategy_meta: TradingStrategyMetadata | None = None
    user_upload_meta: UserUploadMetadata | None = None
    default_meta: DefaultMetadata | None = None
    s3_uri: str | None = None  # Track S3 URI for cleanup after processing


CHUNKERS: dict[str, Callable] = {
    "earnings_call": lambda: EarningsCallChunker(),
    "semantic": lambda: SemanticChunker(),
    "recursive": lambda: RecursiveChunker(),
}

class Pipeline:
    """
    Pipeline for ingesting documents into the RAG system.
    
    Usage:
        pipeline = Pipeline(namespace="earnings_calls", doc_type="earnings_call")

        # Multiple texts
        count = pipe.run(texts=[
            {"content": "Operator: Good afternoon...", "metadata": {"ticker": "AAPL"}},
            {"content": "Operator: Welcome to...", "metadata": {"ticker": "MSFT"}},
        ])

        # Multiple S3 docs
        count = pipe.run(s3_uris=[
            {"uri": "s3://bucket/GOOG_Q4.pdf", "metadata": {"ticker": "GOOG"}},
        ])

        # Mixed
        count = pipe.run(texts=[...], s3_uris=[...])
    """

    def __init__(
        self,
        namespace: str = "earnings_calls",
        doc_type: str = "earnings_call",
        chunker_type: str = "earnings_call",
        move_to_embedded_after_success: bool = True,
    ):
        """
        Initialize the pipeline.

        Args:
            namespace: Pinecone namespace for vectors.
            doc_type: Document type for chunker selection.
            chunker_type: Type of chunker to use (earnings_call, semantic, recursive).
            move_to_embedded_after_success: Move S3 documents from not_embedded to embedded folder after successful processing.
        """
        print(f"Initializing Foundry Pipeline with namespace: {namespace}, doc_type: {doc_type}, chunker_type: {chunker_type}")

        self.namespace = namespace
        self.doc_type = doc_type
        self.move_to_embedded_after_success = move_to_embedded_after_success

        # Initialize components
        # Set Modal to true in the ingestion layer to use the modal GPU for pdf extraction
        self._ingestor = Ingestor(use_modal_gpu=True) # --> import deoc/text ingestion Object 

        self._sparse_encoder = SparseEncoder() # --> import sparse encoder Object
        self._sparse_encoder.load() # --> load the sparse encoder from the file system

        self._pinecone = PineconeManager() # --> import pinecone manager Object
        self._pinecone.connect_index( # --> connect to the pinecone index
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )

        self._chunker = CHUNKERS[chunker_type]() # --> get the chunker method for the document type

    async def run(
        self,
        texts: list[dict] | None = None,
        s3_uris: list[dict] | None = None,
        s3_batch_size: int = 3,
    ) -> int:
        """
        Process multiple texts and/or S3 documents.

        Args:
            texts: List of {"content": str, "metadata": dict}.
            s3_uris: List of {"uri": str, "metadata": dict}.
            s3_batch_size: Number of S3 PDFs per Modal batch call (default 3).

        Returns:
            Total number of vectors upserted.
        """
        texts = texts or []
        s3_uris = s3_uris or []

        if not texts and not s3_uris:
            return 0

        # Step 1: Ingest all documents (S3 processed in batches to avoid Modal timeout)
        ingested = await self._ingest_all(texts, s3_uris, s3_batch_size)
        if not ingested:
            return 0

        print(f"Ingested {len(ingested)} documents")

        # Step 2: Chunk all documents, collect all chunks
        all_chunks = self._chunk_all(ingested)
        if not all_chunks:
            return 0

        # Filter out empty chunks (no tokenizable text = wasted space)
        pre_filter_count = len(all_chunks)
        all_chunks = [c for c in all_chunks if c.text.strip()]
        if pre_filter_count != len(all_chunks):
            print(f"Filtered out {pre_filter_count - len(all_chunks)} empty chunks")

        print(f"Created {len(all_chunks)} chunks from {len(ingested)} documents")

        # Step 3: Embed all chunks in one batch (blocking Voyage AI call → offload to thread)
        embedded_chunks = await asyncio.to_thread(
            partial(embed_chunks, all_chunks, sparse_encoder=self._sparse_encoder)
        )

        print(f"Embedded {len(embedded_chunks)} chunks")

        # Step 4: Upsert all vectors to Pinecone vector db in one batch (blocking Pinecone call → offload to thread)
        upserted = await asyncio.to_thread(
            partial(self._pinecone.upsert_chunks, embedded_chunks, namespace=self.namespace, batch_size=100)
        )

        print(f"Upserted {upserted} vectors to namespace '{self.namespace}'")

        # Step 5: Move S3 documents from not_embedded to embedded folder (blocking S3 call → offload to thread)
        if self.move_to_embedded_after_success and upserted > 0:
            await asyncio.to_thread(self._move_to_embedded, ingested)

        return upserted

    async def _ingest_all(
        self,
        texts: list[dict],
        s3_uris: list[dict],
        s3_batch_size: int,
    ) -> list[IngestedDoc]:
        """Ingest all inputs. S3 PDFs processed in batches to avoid Modal timeout."""
        ingested: list[IngestedDoc] = []

        # Process texts (instant)
        for item in texts:
            doc = self._ingestor.process_text(
                item["content"],
                source_name="raw_text",
            )
            ingested.append(self._build_ingested_doc(doc, item.get("metadata", {}), s3_uri=None))

        # Process S3 URIs in batches
        total_batches = (len(s3_uris) + s3_batch_size - 1) // s3_batch_size if s3_uris else 0
        for i in range(0, len(s3_uris), s3_batch_size):
            batch = s3_uris[i:i + s3_batch_size]
            batch_num = i // s3_batch_size + 1
            print(f"Processing S3 batch {batch_num}/{total_batches}: {len(batch)} files")

            uri_strings = [item["uri"] for item in batch]
            documents = await self._ingestor.process_batch_s3(uri_strings)

            for item, doc in zip(batch, documents):
                if doc is None:
                    print(f"Warning: Failed to process {item['uri']}, skipping")
                    continue
                ingested.append(self._build_ingested_doc(doc, item.get("metadata", {}), s3_uri=item["uri"]))

        return ingested

    def _build_ingested_doc(
        self,
        doc: Document,
        raw_metadata: dict,
        s3_uri: str | None = None,
    ) -> IngestedDoc:
        """Build IngestedDoc with appropriate metadata extraction."""
        metadata_kind = METADATA_KIND_BY_DOC_TYPE.get(self.doc_type, "default")
        canonical_doc_type = CANONICAL_DOC_TYPES.get(self.doc_type, self.doc_type)

        if metadata_kind == "earnings_call":
            earnings_meta = EarningsCallMetadata.from_transcript(raw_metadata)
            return IngestedDoc(
                document=doc,
                metadata=earnings_meta.to_chunk_metadata(),
                doc_id=earnings_meta.doc_id,
                earnings_meta=earnings_meta,
                s3_uri=s3_uri,
            )

        if metadata_kind == "research":
            research_meta = self._build_structured_metadata(
                ResearchDocumentMetadata,
                raw_metadata,
                s3_uri,
                document_type=canonical_doc_type,
            )
            return IngestedDoc(
                document=doc,
                metadata=research_meta.to_chunk_metadata(),
                doc_id=research_meta.doc_id,
                research_meta=research_meta,
                s3_uri=s3_uri,
            )

        if metadata_kind == "strategy":
            strategy_meta = self._build_structured_metadata(
                TradingStrategyMetadata,
                raw_metadata,
                s3_uri,
                document_type=canonical_doc_type,
            )
            return IngestedDoc(
                document=doc,
                metadata=strategy_meta.to_chunk_metadata(),
                doc_id=strategy_meta.doc_id,
                strategy_meta=strategy_meta,
                s3_uri=s3_uri,
            )

        if metadata_kind == "user_upload" and s3_uri:
            user_id = raw_metadata.get("user_id")
            if not user_id:
                raise ValueError("user_id required in metadata for user_upload doc_type")
            upload_meta = UserUploadMetadata.from_s3_uri(s3_uri, user_id=user_id)
            return IngestedDoc(
                document=doc,
                metadata=upload_meta.to_chunk_metadata(),
                doc_id=upload_meta.doc_id,
                user_upload_meta=upload_meta,
                s3_uri=s3_uri,
            )

        # Default fallback - use DefaultMetadata to extract file_name from S3 URI
        if s3_uri:
            default_meta = DefaultMetadata.from_s3_uri(s3_uri, doc_type=self.doc_type)
        else:
            # For raw text, use a generic source name
            source_name = raw_metadata.get("source_name", "raw_text")
            default_meta = DefaultMetadata.from_text(source_name, doc_type=self.doc_type)

        return IngestedDoc(
            document=doc,
            metadata=default_meta.to_chunk_metadata(),
            doc_id=default_meta.doc_id,
            default_meta=default_meta,
            s3_uri=s3_uri,
        )

    def _build_structured_metadata(
        self,
        model_cls,
        raw_metadata: dict,
        s3_uri: str | None,
        document_type: str,
    ):
        """Build a structured metadata model with optional user overrides."""
        if s3_uri:
            meta = model_cls.from_s3_uri(s3_uri, document_type=document_type)
        else:
            meta = model_cls(
                file_name=raw_metadata.get("file_name") or raw_metadata.get("source_name", "raw_text"),
                file_extension=raw_metadata.get("file_extension", "txt"),
                document_type=document_type,
            )

        overrides = {
            key: value
            for key, value in raw_metadata.items()
            if value is not None and key in model_cls.model_fields
        }
        if "document_type" not in overrides:
            overrides["document_type"] = document_type

        if overrides:
            meta = meta.model_copy(update=overrides)

        return meta

    def _chunk_all(self, ingested: list[IngestedDoc]) -> list[Chunk]:
        """Chunk all documents and collect all chunks."""
        all_chunks: list[Chunk] = []
        total = len(ingested)

        for idx, doc_item in enumerate(ingested, start=1):
            if idx == 1 or idx % 25 == 0 or idx == total:
                print(f"Chunking document {idx}/{total}...")

            chunk_metadata = {**doc_item.metadata, "doc_id": doc_item.doc_id}

            chunks = self._chunker.chunk(
                doc_item.document.content,
                doc_type=self.doc_type,
                metadata=chunk_metadata,
            )

            # Add chunk_id using structured metadata if available
            for chunk in chunks:
                chunk_index = chunk.metadata.get("chunk_index", 0)
                if doc_item.earnings_meta:
                    chunk.metadata["chunk_id"] = doc_item.earnings_meta.build_chunk_id(chunk_index)
                elif doc_item.research_meta:
                    chunk.metadata["chunk_id"] = doc_item.research_meta.build_chunk_id(chunk_index)
                elif doc_item.strategy_meta:
                    chunk.metadata["chunk_id"] = doc_item.strategy_meta.build_chunk_id(chunk_index)
                elif doc_item.user_upload_meta:
                    chunk.metadata["chunk_id"] = doc_item.user_upload_meta.build_chunk_id(chunk_index)
                elif doc_item.default_meta:
                    chunk.metadata["chunk_id"] = doc_item.default_meta.build_chunk_id(chunk_index)
                else:
                    chunk.metadata["chunk_id"] = f"{doc_item.doc_id}#{chunk_index:04d}"

            all_chunks.extend(chunks)

        return all_chunks

    def _move_to_embedded(self, ingested: list[IngestedDoc]) -> None:
        """Move S3 documents from not_embedded to embedded folder after successful processing."""
        s3_docs = [doc for doc in ingested if doc.s3_uri]
        if not s3_docs:
            return

        print(f"Moving {len(s3_docs)} S3 documents to embedded folder...")

        moved_count = 0
        for doc in s3_docs:
            if self._ingestor.move_s3_to_embedded(doc.s3_uri):
                moved_count += 1

        print(f"Moved {moved_count}/{len(s3_docs)} S3 documents to embedded folder")

    def _generate_doc_id(self, metadata: dict) -> str:
        """Generate a unique document ID."""
        # Use ticker + fiscal info if available, otherwise UUID
        ticker = metadata.get("ticker")
        fiscal_year = metadata.get("fiscal_year")
        fiscal_quarter = metadata.get("fiscal_quarter")

        if ticker and fiscal_year:
            quarter = f"Q{fiscal_quarter}" if fiscal_quarter else ""
            return f"{ticker}_{fiscal_year}{quarter}_{uuid.uuid4().hex[:8]}"

        return uuid.uuid4().hex


def build_s3_uri_batch(bucket: str, prefix: str, limit: int | None = None) -> list[dict]:
    """Collect S3 URIs under a prefix for pipeline ingestion."""
    import boto3

    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    s3_uris: list[dict] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key == prefix or key.endswith("/"):
                continue
            s3_uris.append({"uri": f"s3://{bucket}/{key}", "metadata": {}})

    s3_uris.sort(key=lambda item: item["uri"])
    if limit is not None:
        return s3_uris[:limit]
    return s3_uris


async def run_trading_strategies_pipeline(limit: int | None = None) -> int:
    """
    Ingest PDFs from the trading strategies S3 folder.

    Intended to be called from a CLI or module entrypoint rather than by
    executing this source file directly.
    """
    bucket = "prophitai-s3-bucket"
    prefix = "pdfs/trading_strategies/not_embedded/"
    s3_uris = build_s3_uri_batch(bucket, prefix, limit=limit)

    if not s3_uris:
        print("No trading strategy files found to ingest.")
        return 0

    print(len(s3_uris))
    print(s3_uris)

    pipeline = Pipeline(
        namespace="trading_strategies",
        doc_type="strategy_research",
        chunker_type="semantic",
        move_to_embedded_after_success=True,
    )

    count = await pipeline.run(s3_uris=s3_uris, s3_batch_size=5)
    print(f"Upserted {count} vectors to namespace 'trading_strategies'")
    return count


async def run_macro_research_pipeline(limit: int | None = None) -> int:
    """
    Ingest PDFs from the macro research S3 folder.

    Intended to be called from a CLI or module entrypoint rather than by
    executing this source file directly.
    """
    bucket = "prophitai-s3-bucket"
    prefix = "pdfs/macro_research/not_embedded/"
    s3_uris = build_s3_uri_batch(bucket, prefix, limit=limit)

    if not s3_uris:
        print("No macro research files found to ingest.")
        return 0

    print(len(s3_uris))
    print(s3_uris)

    pipeline = Pipeline(
        namespace="macro_research",
        doc_type="macro_research",
        chunker_type="semantic",
        move_to_embedded_after_success=True,
    )

    count = await pipeline.run(s3_uris=s3_uris, s3_batch_size=5)
    print(f"Upserted {count} vectors to namespace 'macro_research'")
    return count


if __name__ == "__main__":
    # Set to 1 for a single-file test run.
    # Set to None to ingest the full macro_research folder.
    TEST_LIMIT = 100
    asyncio.run(run_macro_research_pipeline(limit=TEST_LIMIT))
