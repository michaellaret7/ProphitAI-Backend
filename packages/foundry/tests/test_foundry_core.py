"""
Tests for foundry package core components.

Tests metadata models, recursive chunking, retrieval filter building,
and live VectorSearch against the real Pinecone index.
"""

import pytest

from prophitai_foundry.models.chunk import Chunk
from prophitai_foundry.models.document import Document
from prophitai_foundry.models.metadata.earnings import EarningsCallMetadata
from prophitai_foundry.models.metadata.research import ResearchDocumentMetadata
from prophitai_foundry.models.metadata.strategy import TradingStrategyMetadata
from prophitai_foundry.models.metadata.user_upload import UserUploadMetadata
from prophitai_foundry.models.vector import QueryResult
from prophitai_foundry.chunking.recursive import RecursiveChunker
from prophitai_foundry.pipeline import Pipeline
from prophitai_foundry.retrieval.utils import build_metadata_filter
from prophitai_foundry.retrieval.search.vector import VectorSearch


# ================================
# --> Test 1: EarningsCallMetadata
# ================================

class TestEarningsCallMetadata:
    """Verify metadata construction, computed fields, and chunk ID generation."""

    def test_computed_fields(self):
        """fiscal_quarter and doc_id should derive from ticker/period/year."""
        meta = EarningsCallMetadata(
            ticker="AAPL",
            period=3,
            year=2025,
            call_date="2025-10-30",
        )

        assert meta.fiscal_quarter == "2025Q3"
        assert meta.doc_id == "earnings_call:AAPL:2025Q3"

    def test_to_chunk_metadata(self):
        """to_chunk_metadata should return a flat dict with all required keys."""
        meta = EarningsCallMetadata(
            ticker="MSFT",
            period=1,
            year=2026,
            call_date="2026-01-28",
        )
        chunk_meta = meta.to_chunk_metadata()

        assert chunk_meta == {
            "ticker": "MSFT",
            "doc_id": "earnings_call:MSFT:2026Q1",
            "call_date": "2026-01-28",
            "fiscal_year": 2026,
            "fiscal_quarter": "2026Q1",
        }

    def test_build_chunk_id(self):
        """Chunk IDs should be zero-padded to 4 digits."""
        meta = EarningsCallMetadata(
            ticker="GOOG",
            period=4,
            year=2025,
            call_date="2025-12-15",
        )

        assert meta.build_chunk_id(0) == "earnings_call:GOOG:2025Q4#0000"
        assert meta.build_chunk_id(42) == "earnings_call:GOOG:2025Q4#0042"
        assert meta.build_chunk_id(9999) == "earnings_call:GOOG:2025Q4#9999"

    def test_from_transcript(self):
        """from_transcript should parse period string like 'Q2' into int."""
        transcript = {
            "ticker": "NVDA",
            "period": "Q2",
            "year": 2025,
            "date": "2025-08-20",
            "content": "...",
        }
        meta = EarningsCallMetadata.from_transcript(transcript)

        assert meta.period == 2
        assert meta.fiscal_quarter == "2025Q2"
        assert meta.doc_id == "earnings_call:NVDA:2025Q2"

    def test_from_transcript_not_found_raises(self):
        """Should raise ValueError when transcript not found."""
        with pytest.raises(ValueError, match="Transcript not found"):
            EarningsCallMetadata.from_transcript({"found": False, "ticker": "XYZ"})


# ================================
# --> Test 2: UserUploadMetadata
# ================================

class TestUserUploadMetadata:
    """Verify user-upload metadata produces stable document IDs."""

    def test_doc_id_stable_across_accesses(self):
        """doc_id should be generated once, not on every property access."""
        meta = UserUploadMetadata(
            user_id="clerk_123",
            file_name="report",
            file_extension="pdf",
        )

        first = meta.doc_id
        second = meta.doc_id

        assert first == second
        assert meta.to_chunk_metadata()["doc_id"] == first
        assert meta.build_chunk_id(2) == f"{first}#0002"


# ================================
# --> Test 3: ResearchDocumentMetadata
# ================================

