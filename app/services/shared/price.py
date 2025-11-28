from typing import List, Dict, Any, Literal
from datetime import timedelta
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_current_utc_time


class PriceService:
    """
    Service for fetching and formatting stock price data
    """

    def get_stock_prices(self, tickers: List[str], days: int) -> Dict[str, Any]:
        """
        Fetch OHLCV stock price data for multiple tickers over specified number of days.

        Args:
            tickers: List of stock ticker symbols
            days: Number of days of historical data to retrieve

        Returns:
            Dict containing payload (with open, high, low, close, volume) and counts for response envelope

        Raises:
            ValueError: If no price data found for any ticker
        """
        # Calculate date range (using UTC time for consistency)
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=days)

        # Format dates as strings
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # Fetch OHLCV data using the bulk function
        price_data_map = fetch_bulk_ohlcv_data_for_tickers(
            tickers=tickers,
            start_date_str=start_date_str,
            end_date_str=end_date_str
        )

        if not price_data_map:
            raise ValueError(f"No price data found for tickers: {', '.join(tickers)}")

        # Transform data into response format
        payload = []
        for ticker, price_df in price_data_map.items():
            ticker_data = {
                "ticker": ticker,
                "data": [
                    {
                        "date": date.strftime('%Y-%m-%d'),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume'])
                    }
                    for date, row in price_df.iterrows()
                ]
            }
            payload.append(ticker_data)

        # Build counts metadata
        counts = {
            'currentItemCount': len(payload),
            'itemsPerPage': len(payload),
            'startIndex': 1,
            'totalItems': len(payload),
        }

        return {
            'payload': payload,
            'counts': counts
        }

    def get_stock_prices_intraday(
        self,
        tickers: List[str],
        days: int,
        frequency: Literal['15mins', 'hourly'] = '15mins'
    ) -> Dict[str, Any]:
        """
        Fetch intraday OHLCV price data for multiple tickers.

        Args:
            tickers: List of stock ticker symbols
            days: Number of days of historical data to retrieve
            frequency: Data frequency - '15mins' or 'hourly'

        Returns:
            Dict containing payload (with datetime, open, high, low, close, volume) and counts

        Raises:
            ValueError: If no price data found for any ticker
        """
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=days)

        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        price_data_map = fetch_bulk_ohlcv_data_for_tickers(
            tickers=tickers,
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            frequency=frequency
        )

        if not price_data_map:
            raise ValueError(f"No price data found for tickers: {', '.join(tickers)}")

        payload = []
        for ticker, price_df in price_data_map.items():
            ticker_data = {
                "ticker": ticker,
                "data": [
                    {
                        "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume'])
                    }
                    for dt, row in price_df.iterrows()
                ]
            }
            payload.append(ticker_data)

        counts = {
            'currentItemCount': len(payload),
            'itemsPerPage': len(payload),
            'startIndex': 1,
            'totalItems': len(payload),
        }

        return {
            'payload': payload,
            'counts': counts
        }
