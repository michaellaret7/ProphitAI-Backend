"""
Metadata models for research document processing.

Uses LLM-based extraction to derive structured metadata from S3 URIs
and document filenames where information must be inferred.
"""

import json
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from prophitai_foundry.models.metadata.utils import (
    infer_source_id,
    parse_s3_uri,
    sanitize_for_vector_id,
    split_file_name,
)
from prophitai_shared import get_backend


class ResearchDocumentMetadata(BaseModel):
    """
    Metadata builder for research documents (PDFs, reports, etc.).

    Automatically derives doc_id and provides chunk_id generation.
    Can extract metadata from S3 URIs using LLM-based parsing.

    Usage:
        # From S3 URI (LLM-extracted)
        meta = ResearchDocumentMetadata.from_s3_uri(
            "s3://prophitai-s3-bucket/pdfs/macro_research/JPM_Weekly_Jan2026.pdf"
        )

        # From manual input
        meta = ResearchDocumentMetadata(
            file_name="JPM_Weekly_Jan2026",
            file_extension="pdf",
            document_type="macro_research",  # or "ticker_research", "equity_research"
            research_provider="JPMorgan",
            research_date="2026-01",
        )

        chunks = chunker.chunk(content, metadata=meta.to_chunk_metadata())

        for chunk in chunks:
            chunk.metadata["chunk_id"] = meta.build_chunk_id(chunk.metadata["chunk_index"])
    """

    file_name: str = Field(..., description="File name without extension")
    file_extension: str = Field(..., description="File extension (pdf, csv, etc.)")
    document_type: str = Field(..., description="Type of document (macro_research, ticker_research, equity_research)")
    source_id: Optional[str] = Field(None, description="Stable external source identifier when available")
    research_provider: Optional[str] = Field(None, description="Research provider (JPMorgan, Goldman, etc.)")
    research_date: Optional[str] = Field(None, description="Research date or period (YYYY-MM or descriptive)")
    ticker: Optional[str] = Field(None, description="Stock ticker if this is ticker-specific research")
    s3_bucket: Optional[str] = Field(None, description="S3 bucket name if from S3")
    s3_key: Optional[str] = Field(None, description="Full S3 object key if from S3")

    @computed_field
    @property
    def doc_id(self) -> str:
        """Unique document identifier for the research document."""
        provider_part = sanitize_for_vector_id(self.research_provider.lower()) if self.research_provider else "unknown"
        date_part = self.research_date.replace("-", "") if self.research_date else "undated"
        source_part = sanitize_for_vector_id((self.source_id or self.file_name).lower())

        if self.ticker:
            return f"{self.document_type}:{self.ticker}:{provider_part}:{date_part}:{source_part}"
        return f"{self.document_type}:{provider_part}:{source_part}:{date_part}"

    @classmethod
    def from_s3_uri(
        cls,
        s3_uri: str,
        document_type: Optional[str] = None,
        provider: str = "groq",
        model: str = "llama-3.1-8b-instant",
    ) -> "ResearchDocumentMetadata":
        """
        Extract metadata from an S3 URI using LLM-based parsing.

        Args:
            s3_uri: Full S3 URI (s3://bucket/key/to/file.pdf).
            provider: LLM provider to use for extraction.
            model: Model name to use for extraction.

        Returns:
            ResearchDocumentMetadata with fields populated from LLM extraction.
        """
        s3_bucket, s3_key = parse_s3_uri(s3_uri)
        file_name, file_extension = split_file_name(s3_key)

        backend = get_backend(provider=provider, model=model)
        response_json = backend.create_json_object(
            messages=[
                {
                    "role": "user",
                    "content": f"""Parse the following S3 URI into structured metadata.

URI: {s3_uri}

Return a JSON object with these fields:
- source_id: stable source identifier if obvious from the path or filename (e.g., arxiv:2312.15730, ssrn:5278107), null if unknown
- research_provider: infer the research provider from the path/filename if possible (e.g., JPMorgan, Goldman Sachs, Morgan Stanley), null if unknown
- research_date: infer date from the path/filename if possible (format as YYYY-MM if possible), null if unknown
- document_type: infer the type from the path (e.g., macro_research, ticker_research, equity_research). Use "ticker_research" or "equity_research" if a specific stock ticker is mentioned
- ticker: if the document is about a specific stock, extract the ticker symbol (e.g., AAPL, MSFT), null if it's general/macro research

Return ONLY valid JSON, no other text.""",
                }
            ],
        )

        parsed = json.loads(response_json)
        resolved_document_type = document_type or parsed.get("document_type") or "research"
        # Macro research should never have a ticker
        ticker = None if resolved_document_type == "macro_research" else parsed.get("ticker")
        return cls(
            file_name=file_name,
            file_extension=file_extension,
            document_type=resolved_document_type,
            source_id=parsed.get("source_id") or infer_source_id(file_name),
            research_provider=parsed.get("research_provider"),
            research_date=parsed.get("research_date"),
            ticker=ticker,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )

    @classmethod
    def from_s3_uris_batch(
        cls,
        s3_uris: list[str],
        document_type: Optional[str] = None,
        provider: str = "groq",
        model: str = "llama-3.1-8b-instant",
    ) -> list["ResearchDocumentMetadata"]:
        """
        Extract metadata from multiple S3 URIs in a single LLM call.

        More efficient than calling from_s3_uri multiple times.

        Args:
            s3_uris: List of S3 URIs to parse.
            provider: LLM provider to use.
            model: Model name to use.

        Returns:
            List of ResearchDocumentMetadata instances.
        """
        backend = get_backend(provider=provider, model=model)

        uris_formatted = "\n".join(f"{i+1}. {uri}" for i, uri in enumerate(s3_uris))

        response_json = backend.create_json_object(
            messages=[
                {
                    "role": "user",
                    "content": f"""Parse each of the following S3 URIs into structured metadata.

URIs:
{uris_formatted}

Return a JSON object with a "documents" array where each element has:
- source_id: stable source identifier if obvious from the path or filename (e.g., arxiv:2312.15730, ssrn:5278107), null if unknown
- research_provider: infer the research provider if possible, null if unknown
- research_date: infer date if possible (format as YYYY-MM), null if unknown
- document_type: infer the type from the path (e.g., macro_research, ticker_research, equity_research). Use "ticker_research" or "equity_research" if a specific stock ticker is mentioned
- ticker: if the document is about a specific stock, extract the ticker symbol (e.g., AAPL, MSFT), null if it's general/macro research

Return ONLY valid JSON, no other text.""",
                }
            ],
        )

        parsed = json.loads(response_json)
        documents = parsed.get("documents", [])

        results = []
        for s3_uri, doc in zip(s3_uris, documents):
            s3_bucket, s3_key = parse_s3_uri(s3_uri)
            file_name, file_extension = split_file_name(s3_key)

            resolved_document_type = document_type or doc.get("document_type") or "research"
            # Macro research should never have a ticker
            ticker = None if resolved_document_type == "macro_research" else doc.get("ticker")
            results.append(
                cls(
                    file_name=file_name,
                    file_extension=file_extension,
                    document_type=resolved_document_type,
                    source_id=doc.get("source_id") or infer_source_id(file_name),
                    research_provider=doc.get("research_provider"),
                    research_date=doc.get("research_date"),
                    ticker=ticker,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                )
            )
        return results

    def to_chunk_metadata(self) -> dict:
        """
        Convert to metadata dict for chunker.

        Returns:
            Dict with all fields needed for chunk metadata.
        """
        meta = {
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "document_type": self.document_type,
            "research_provider": self.research_provider,
            "research_date": self.research_date,
        }
        if self.source_id:
            meta["source_id"] = self.source_id
        if self.ticker:
            meta["ticker"] = self.ticker
        return meta

    def build_chunk_id(self, chunk_index: int) -> str:
        """
        Build a unique chunk ID from the doc_id and chunk index.

        Args:
            chunk_index: 0-based index of the chunk.

        Returns:
            Chunk ID in format doc_id#NNNN.
        """
        return f"{self.doc_id}#{chunk_index:04d}"
