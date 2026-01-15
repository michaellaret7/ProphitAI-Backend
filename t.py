"""Speed comparison: Batch news endpoint vs sequential single-ticker calls."""
import asyncio
import time
from app.db.core.pull_fmp_data import FMP_API_DATA


async def test_sequential(tickers: list[str], limit: int = 50):
    """Fetch news for each ticker sequentially (old approach)."""
    fmp = FMP_API_DATA()
    results = {}

    for ticker in tickers:
        data = await asyncio.to_thread(fmp.get_stock_news, ticker=ticker, limit=limit)
        results[ticker] = data if data else []

    return results


async def test_batch(tickers: list[str], limit: int = 50):
    """Fetch news for all tickers in one batch call (new approach)."""
    fmp = FMP_API_DATA()
    data = await asyncio.to_thread(fmp.get_batch_stock_news, tickers=tickers, limit=limit)

    # Group by ticker (mimics controller logic)
    results = {ticker: [] for ticker in tickers}
    if data:
        for item in data:
            symbol = item.get('symbol', '').upper()
            if symbol in results:
                results[symbol].append(item)

    return results


async def main():
    tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
    limit = 50

    print("=" * 60)
    print("BATCH NEWS ENDPOINT SPEED COMPARISON")
    print("=" * 60)
    print(f"Tickers: {tickers}")
    print(f"Limit per ticker: {limit}")
    print("-" * 60)

    # Test sequential approach
    print("\n[1] SEQUENTIAL (5 separate API calls)...")
    start = time.perf_counter()
    sequential_results = await test_sequential(tickers, limit)
    sequential_time = time.perf_counter() - start
    sequential_total = sum(len(v) for v in sequential_results.values())
    print(f"    Time: {sequential_time:.3f}s")
    print(f"    Total news items: {sequential_total}")
    for t, news in sequential_results.items():
        print(f"      {t}: {len(news)} items")

    # Test batch approach
    print("\n[2] BATCH (1 API call with comma-separated symbols)...")
    start = time.perf_counter()
    batch_results = await test_batch(tickers, limit)
    batch_time = time.perf_counter() - start
    batch_total = sum(len(v) for v in batch_results.values())
    print(f"    Time: {batch_time:.3f}s")
    print(f"    Total news items: {batch_total}")
    for t, news in batch_results.items():
        print(f"      {t}: {len(news)} items")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Sequential: {sequential_time:.3f}s ({sequential_total} items)")
    print(f"Batch:      {batch_time:.3f}s ({batch_total} items)")

    if batch_time < sequential_time:
        speedup = sequential_time / batch_time
        print(f"\n✅ Batch is {speedup:.1f}x FASTER")
        print(f"   Time saved: {sequential_time - batch_time:.3f}s ({(1 - batch_time/sequential_time) * 100:.1f}%)")
    else:
        print(f"\n⚠️  Sequential was faster (unexpected)")


if __name__ == "__main__":
    asyncio.run(main())
