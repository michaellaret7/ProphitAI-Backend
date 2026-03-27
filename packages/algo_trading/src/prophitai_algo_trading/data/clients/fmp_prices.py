"""FMP API mixin for price data endpoints."""

from datetime import datetime


class FMPPricesMixin:
    """Mixin providing price-related FMP API methods."""

    def get_intraday_prices_for_ticker(self, ticker: str, from_date: datetime, to_date: datetime, interval: str = '15min'):
        """
        Retrieves intraday price data for a ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            from_date (datetime): Start date.
            to_date (datetime): End date.
            interval (str): Time interval - '1min', '5min', '15min', '30min', '1hour', '4hour'. Defaults to '15min'.
        """
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/{interval}/{ticker}?from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}"
        return self._make_fmp_api_request(url)

    def get_daily_prices_for_ticker(self, ticker: str, from_date: datetime, to_date: datetime):
        """
        Retrieves daily OHLCV price data for a ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}"
        return self._make_fmp_api_request(url)

    def get_full_quote(self, ticker: str):
        """
        Retrieves full quote information including current price and market cap.
        """
        url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
        return self._make_fmp_api_request(url)

    def get_batch_quote(self, symbols):
        """
        Retrieves batch quote information for multiple symbols at once.

        Args:
            symbols: Either a list of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
                    or a comma-separated string (e.g., 'AAPL,MSFT,GOOGL')

        Returns:
            list: A list of quote dictionaries containing price, volume, market cap, and other data
        """
        if isinstance(symbols, list):
            symbols_str = ','.join(symbols)
        else:
            symbols_str = symbols

        url = f"https://financialmodelingprep.com/stable/batch-quote?symbols={symbols_str}"
        return self._make_fmp_api_request(url)
