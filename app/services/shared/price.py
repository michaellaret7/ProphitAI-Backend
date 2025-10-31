from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_current_utc_time


class PriceService:
    """
    Service for fetching and formatting stock price data
    """

    def get_stock_prices(self, tickers: List[str], days: int) -> Dict[str, Any]:
        """
        Fetch stock price data for multiple tickers over specified number of days.

        Args:
            tickers: List of stock ticker symbols
            days: Number of days of historical data to retrieve

        Returns:
            Dict containing payload and counts for response envelope

        Raises:
            ValueError: If no price data found for any ticker
        """
        # Calculate date range (using UTC time for consistency)
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=days)

        # Format dates as strings
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # Fetch price data using the bulk function
        price_data_map = fetch_bulk_price_data_for_tickers(
            tickers=tickers,
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            frequency='daily'
        )

        if not price_data_map:
            raise ValueError(f"No price data found for tickers: {', '.join(tickers)}")

        # Transform data into response format
        payload = []
        for ticker, price_series in price_data_map.items():
            ticker_data = {
                "ticker": ticker,
                "data": [
                    {
                        "date": date.strftime('%Y-%m-%d'),
                        "close": float(price)
                    }
                    for date, price in price_series.items()
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