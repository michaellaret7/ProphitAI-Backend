"""
Train the BM25 sparse encoder on chunked earnings call transcripts.

Fetches transcripts for all actively trading equities, chunks them using
the EarningsCallChunker, and fits the BM25 encoder on the resulting corpus.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.repositories.transcripts_data import get_earnings_transcripts
from app.core.foundry.chunking.earnings_calls.chunker import EarningsCallChunker
from app.core.foundry.embeddings.sparse_encoder import SparseEncoder


def screen_tickers() -> list[str]:
    """Get all actively trading equities (non-ETFs)."""
    with MarketSession() as session:
        tickers = session.query(Ticker).filter(
            Ticker.is_actively_trading == True,
            Ticker.is_etf == False
        ).all()
        return [str(ticker.ticker) for ticker in tickers]


def train_encoder(max_workers: int = 20, transcripts_per_ticker: int = 14) -> None:
    """
    Train the BM25 sparse encoder on chunked earnings call transcripts.
    

    Args:
        max_workers: Number of parallel threads for fetching transcripts.
        transcripts_per_ticker: Max transcripts to fetch per ticker.
    """
    chunker = EarningsCallChunker()
    corpus: list[str] = []
    transcript_count = 0

    tickers = screen_tickers()
    print(f"Fetching transcripts for {len(tickers)} tickers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(get_earnings_transcripts, ticker, limit=transcripts_per_ticker)
            for ticker in tickers
        ]
        total = len(futures)

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            ticker = result.get('ticker', 'Unknown')
            items = result.get('items', [])

            # Chunk each transcript and add to corpus
            for item in items:
                content = item.get('content')
                if content:
                    chunks = chunker.chunk(content, doc_type="earnings_call")
                    corpus.extend([chunk.text for chunk in chunks])
                    transcript_count += 1

            print(f"[{i}/{total}] {ticker}: {len(items)} transcripts, corpus size: {len(corpus)} chunks")

    print(f"\nTotal transcripts processed: {transcript_count}")
    print(f"Total chunks in corpus: {len(corpus)}")

    # Fit and save the encoder
    print("\nFitting BM25 encoder...")
    encoder = SparseEncoder()
    encoder.fit(corpus)

    save_path = encoder.save()
    print(f"Encoder saved to: {save_path}")


if __name__ == "__main__":
    train_encoder()
