"""Alpaca Market Data client for historical and real-time price data."""

import os
from datetime import datetime

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.enums import DataFeed
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

load_dotenv()

# Reason: maps string intervals to Alpaca TimeFrame objects
_TIMEFRAME_MAP = {
    '1min': TimeFrame.Minute,
    '5min': TimeFrame(5, 'Min'),
    '15min': TimeFrame(15, 'Min'),
    '30min': TimeFrame(30, 'Min'),
    '1hour': TimeFrame.Hour,
    'daily': TimeFrame.Day,
}


class AlpacaDataClient:
    """Client for Alpaca Market Data API (historical bars and quotes)."""

    def __init__(self, api_key: str | None = None, secret_key: str | None = None, feed: str = 'iex'):
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY')
        self.feed = DataFeed.IEX if feed == 'iex' else DataFeed.SIP

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "API credentials required. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "environment variables or pass them to the constructor."
            )

        self.client = StockHistoricalDataClient(self.api_key, self.secret_key)

    def get_intraday_prices_for_ticker(
        self,
        ticker: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = '15min',
    ) -> list[dict]:
        """Fetch intraday OHLCV bars from Alpaca.

        Args:
            ticker: Stock symbol (e.g. 'AAPL').
            from_date: Start of date range.
            to_date: End of date range.
            interval: '1min', '5min', '15min', '30min', '1hour'.

        Returns:
            List of dicts with keys: date, open, high, low, close, volume.
        """
        timeframe = _TIMEFRAME_MAP.get(interval)
        if not timeframe:
            raise ValueError(f"Unsupported interval '{interval}'. Use one of: {list(_TIMEFRAME_MAP.keys())}")

        request = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=timeframe,
            start=from_date,
            end=to_date,
            feed=self.feed,
        )

        bars = self.client.get_stock_bars(request)
        try:
            bar_list = bars[ticker]
        except KeyError:
            bar_list = []

        return [
            {
                'date': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': int(bar.volume),
            }
            for bar in bar_list
        ]

    def get_daily_prices_for_ticker(
        self,
        ticker: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list[dict]:
        """Fetch daily OHLCV bars from Alpaca.

        Args:
            ticker: Stock symbol.
            from_date: Start date.
            to_date: End date.

        Returns:
            List of dicts with keys: date, open, high, low, close, volume.
        """
        return self.get_intraday_prices_for_ticker(ticker, from_date, to_date, interval='daily')

    def get_latest_quote(self, ticker: str) -> dict | None:
        """Fetch the latest quote (bid/ask) for a ticker.

        Args:
            ticker: Stock symbol.

        Returns:
            Dict with bid_price, ask_price, bid_size, ask_size, or None on failure.
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=ticker, feed=self.feed)
            quotes = self.client.get_stock_latest_quote(request)
            quote = quotes.get(ticker)
            if not quote:
                return None
            return {
                'bid_price': quote.bid_price,
                'ask_price': quote.ask_price,
                'bid_size': quote.bid_size,
                'ask_size': quote.ask_size,
                'timestamp': quote.timestamp,
            }
        except Exception as e:
            print(f"Error fetching latest quote for {ticker}: {e}")
            return None
