from app.core.foundry.pipeline import IngestionPipeline
from app.core.foundry.models.pipeline import IngestionItem
from app.core.foundry.models.metadata import EarningsCallMetadata
from app.repositories.transcripts_data import get_earnings_transcripts

def test_pipeline_with_multiple_calls_per_ticker():
    tickers = ["VLO", "CLH", "GOOGL"]
    items = []

    for ticker in tickers:
        # Get all available transcripts for this ticker
        result = get_earnings_transcripts(ticker, limit=4)

        # result structure: {'ticker': 'VLO', 'count': 2, 'items': [...]}
        for transcript in result["items"]:
            # Reason: Build full transcript dict for EarningsCallMetadata
            full_transcript = {
                "ticker": ticker,
                "period": transcript["period"],
                "year": transcript["year"],
                "date": transcript.get("date", "1970-01-01"),
                "content": transcript["content"],
            }
            metadata = EarningsCallMetadata.from_transcript(full_transcript).to_chunk_metadata()
            metadata["doc_type"] = "earnings_call"

            items.append(IngestionItem(
                source_type="text",
                content=transcript["content"],
                metadata=metadata,
            ))

    pipeline = IngestionPipeline(namespace="earnings_calls")
    result = pipeline.run(items)

    print(result)

    print(f"Ingested {len(items)} transcripts, {result.total_chunks} chunks")  

