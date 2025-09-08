import os
import requests
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta

class FMP_API_DATA: 
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            print("Error: FMP_API_KEY not found in environment variables.")

    def _make_fmp_api_request(self, url: str):
        """Helper function to make requests to the FMP API."""
        if not self.api_key:
            return None
        
        separator = '&' if '?' in url else '?'
        full_url = f"{url}{separator}apikey={self.api_key}"
        
        try:
            response = requests.get(full_url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    def get_analyst_estimates(self, ticker: str, period: str = 'quarter', page: int = 0, limit: int = 1000):
        """
        Retrieves analyst financial estimates for a given stock ticker from Financial Modeling Prep.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
            page (int): The page number for pagination. Defaults to 0.
            limit (int): The number of records per page. Defaults to 10.

        Returns:
            dict: A dictionary containing the analyst estimate data, or None if an error occurs.
        """
        url = f"https://financialmodelingprep.com/stable/analyst-estimates?symbol={ticker}&period={period}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_earnings_surprises(self, ticker: str):
        """
        Retrieves historical earnings surprises for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/earnings-surprises/{ticker}"
        return self._make_fmp_api_request(url)

    def get_analyst_recommendations(self, ticker: str):
        """
        Retrieves current analyst recommendations for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/rating/{ticker}"
        return self._make_fmp_api_request(url)

    def get_cash_flow_statements(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves cash flow statements for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_balance_sheets(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves balance sheet statements for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_income_statements(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves income statements for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_financial_ratios(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves financial ratios for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/ratios/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_key_metrics(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves key metrics for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_financial_scores(self, ticker: str):
        """
        Retrieves financial scores for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/financial-scores?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_revenue_product_segmentation(self, ticker: str):
        """
        Retrieves revenue product segmentation for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/revenue-product-segmentation?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_revenue_geographic_segmentation(self, ticker: str):
        """
        Retrieves revenue geographic segmentation for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/revenue-geographic-segmentation?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_etf_holdings(self, ticker: str):
        """
        Retrieves holdings for a given ETF or mutual fund.
        """
        url = f"https://financialmodelingprep.com/stable/etf/holdings?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_etf_info(self, ticker: str):
        """
        Retrieves information for a given ETF or mutual fund.
        """
        url = f"https://financialmodelingprep.com/stable/etf/info?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_dividends(self, ticker: str):
        """
        Retrieves dividend information for a given stock.
        """
        url = f"https://financialmodelingprep.com/stable/dividends?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_press_releases(self, ticker: str, limit: int = 1000):
        """
        Retrieves press releases for a given stock.
        """
        url = f"https://financialmodelingprep.com/stable/news/press-releases?symbols={ticker}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_stock_news(self, ticker: str, limit: int = 1000):
        """
        Retrieves news for a given stock.
        """
        url = f"https://financialmodelingprep.com/stable/news/stock?symbols={ticker}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_general_news(self, limit: int = 1000):
        """
        Retrieves general news.
        """
        url = f"https://financialmodelingprep.com/stable/news/general-latest?limit={limit}"
        return self._make_fmp_api_request(url)

    def get_earnings_transcript(self, ticker: str, year: int, quarter: int):
        """
        Retrieves the earnings call transcript for a given stock, year, and quarter.
        """
        url = f"https://financialmodelingprep.com/stable/earning-call-transcript?symbol={ticker}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_rating_scores(self, ticker: str, limit: int = 1000):
        """
        Retrieves historical ratings for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/ratings-historical?symbol={ticker}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_price_target_summary(self, ticker: str):
        """
        Retrieves the price target summary for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/price-target-summary?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_price_target_news(self, ticker: str, page: int = 0, limit: int = 1000):
        """
        Retrieves price target news for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/price-target-news?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_stock_grades_individual(self, ticker: str, limit: int = 10000):
        """
        Retrieves stock grades for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/grades?symbol={ticker}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_stock_grades_summary(self, ticker: str, limit: int = 100):
        """
        Retrieves historical stock grades for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/grades-historical?symbol={ticker}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_stock_grade_news(self, ticker: str, page: int = 0, limit: int = 1000):
        """
        Retrieves stock grade news for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/grades-news?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_intraday_prices_for_ticker(self, ticker: str, from_date: datetime, to_date: datetime):
        """
        Retrieves 15-minute interval price data for a ticker for the last two weeks.
        """
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/15min/{ticker}?from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}"
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
