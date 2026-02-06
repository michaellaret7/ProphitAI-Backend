"""
Bulk embed earnings transcripts into Pinecone.

Auto-detects mode based on CSV state:
  - If CSV is empty/missing: populates it with all active non-ETF tickers
  - If CSV has tickers: processes next 10, embeds transcripts, removes from CSV

Run repeatedly until CSV is empty to process all tickers.
"""

import csv
import os
import time
from datetime import datetime

from dotenv import load_dotenv

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.core.foundry.pipeline import Pipeline

load_dotenv()

CSV_PATH = "app/core/foundry/active_tickers.csv"
START_YEAR = 2010
TICKER_BATCH_SIZE = 10


def get_active_non_etf_tickers() -> list[str]:
    """Fetch all active non-ETF tickers from the database."""
    session = MarketSession()
    try:
        tickers = (
            session.query(Ticker.ticker)
            .filter(Ticker.is_actively_trading == True)
            .filter(Ticker.is_etf == False)
            .all()
        )
        return [t[0] for t in tickers]
    finally:
        session.close()


def write_tickers_to_csv(tickers: list[str]) -> None:
    """Write ticker list to CSV file."""
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for ticker in tickers:
            writer.writerow([ticker])
    print(f"Wrote {len(tickers)} tickers to {CSV_PATH}")


def read_tickers_from_csv() -> list[str]:
    """Read remaining tickers from CSV."""
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        return [row["ticker"] for row in reader]


def remove_tickers_from_csv(processed: list[str]) -> int:
    """Remove processed tickers from CSV. Returns remaining count."""
    remaining = read_tickers_from_csv()
    remaining = [t for t in remaining if t not in processed]
    write_tickers_to_csv(remaining)
    return len(remaining)


def fetch_transcripts_for_ticker(fmp: FMP_API_DATA, ticker: str) -> list[dict]:
    """Fetch all earnings transcripts for a ticker from START_YEAR to now."""
    transcripts = []
    current_year = datetime.now().year

    for year in range(START_YEAR, current_year + 1):
        for quarter in range(1, 5):
            data = fmp.get_earnings_transcript(ticker, year, quarter)
            if not data:
                continue

            content = None
            date = None
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get("content")
                date = data[0].get("date")
            elif isinstance(data, dict):
                content = data.get("content")
                date = data.get("date")

            if content:
                transcripts.append({
                    "content": content,
                    "metadata": {
                        "ticker": ticker,
                        "period": quarter,
                        "year": year,
                        "date": date or f"{year}-01-01",
                    },
                })

    return transcripts


def init_csv():
    """Initialize CSV with all active non-ETF tickers."""
    print("Fetching active non-ETF tickers from database...")
    tickers = get_active_non_etf_tickers()
    print(f"Found {len(tickers)} tickers")
    write_tickers_to_csv(tickers)
    print("Done. Run again to start embedding.")


def embed_batch():
    """Process next 10 tickers from CSV, embed transcripts, remove from CSV."""
    tickers = read_tickers_from_csv()
    if not tickers:
        print("No tickers remaining in CSV. Processing complete.")
        return

    batch = tickers[:TICKER_BATCH_SIZE]
    print(f"Processing {len(batch)} tickers ({len(tickers)} remaining total)")

    pipeline = Pipeline(
        namespace="earnings_calls",
        doc_type="earnings_call",
        chunker_type="earnings_call",
    )
    fmp = FMP_API_DATA()

    processed = []
    total_vectors = 0

    for i, ticker in enumerate(batch):
        print(f"\n[{i + 1}/{len(batch)}] {ticker}")
        try:
            transcripts = fetch_transcripts_for_ticker(fmp, ticker)
            if not transcripts:
                print(f"  No transcripts found")
                processed.append(ticker)
                continue

            print(f"  Found {len(transcripts)} transcripts")
            texts = [{"content": t["content"], "metadata": t["metadata"]} for t in transcripts]
            count = pipeline.run(texts=texts)
            total_vectors += count
            print(f"  Embedded {count} vectors")
            processed.append(ticker)

        except Exception as e:
            print(f"  Error: {e}")
            processed.append(ticker)

        time.sleep(0.5)

    remaining = remove_tickers_from_csv(processed)
    print(f"\nBatch complete. Vectors: {total_vectors}. Remaining tickers: {remaining}")


if __name__ == "__main__":
    for i in range(2):
        tickers = read_tickers_from_csv()

        print(f"Found {len(tickers)} tickers in CSV. Processing next batch...")
        embed_batch()
