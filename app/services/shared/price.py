from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.repositories.price_data import fetch_bulk_price_data_for_tickers


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
        # Calculate date range
        end_date = datetime.now()
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


class TickerReturnsService:
    """
    Service for calculating and formatting daily returns for a single ticker
    """

    def get_ticker_returns(self, ticker: str, years: int) -> Dict[str, Any]:
        """
        Calculate daily returns for a ticker over specified number of years.

        Args:
            ticker: Stock ticker symbol
            years: Number of years of historical data (1-10)

        Returns:
            Dict containing payload for response envelope with daily returns

        Raises:
            ValueError: If no price data found or invalid parameters
        """
        # Validate inputs
        if not ticker:
            raise ValueError("Ticker is required")
        if years < 1 or years > 10:
            raise ValueError("Years must be between 1 and 10")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        # Format dates as strings
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # Fetch price data
        price_data_map = fetch_bulk_price_data_for_tickers(
            tickers=[ticker.upper()],
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            frequency='daily'
        )

        ticker_upper = ticker.upper()
        if not price_data_map or ticker_upper not in price_data_map:
            raise ValueError(f"No price data found for ticker: {ticker}")

        # Get price series
        price_series = price_data_map[ticker_upper]

        if price_series.empty:
            raise ValueError(f"No price data found for ticker: {ticker}")

        # Calculate daily returns (as decimals: 0.015 = 1.5% gain)
        returns_series = price_series.pct_change()

        # Remove first NaN value from pct_change()
        returns_series = returns_series.dropna()

        # Format returns data
        returns_data = [
            {
                "date": date.strftime('%Y-%m-%d'),
                "return": round(float(ret), 6)  # Round to 6 decimal places for precision
            }
            for date, ret in returns_series.items()
        ]

        return {
            'ticker': ticker_upper,
            'returns': returns_data,
            'startDate': start_date_str,
            'endDate': end_date_str,
            'totalDataPoints': len(returns_data)
        }


if __name__ == "__main__":
    price_service = PriceService()
    print(price_service.get_stock_prices(['AAPL', 'MSFT'], 365))