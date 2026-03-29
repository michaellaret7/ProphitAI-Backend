"""
Metadata models for RAG document processing.

Provides structured metadata builders for different document types,
automatically deriving fields from source data.
"""

from pydantic import BaseModel, Field, computed_field


class EarningsCallMetadata(BaseModel):
    """
    Metadata builder for earnings call transcripts.

    Automatically derives doc_id, fiscal_quarter, and provides
    chunk_id generation from minimal input.

    Usage:
        from app.repositories.transcripts_data import get_latest_transcript

        transcript = get_latest_transcript("AAPL")
        meta = EarningsCallMetadata.from_transcript(transcript)

        chunks = chunker.chunk(
            transcript["content"],
            doc_type="earnings_call",
            metadata=meta.to_chunk_metadata(),
        )

        # After chunking, build chunk_ids
        for chunk in chunks:
            chunk.metadata["chunk_id"] = meta.build_chunk_id(chunk.metadata["chunk_index"])
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    period: int = Field(..., description="Fiscal quarter (1-4)")
    year: int = Field(..., description="Fiscal year")
    call_date: str = Field(..., description="Date of earnings call (YYYY-MM-DD)")

    @computed_field
    @property
    def fiscal_quarter(self) -> str:
        """Fiscal quarter in format YYYYQN (e.g., 2025Q3)."""
        return f"{self.year}Q{self.period}"

    @computed_field
    @property
    def doc_id(self) -> str:
        """Unique document identifier for the earnings call."""
        return f"earnings_call:{self.ticker}:{self.fiscal_quarter}"

    @classmethod
    def from_transcript(cls, transcript: dict) -> "EarningsCallMetadata":
        """
        Create metadata from a transcript dict returned by get_latest_transcript.

        Args:
            transcript: Dict with keys: ticker, period, year, date, content.

        Returns:
            EarningsCallMetadata instance with all fields populated.

        Raises:
            ValueError: If transcript is not found or missing required fields.
        """
        if not transcript.get("found", True):
            raise ValueError(f"Transcript not found for ticker: {transcript.get('ticker')}")

        # Parse period: database stores as 'Q1', 'Q2', etc. but we need int (1-4)
        raw_period = transcript["period"]
        if isinstance(raw_period, str) and raw_period.upper().startswith("Q"):
            period = int(raw_period[1:])
        else:
            period = int(raw_period)

        return cls(
            ticker=transcript["ticker"],
            period=period,
            year=transcript["year"],
            call_date=transcript["date"],
        )

    def to_chunk_metadata(self) -> dict:
        """
        Convert to metadata dict for chunker.

        Returns:
            Dict with all fields needed for chunk metadata.
        """
        return {
            "ticker": self.ticker,
            "doc_id": self.doc_id,
            "call_date": self.call_date,
            "fiscal_year": self.year,
            "fiscal_quarter": self.fiscal_quarter,
        }

    def build_chunk_id(self, chunk_index: int) -> str:
        """
        Build a unique chunk ID from the doc_id and chunk index.

        Args:
            chunk_index: 0-based index of the chunk.

        Returns:
            Chunk ID in format doc_id#NNNN (e.g., earnings_call:AAPL:2025Q3#0042).
        """
        return f"{self.doc_id}#{chunk_index:04d}"