class TestResearchDocumentMetadata:
    """Verify research metadata IDs remain stable and collision-resistant."""

    def test_ticker_research_doc_id_uses_source_identifier(self):
        """Two same-month ticker notes should not collide when source differs."""
        base = {
            "file_extension": "pdf",
            "document_type": "equity_research",
            "research_provider": "Goldman Sachs",
            "research_date": "2026-01",
            "ticker": "AAPL",
        }

        meta_one = ResearchDocumentMetadata(
            file_name="AAPL_note_v1",
            source_id="gs:aapl-note-v1",
            **base,
        )
        meta_two = ResearchDocumentMetadata(
            file_name="AAPL_note_v2",
            source_id="gs:aapl-note-v2",
            **base,
        )

        assert meta_one.doc_id != meta_two.doc_id

    def test_source_id_included_in_chunk_metadata(self):
        """source_id should remain available for downstream filtering and traceability."""
        meta = ResearchDocumentMetadata(
            file_name="JPM_Weekly_Jan2026",
            file_extension="pdf",
            document_type="macro_research",
            source_id="jpm:weekly:2026-01",
            research_provider="JPMorgan",
            research_date="2026-01",
        )

        chunk_meta = meta.to_chunk_metadata()

        assert chunk_meta["source_id"] == "jpm:weekly:2026-01"
        assert chunk_meta["document_type"] == "macro_research"


# ================================
# --> Test 4: TradingStrategyMetadata
# ================================

class TestTradingStrategyMetadata:
    """Verify strategy metadata supports flat filtering and stable IDs."""

    def test_from_s3_uri_infers_source_and_strategy_fields(self):
        """Known filename patterns should populate useful default metadata."""
        meta = TradingStrategyMetadata.from_s3_uri(
            "s3://bucket/pdfs/trading_strategies/not_embedded/"
            "arxiv_2312.15730_Deep_RL_for_Quantitative_Trading.pdf"
        )

        assert meta.document_type == "strategy_research"
        assert meta.source_id == "arxiv:2312.15730"
        assert meta.strategy_family == "reinforcement_learning"
        assert meta.doc_id.startswith("strategy_research:reinforcement_learning:arxiv:2312.15730")

    def test_to_chunk_metadata_preserves_flat_filterable_fields(self):
        """Chunk metadata should keep list and scalar fields flat for Pinecone."""
        meta = TradingStrategyMetadata(
            file_name="stat_arb_playbook",
            file_extension="pdf",
            source_id="internal:stat-arb-playbook",
            research_provider="Internal",
            publication_date="2026-02-14",
            strategy_family="stat_arb",
            asset_class="equities",
            market="us",
            frequency="daily",
            universe="SP500",
            tickers=["AAPL", "MSFT"],
            tags=["pairs", "mean_reversion"],
            version="v2",
        )

        chunk_meta = meta.to_chunk_metadata()

        assert chunk_meta["strategy_family"] == "stat_arb"
        assert chunk_meta["tickers"] == ["AAPL", "MSFT"]
        assert chunk_meta["tags"] == ["pairs", "mean_reversion"]
        assert chunk_meta["publication_date"] == "2026-02-14"

    def test_pipeline_strategy_builder_applies_overrides(self):
        """Pipeline strategy metadata should use inferred defaults plus explicit overrides."""
        pipeline = Pipeline.__new__(Pipeline)
        pipeline.doc_type = "strategy_research"

        ingested = Pipeline._build_ingested_doc(
            pipeline,
            Document(content="alpha", metadata={}, source="s3://bucket/doc.pdf"),
            {
                "publication_date": "2026-03-01",
                "strategy_family": "momentum",
                "research_provider": "Internal Research",
                "tags": ["equities", "trend"],
            },
            s3_uri=(
                "s3://bucket/pdfs/trading_strategies/not_embedded/"
                "arxiv_2312.15730_Deep_RL_for_Quantitative_Trading.pdf"
            ),
        )

        assert ingested.strategy_meta is not None
        assert ingested.strategy_meta.strategy_family == "momentum"
        assert ingested.strategy_meta.research_provider == "Internal Research"
        assert ingested.strategy_meta.publication_date == "2026-03-01"
        assert ingested.metadata["tags"] == ["equities", "trend"]


# ================================
# --> Test 5: RecursiveChunker
# ================================

