"""
Metadata model for trading strategy research documents.

Provides a flat, filterable schema for strategy papers and notes so retrieval
can segment by strategy family, asset class, market, and source.
"""

from typing import Optional

from pydantic import BaseModel, Field, computed_field

from prophitai_foundry.models.metadata.utils import (
    infer_source_id,
    parse_s3_uri,
    sanitize_for_vector_id,
    split_file_name,
)


def _infer_label(text: str, keyword_map: list[tuple[list[str], str]]) -> str | None:
    """Return the first matching label for the provided text."""
    lowered = text.lower()
    for keywords, label in keyword_map:
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


class TradingStrategyMetadata(BaseModel):
    """
    Metadata for trading strategy research documents.

    This schema is intentionally flat so it can be stored directly in Pinecone
    metadata and used for filtering during retrieval.
    """

    file_name: str = Field(..., description="File name without extension")
    file_extension: str = Field(..., description="File extension (pdf, txt, etc.)")
    document_type: str = Field(default="strategy_research", description="Canonical document type")
    source_id: Optional[str] = Field(None, description="Stable source identifier such as arxiv:2312.15730")
    title: Optional[str] = Field(None, description="Human-readable title for the document")
    research_provider: Optional[str] = Field(None, description="Publisher, bank, author group, or source")
    publication_date: Optional[str] = Field(None, description="Publication date (prefer YYYY-MM-DD)")
    strategy_family: Optional[str] = Field(None, description="High-level strategy family")
    asset_class: Optional[str] = Field(None, description="Primary asset class covered by the research")
    market: Optional[str] = Field(None, description="Primary market or region covered")
    frequency: Optional[str] = Field(None, description="Execution or rebalance frequency")
    universe: Optional[str] = Field(None, description="Target instrument universe")
    tickers: Optional[list[str]] = Field(None, description="Relevant tickers or instruments")
    tags: Optional[list[str]] = Field(None, description="Additional filterable tags")
    version: Optional[str] = Field(None, description="Optional document version")
    s3_bucket: Optional[str] = Field(None, description="S3 bucket name")
    s3_key: Optional[str] = Field(None, description="Full S3 object key")

    @computed_field
    @property
    def doc_id(self) -> str:
        """Stable document identifier used as the chunk ID prefix."""
        strategy_part = (
            sanitize_for_vector_id(self.strategy_family.lower())
            if self.strategy_family
            else "general"
        )
        source_part = sanitize_for_vector_id((self.source_id or self.file_name).lower())
        date_part = self.publication_date.replace("-", "") if self.publication_date else "undated"
        return f"{self.document_type}:{strategy_part}:{source_part}:{date_part}"

    @classmethod
    def from_s3_uri(
        cls,
        s3_uri: str,
        document_type: str = "strategy_research",
    ) -> "TradingStrategyMetadata":
        """
        Build strategy metadata from an S3 URI using lightweight heuristics.

        Explicit metadata passed later through the pipeline should override these
        inferred defaults.
        """
        s3_bucket, s3_key = parse_s3_uri(s3_uri)
        file_name, file_extension = split_file_name(s3_key)
        search_text = f"{s3_key} {file_name}"

        return cls(
            file_name=file_name,
            file_extension=file_extension,
            document_type=document_type,
            source_id=infer_source_id(file_name),
            title=file_name.replace("_", " "),
            strategy_family=cls._infer_strategy_family(search_text),
            asset_class=cls._infer_asset_class(search_text),
            market=cls._infer_market(search_text),
            frequency=cls._infer_frequency(search_text),
            universe=cls._infer_universe(search_text),
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )

    @staticmethod
    def _infer_strategy_family(text: str) -> str | None:
        return _infer_label(
            text,
            [
                (["stat arb", "stat_arb", "statarb", "pairs trading", "pairs_trading"], "stat_arb"),
                (["mean reversion", "mean_reverting", "mean_revert"], "mean_reversion"),
                (["momentum"], "momentum"),
                (["market making", "market_making"], "market_making"),
                (["grid trading", "grid_trading"], "grid_trading"),
                (["option", "hedging", "deltahedge", "deep hedging"], "options"),
                (
                    [
                        "reinforcement learning",
                        "deep rl",
                        "deep_rl",
                        "q learning",
                        "q_learning",
                        "finrl",
                        "_rl_",
                    ],
                    "reinforcement_learning",
                ),
                (["sentiment", "llm"], "sentiment"),
                (["factor", "risk parity", "kelly", "portfolio optimization"], "portfolio_construction"),
            ],
        )

    @staticmethod
    def _infer_asset_class(text: str) -> str | None:
        return _infer_label(
            text,
            [
                (["crypto", "bitcoin", "cryptocurrency", "btc", "eth"], "crypto"),
                (["option", "options"], "options"),
                (["future", "futures"], "futures"),
                (["fx", "forex", "currency"], "fx"),
                (["stock", "equity", "equities", "sp500", "s&p"], "equities"),
            ],
        )

    @staticmethod
    def _infer_market(text: str) -> str | None:
        return _infer_label(
            text,
            [
                (["sp500", "s&p", "nasdaq", "nyse", "us "], "us"),
                (["eurozone", "europe", "ecb"], "europe"),
                (["crypto", "bitcoin", "ethereum"], "crypto"),
            ],
        )

    @staticmethod
    def _infer_frequency(text: str) -> str | None:
        return _infer_label(
            text,
            [
                (["high frequency", "high_frequency", "hft", "intraday", "realtime", "real time", "lob"], "intraday"),
                (["daily", "multi day", "multi_day", "multi-day"], "daily"),
                (["weekly"], "weekly"),
            ],
        )

    @staticmethod
    def _infer_universe(text: str) -> str | None:
        return _infer_label(
            text,
            [
                (["sp500", "s&p 500", "s&p500"], "SP500"),
                (["bitcoin", "btc"], "BTC"),
            ],
        )

    def to_chunk_metadata(self) -> dict:
        """Convert to a flat metadata dict suitable for chunk storage."""
        metadata = {
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "document_type": self.document_type,
            "source_id": self.source_id,
            "title": self.title,
            "research_provider": self.research_provider,
            "publication_date": self.publication_date,
            "strategy_family": self.strategy_family,
            "asset_class": self.asset_class,
            "market": self.market,
            "frequency": self.frequency,
            "universe": self.universe,
            "tickers": self.tickers,
            "tags": self.tags,
            "version": self.version,
            "s3_bucket": self.s3_bucket,
            "s3_key": self.s3_key,
        }
        return {key: value for key, value in metadata.items() if value is not None}

    def build_chunk_id(self, chunk_index: int) -> str:
        """Build a unique chunk ID from the doc ID and chunk index."""
        return f"{self.doc_id}#{chunk_index:04d}"
