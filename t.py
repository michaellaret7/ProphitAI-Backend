"""Test script for batch quotes endpoint."""

import asyncio
from app.api.controller.price import get_batch_quotes_controller


async def test_batch_quotes():
    """Test the batch quotes controller."""

    # Test with valid stock symbols
    tickers = ["AAPL", "MSFT", "GOOGL", "NVDA"]

    print("="*60)
    print("Testing Batch Quotes Endpoint")
    print("="*60)
    print(f"\nRequesting quotes for: {tickers}")

    result = await get_batch_quotes_controller(tickers=tickers)

    print(f"\nStatus: {result.get('status')}")
    print(f"Message: {result.get('message')}")

    data = result.get('data', {})
    payload = data.get('payload', {})
    quotes_data = payload.get('data', {})
    missing = payload.get('missing_tickers', [])

    print(f"\nFound: {len(quotes_data)} quotes")
    print(f"Missing: {len(missing)} tickers")

    if missing:
        print(f"Missing tickers: {missing}")

    print("\n" + "-"*60)
    print("Quote Details:")
    print("-"*60)

    for symbol, quote in quotes_data.items():
        print(f"\n{symbol}:")
        print(f"  Price: ${quote.get('price', 'N/A')}")
        print(f"  Change: {quote.get('change', 'N/A')} ({quote.get('changesPercentage', 'N/A')}%)")
        print(f"  Day Range: ${quote.get('dayLow', 'N/A')} - ${quote.get('dayHigh', 'N/A')}")
        print(f"  Volume: {quote.get('volume', 'N/A'):,}")
        print(f"  Market Cap: ${quote.get('marketCap', 0):,.0f}")


async def test_with_invalid_ticker():
    """Test with a mix of valid and invalid tickers."""

    tickers = ["AAPL", "INVALID_TICKER_XYZ", "MSFT"]

    print("\n" + "="*60)
    print("Testing with Invalid Ticker")
    print("="*60)
    print(f"\nRequesting quotes for: {tickers}")

    result = await get_batch_quotes_controller(tickers=tickers)

    data = result.get('data', {})
    payload = data.get('payload', {})
    quotes_data = payload.get('data', {})
    missing = payload.get('missing_tickers', [])

    print(f"\nFound: {len(quotes_data)} quotes: {list(quotes_data.keys())}")
    print(f"Missing: {len(missing)} tickers: {missing}")


async def main():
    await test_batch_quotes()
    await test_with_invalid_ticker()
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