class TestRecursiveChunker:
    """Verify recursive chunking produces valid Chunk objects within size limits."""

    def test_basic_chunking(self):
        """Chunking a multi-paragraph text should produce multiple Chunk objects."""
        chunker = RecursiveChunker(
            tokenizer="gpt2",
            chunk_size=50,
            chunk_overlap=0,
        )

        text = (
            "Apple reported record revenue of $124 billion for Q1 2025. "
            "This represents a 4% year-over-year increase driven by strong "
            "iPhone and Services performance.\n\n"
            "Operating expenses came in at $15.4 billion, slightly above "
            "analyst estimates. Management attributed the increase to "
            "investments in AI research and development.\n\n"
            "The company returned $25 billion to shareholders through "
            "dividends and share buybacks during the quarter. Tim Cook "
            "highlighted the growing installed base of over 2.2 billion "
            "active devices worldwide."
        )

        chunks = chunker.chunk(text, metadata={"ticker": "AAPL"})

        assert len(chunks) >= 2, "Expected multiple chunks for this text"

        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.token_count > 0
            assert chunk.token_count <= 50
            assert len(chunk.text) > 0
            assert chunk.start_index >= 0
            assert chunk.end_index > chunk.start_index

    def test_metadata_propagation(self):
        """Custom metadata should appear in every chunk."""
        custom_meta = {"ticker": "TSLA", "doc_id": "test_doc"}
        chunker = RecursiveChunker(
            tokenizer="gpt2",
            chunk_size=30,
            metadata=custom_meta,
        )

        text = "Tesla delivered 500,000 vehicles in Q4. Revenue hit $25 billion."
        chunks = chunker.chunk(text)

        for chunk in chunks:
            assert chunk.metadata.get("ticker") == "TSLA"
            assert chunk.metadata.get("doc_id") == "test_doc"

    def test_short_text_single_chunk(self):
        """Text shorter than chunk_size should produce exactly one chunk."""
        chunker = RecursiveChunker(tokenizer="gpt2", chunk_size=512)

        text = "Revenue was up 10% year over year."
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].text.strip() == text.strip()


# ================================
# --> Test 6: build_metadata_filter
# ================================

class TestBuildMetadataFilter:
    """Verify Pinecone filter dict construction from keyword arguments."""

    def test_single_values(self):
        """Single-value filters should map directly."""
        result = build_metadata_filter(ticker="AAPL", fiscal_year=2025)
        assert result == {"ticker": "AAPL", "fiscal_year": 2025}

    def test_list_values_use_in_operator(self):
        """List values should use Pinecone's $in operator."""
        result = build_metadata_filter(ticker=["AAPL", "MSFT"])
        assert result == {"ticker": {"$in": ["AAPL", "MSFT"]}}

    def test_none_values_filtered_out(self):
        """None values should be excluded from the filter."""
        result = build_metadata_filter(ticker="AAPL", fiscal_year=None)
        assert result == {"ticker": "AAPL"}

    def test_all_none_returns_none(self):
        """If all values are None, return None (no filter)."""
        result = build_metadata_filter(ticker=None, fiscal_year=None)
        assert result is None

    def test_empty_returns_none(self):
        """No kwargs should return None."""
        result = build_metadata_filter()
        assert result is None

    def test_validation_rejects_invalid_keys(self):
        """Invalid keys should raise ValueError when valid_keys is set."""
        with pytest.raises(ValueError, match="Invalid filter keys"):
            build_metadata_filter(
                valid_keys={"ticker", "fiscal_year"},
                ticker="AAPL",
                bad_key="oops",
            )

    def test_validation_passes_valid_keys(self):
        """Valid keys should pass without error."""
        result = build_metadata_filter(
            valid_keys={"ticker", "fiscal_year"},
            ticker="AAPL",
            fiscal_year=2025,
        )
        assert result == {"ticker": "AAPL", "fiscal_year": 2025}


# ================================
# --> Test 7: VectorSearch (live)
# ================================

class TestVectorSearch:
    """Live search tests against the real Pinecone index + Voyage embeddings."""

    @pytest.fixture(autouse=True)
    def _setup_search(self):
        """Create a shared VectorSearch instance for all tests."""
        self.search = VectorSearch(use_rerank=False, validate_filters=True)

    def test_earnings_call_search(self):
        """Searching earnings_calls for AAPL revenue should return relevant chunks."""
        results = self.search.search(
            query="What was Apple's reported revenue?",
            top_k=5,
            namespace="earnings_calls",
            ticker="AAPL",
        )

        assert len(results) == 5
        assert all(isinstance(r, QueryResult) for r in results)

        # Scores should be sorted descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Every result should have the filtered ticker
        for r in results:
            assert r.metadata["ticker"] == "AAPL"
            assert "text" in r.metadata
            assert len(r.metadata["text"]) > 0

    def test_multi_ticker_filter(self):
        """$in filter with multiple tickers should return results from both."""
        results = self.search.search(
            query="capital expenditures and free cash flow",
            top_k=10,
            namespace="earnings_calls",
            ticker=["AAPL", "MSFT"],
        )

        assert len(results) > 0
        returned_tickers = {r.metadata["ticker"] for r in results}
        # All returned tickers should be within the filter set
        assert returned_tickers.issubset({"AAPL", "MSFT"})

    def test_macro_research_namespace(self):
        """Search should work across different namespaces."""
        results = self.search.search(
            query="Federal Reserve interest rate policy",
            top_k=3,
            namespace="macro_research",
        )

        assert len(results) == 3
        assert all(isinstance(r, QueryResult) for r in results)
        assert all(r.score > 0 for r in results)
