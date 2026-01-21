"""
Efficient batch ingestion pipeline for RAG.

Processes multiple texts and S3 documents in a single pass:
1. Ingest all (parallel S3 fetches)
2. Chunk all → collect all chunks
3. Embed all chunks in one batch call
4. Upsert all vectors in one batch call
"""

from __future__ import annotations

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from dotenv import load_dotenv

from app.core.foundry.chunking.earnings_calls import EarningsCallChunker
from app.core.foundry.chunking.recursive import RecursiveChunker
from app.core.foundry.chunking.semantic import SemanticChunker
from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.sparse_encoder import SparseEncoder
from app.core.foundry.embeddings.voyage_embeddings import embed_chunks
from app.core.foundry.ingestion import Ingestor
from app.core.foundry.models.chunk import Chunk
from app.core.foundry.models.document import Document
from app.core.foundry.models.metadata import EarningsCallMetadata

load_dotenv()

@dataclass
class IngestedDoc:
    """Document with its associated metadata."""
    document: Document
    metadata: dict
    doc_id: str
    earnings_meta: EarningsCallMetadata | None = None


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
        s3_workers: int = 5,
        chunker_type: str = "earnings_call",
    ):
        """
        Initialize the pipeline.

        Args:
            namespace: Pinecone namespace for vectors.
            doc_type: Document type for chunker selection.
            s3_workers: Max parallel workers for S3 fetches.
        """
        self.namespace = namespace
        self.doc_type = doc_type
        self.s3_workers = s3_workers

        # Initialize components
        self._ingestor = Ingestor() # --> import deoc/text ingestion Object 

        self._sparse_encoder = SparseEncoder() # --> import sparse encoder Object
        self._sparse_encoder.load() # --> load the sparse encoder from the file system

        self._pinecone = PineconeManager() # --> import pinecone manager Object
        self._pinecone.connect_index( # --> connect to the pinecone index
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )

        self._chunker = CHUNKERS[chunker_type]() # --> get the chunker method for the document type

    def run(
        self,
        texts: list[dict] | None = None,
        s3_uris: list[dict] | None = None,
    ) -> int:
        """
        Process multiple texts and/or S3 documents.

        Args:
            texts: List of {"content": str, "metadata": dict}.
            s3_uris: List of {"uri": str, "metadata": dict}.

        Returns:
            Total number of vectors upserted.
        """
        texts = texts or []
        s3_uris = s3_uris or []

        if not texts and not s3_uris:
            return 0

        # Step 1: Ingest all documents using the ingestor Object layer 
        ingested = self._ingest_all(texts, s3_uris)
        if not ingested:
            return 0

        print(f"Ingested {len(ingested)} documents")

        # Step 2: Chunk all documents, collect all chunks 
        all_chunks = self._chunk_all(ingested)
        if not all_chunks:
            return 0

        print(f"Created {len(all_chunks)} chunks from {len(ingested)} documents")

        # Step 3: Embed all chunks in one batch. Here we are embedding dense and sparse vectors 
        embedded_chunks = embed_chunks(
            all_chunks,
            sparse_encoder=self._sparse_encoder,
        )

        print(f"Embedded {len(embedded_chunks)} chunks")

        # Step 4: Upsert all vectors to Pinecone vector db in one batch
        upserted = self._pinecone.upsert_chunks(
            embedded_chunks,
            namespace=self.namespace,
            batch_size=100,
        )

        print(f"Upserted {upserted} vectors to namespace '{self.namespace}'")

        return upserted

    def _ingest_all(
        self,
        texts: list[dict],
        s3_uris: list[dict],
    ) -> list[IngestedDoc]:
        """Ingest all inputs. S3 fetches run in parallel."""
        ingested: list[IngestedDoc] = []

        # Process texts (instant)
        for item in texts:
            doc = self._ingestor.process_text(
                item["content"],
                source_name="raw_text",
            )
            ingested.append(self._build_ingested_doc(doc, item.get("metadata", {})))

        # Process S3 URIs in parallel
        if s3_uris:
            with ThreadPoolExecutor(max_workers=self.s3_workers) as executor:
                s3_results = list(executor.map(self._ingest_s3_single, s3_uris))
                ingested.extend(s3_results)

        return ingested

    def _ingest_s3_single(self, item: dict) -> IngestedDoc: # --> this function is the one used in the thread pool executor
        """Ingest a single S3 document."""
        doc = self._ingestor.process(item["uri"])
        return self._build_ingested_doc(doc, item.get("metadata", {}))

    def _build_ingested_doc(self, doc: Document, raw_metadata: dict) -> IngestedDoc:
        """Build IngestedDoc, using EarningsCallMetadata for earnings calls."""
        if self.doc_type == "earnings_call":
            earnings_meta = EarningsCallMetadata.from_transcript(raw_metadata)
            return IngestedDoc(
                document=doc,
                metadata=earnings_meta.to_chunk_metadata(),
                doc_id=earnings_meta.doc_id,
                earnings_meta=earnings_meta,
            )
 
        return IngestedDoc(
            document=doc,
            metadata=raw_metadata,
            doc_id=self._generate_doc_id(raw_metadata),
        )

    def _chunk_all(self, ingested: list[IngestedDoc]) -> list[Chunk]:
        """Chunk all documents and collect all chunks."""
        all_chunks: list[Chunk] = []

        for doc_item in ingested:
            chunk_metadata = {**doc_item.metadata, "doc_id": doc_item.doc_id}

            chunks = self._chunker.chunk(
                doc_item.document.content,
                doc_type=self.doc_type,
                metadata=chunk_metadata,
            )

            # Add chunk_id using EarningsCallMetadata if available
            for chunk in chunks:
                chunk_index = chunk.metadata.get("chunk_index", 0)
                if doc_item.earnings_meta:
                    chunk.metadata["chunk_id"] = doc_item.earnings_meta.build_chunk_id(chunk_index)
                else:
                    chunk.metadata["chunk_id"] = f"{doc_item.doc_id}#{chunk_index:04d}"

            all_chunks.extend(chunks)

        return all_chunks

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


if __name__ == "__main__":
    from app.repositories.transcripts_data import get_earnings_transcripts
    from app.core.foundry.utils.delete_embeddings import DeleteEmbeddings

    # de = DeleteEmbeddings()
    # de.delete_all(namespace="earnings_calls")

    # Get last 6 transcripts for a ticker
    ticker = "V"
    result = get_earnings_transcripts(ticker, limit=12)

    # Build input list - add ticker to each item since get_earnings_transcripts doesn't include it
    texts = [
        {"content": item["content"], "metadata": {**item, "ticker": ticker}}
        for item in result["items"]
    ]

    print(f"Processing {len(texts)} transcripts for {ticker}")

    pipe = Pipeline(namespace="earnings_calls", doc_type="earnings_call", chunker_type="earnings_call")
    count = pipe.run(texts=texts)
    print(f"Upserted {count} vectors")
