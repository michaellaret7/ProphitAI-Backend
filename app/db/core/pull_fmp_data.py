import os
import requests
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import pandas as pd
import time

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
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(full_url)
                
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16s
                    print(f"Rate limit hit (429). Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    print(f"An error occurred after {max_retries} attempts: {e}")
                    return None
                time.sleep(1)
        
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

    def get_etf_country_weightings(self, ticker: str):
        """
        Retrieves country weightings for a given ETF.
        """
        url = f"https://financialmodelingprep.com/stable/etf/country-weightings?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_dividends(self, ticker: str):
        """
        Retrieves dividend information for a given stock.
        """
        url = f"https://financialmodelingprep.com/stable/dividends?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_press_releases(self, ticker: str, limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Retrieves press releases for a given stock.

        Args:
            ticker (str): The stock ticker symbol.
            limit (int): Maximum number of results to return. Defaults to 1000.
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/news/press-releases?symbols={ticker}&limit={limit}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_stock_news(self, ticker: str, limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Retrieves news for a given stock.

        Args:
            ticker (str): The stock ticker symbol.
            limit (int): Maximum number of results to return. Defaults to 1000.
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/news/stock?symbols={ticker}&limit={limit}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_general_news(self, limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Retrieves general news.

        Args:
            limit (int): Maximum number of results to return. Defaults to 1000.
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/news/general-latest?limit={limit}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_fmp_articles(self, page: int = 0, limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Retrieves FMP articles.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Maximum number of results to return per page. Defaults to 1000.
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/fmp-articles?page={page}&limit={limit}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
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

    def get_company_profile(self, ticker: str):
        """
        Retrieves company profile including beta, IPO date, and company details.
        """
        url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}"
        return self._make_fmp_api_request(url)
    
    def search_by_symbol(self, query: str):
        """
        Searches for securities by ticker symbol.

        Args:
            query (str): The ticker symbol to search for (e.g., 'MSFT', 'AAPL').

        Returns:
            list: Matching securities with symbol, name, currency, exchange info.
        """
        url = f"https://financialmodelingprep.com/stable/search-symbol?query={query}"
        return self._make_fmp_api_request(url)

    def search_by_name(self, query: str):
        """
        Searches for securities by company name.

        Args:
            query (str): The company name to search for (e.g., 'Apple', 'Microsoft').

        Returns:
            list: Matching securities with symbol, name, currency, exchange info.
        """
        url = f"https://financialmodelingprep.com/stable/search-name?query={query}"
        return self._make_fmp_api_request(url)

    def search_by_cusip(self, cusip: str):
        """
        Searches for securities by CUSIP identifier.

        Args:
            cusip (str): The CUSIP number (e.g., '037833100' for Apple).

        Returns:
            list: Matching securities with symbol, name, and CUSIP info.
        """
        url = f"https://financialmodelingprep.com/stable/search-cusip?cusip={cusip}"
        return self._make_fmp_api_request(url)

    def search_by_isin(self, isin: str):
        """
        Searches for securities by ISIN (International Securities Identification Number).

        Args:
            isin (str): The ISIN number (e.g., 'US0378331005' for Apple).

        Returns:
            list: Matching securities with symbol, name, and ISIN info.
        """
        url = f"https://financialmodelingprep.com/stable/search-isin?isin={isin}"
        return self._make_fmp_api_request(url)

    def search_by_cik(self, cik: str):
        """
        Searches for securities by CIK (SEC Central Index Key).

        Args:
            cik (str): The CIK number (e.g., '320193' for Apple).

        Returns:
            list: Matching securities with symbol, name, and CIK info.
        """
        url = f"https://financialmodelingprep.com/stable/search-cik?cik={cik}"
        return self._make_fmp_api_request(url)

    def get_isin_lookup(self, isin: str):
        """
        Retrieves security information by ISIN (International Securities Identification Number).
        Returns symbol, security type, and other details.

        Note: Consider using search_by_isin() instead for consistency.
        """
        url = f"https://financialmodelingprep.com/stable/search-isin?isin={isin}"
        return self._make_fmp_api_request(url)

    def get_company_notes(self, ticker: str):
        """
        Retrieves company notes and bonds information for a given stock ticker.
        """
        url = f"https://financialmodelingprep.com/stable/company-notes?symbol={ticker}"
        return self._make_fmp_api_request(url)
    
    def get_stock_peers(self, ticker: str):
        """
        Retrieves stock peers for a given ticker.
        Returns a list of peer companies in the same sector/industry.
        """
        url = f"https://financialmodelingprep.com/stable/stock-peers?symbol={ticker}"
        return self._make_fmp_api_request(url)
 
    def get_esg_disclosures(self, ticker: str):
        """
        Retrieves ESG (Environmental, Social, Governance) disclosures for a given stock ticker.
        Returns ESG ratings and sustainability metrics.
        """
        url = f"https://financialmodelingprep.com/stable/esg-disclosures?symbol={ticker}"
        return self._make_fmp_api_request(url)
 
    def get_institutional_holder_analytics(self, ticker: str, year: int, quarter: int):
        """
        Retrieves institutional ownership analytics for a given stock ticker.
        Returns holder analytics data for specified year and quarter.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            year (int): The year (e.g., 2025).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/extract-analytics/holder?symbol={ticker}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_institutional_positions_summary(self, ticker: str, year: int, quarter: int):
        """
        Retrieves institutional ownership positions summary for a given stock ticker.
        Returns summary of institutional positions for specified year and quarter.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            year (int): The year (e.g., 2023).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/symbol-positions-summary?symbol={ticker}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_institutional_holder_analytics(self, ticker: str, year: int, quarter: int):
        """
        Retrieves institutional ownership analytics for a given stock ticker.
        Returns holder analytics data for specified year and quarter.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            year (int): The year (e.g., 2025).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/extract-analytics/holder?symbol={ticker}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)
    
    def get_historical_sector_performance(self, sector: str, from_date: str = None, to_date: str = None):
        """
        Retrieves historical sector performance for a given sector.
        Returns historical performance data for the specified sector.

        Args:
            sector (str): The sector name (e.g., 'Energy', 'Technology', 'Healthcare').
            from_date (str, optional): Start date in YYYY-MM-DD format (e.g., '2024-02-01').
            to_date (str, optional): End date in YYYY-MM-DD format (e.g., '2024-03-01').
        """
        url = f"https://financialmodelingprep.com/stable/historical-sector-performance?sector={sector}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_historical_industry_performance(self, industry: str, from_date: str = None, to_date: str = None):
        """
        Retrieves historical industry performance for a given industry.
        Returns historical performance data for the specified industry.

        Args:
            industry (str): The industry name (e.g., 'Biotechnology', 'Software', 'Banks').
            from_date (str, optional): Start date in YYYY-MM-DD format (e.g., '2024-02-01').
            to_date (str, optional): End date in YYYY-MM-DD format (e.g., '2024-03-01').
        """
        url = f"https://financialmodelingprep.com/stable/historical-industry-performance?industry={industry}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_historical_sector_pe(self, sector: str, from_date: str = None, to_date: str = None):
        """
        Retrieves historical P/E ratio data for a given sector.
        Returns historical price-to-earnings ratios for the specified sector.

        Args:
            sector (str): The sector name (e.g., 'Energy', 'Technology', 'Healthcare').
            from_date (str, optional): Start date in YYYY-MM-DD format (e.g., '2024-02-01').
            to_date (str, optional): End date in YYYY-MM-DD format (e.g., '2024-03-01').
        """
        url = f"https://financialmodelingprep.com/stable/historical-sector-pe?sector={sector}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_historical_industry_pe(self, industry: str, from_date: str = None, to_date: str = None):
        """
        Retrieves historical P/E ratio data for a given industry.
        Returns historical price-to-earnings ratios for the specified industry.

        Args:
            industry (str): The industry name (e.g., 'Biotechnology', 'Software', 'Banks').
            from_date (str, optional): Start date in YYYY-MM-DD format (e.g., '2024-02-01').
            to_date (str, optional): End date in YYYY-MM-DD format (e.g., '2024-03-01').
        """
        url = f"https://financialmodelingprep.com/stable/historical-industry-pe?industry={industry}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_mergers_acquisitions_latest(self, page: int = 0, limit: int = 1000):
        """
        Retrieves the latest mergers and acquisitions data.
        Returns information about recent M&A transactions including acquiring and target companies.

        Args:
            page (int): The page number for pagination. Defaults to 0.
            limit (int): The number of records per page. Defaults to 1000.
        """
        url = f"https://financialmodelingprep.com/stable/mergers-acquisitions-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_mergers_acquisitions_search(self, name: str):
        """
        Searches for mergers and acquisitions by company name.
        Returns M&A transactions involving the specified company.

        Args:
            name (str): The company name to search for (e.g., 'MICROSOFT', 'APPLE').
        """
        url = f"https://financialmodelingprep.com/stable/mergers-acquisitions-search?name={name}"
        return self._make_fmp_api_request(url)

    # Company Information Endpoints
    def get_profile_by_cik(self, cik: str):
        """
        Retrieves company profile by CIK (Central Index Key).

        Args:
            cik (str): The CIK number (e.g., '0000320193' for Apple).
        """
        url = f"https://financialmodelingprep.com/stable/profile-cik?cik={cik}"
        return self._make_fmp_api_request(url)

    def get_delisted_companies(self, page: int = 0, limit: int = 1000):
        """
        Retrieves list of delisted companies.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 1000.
        """
        url = f"https://financialmodelingprep.com/stable/delisted-companies?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_employee_count(self, ticker: str):
        """
        Retrieves current employee count for a given company.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/employee-count?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_historical_employee_count(self, ticker: str):
        """
        Retrieves historical employee count data for a given company.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/historical-employee-count?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_market_capitalization(self, ticker: str):
        """
        Retrieves current market capitalization for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/market-capitalization?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_market_capitalization_batch(self, symbols):
        """
        Retrieves market capitalization for multiple stocks at once.

        Args:
            symbols: Either a list of ticker symbols or a comma-separated string.
        """
        if isinstance(symbols, list):
            symbols_str = ','.join(symbols)
        else:
            symbols_str = symbols
        url = f"https://financialmodelingprep.com/stable/market-capitalization-batch?symbols={symbols_str}"
        return self._make_fmp_api_request(url)

    def get_historical_market_capitalization(self, ticker: str, from_date: str = None, to_date: str = None):
        """
        Retrieves historical market capitalization data for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/historical-market-capitalization?symbol={ticker}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_shares_float(self, ticker: str):
        """
        Retrieves shares float data for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/shares-float?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_shares_float_all(self):
        """
        Retrieves shares float data for all available stocks.
        """
        url = "https://financialmodelingprep.com/stable/shares-float-all"
        return self._make_fmp_api_request(url)

    def get_key_executives(self, ticker: str):
        """
        Retrieves key executives information for a given company.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/key-executives?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_executive_compensation(self, ticker: str):
        """
        Retrieves executive compensation data for a given company.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/governance-executive-compensation?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_executive_compensation_benchmark(self, year: int):
        """
        Retrieves executive compensation benchmark data for a given year.

        Args:
            year (int): The year (e.g., 2024).
        """
        url = f"https://financialmodelingprep.com/stable/executive-compensation-benchmark?year={year}"
        return self._make_fmp_api_request(url)

    # Quote - Exchange & Asset Lists Endpoints
    def get_batch_exchange_quote(self, exchange: str):
        """
        Retrieves batch quote data for all stocks on a specific exchange.

        Args:
            exchange (str): The exchange code (e.g., 'NASDAQ', 'NYSE').
        """
        url = f"https://financialmodelingprep.com/stable/batch-exchange-quote?exchange={exchange}"
        return self._make_fmp_api_request(url)

    def get_batch_mutualfund_quotes(self):
        """
        Retrieves batch quote data for all mutual funds.
        """
        url = "https://financialmodelingprep.com/stable/batch-mutualfund-quotes"
        return self._make_fmp_api_request(url)

    def get_batch_etf_quotes(self):
        """
        Retrieves batch quote data for all ETFs.
        """
        url = "https://financialmodelingprep.com/stable/batch-etf-quotes"
        return self._make_fmp_api_request(url)

    def get_batch_commodity_quotes(self):
        """
        Retrieves batch quote data for all commodities.
        """
        url = "https://financialmodelingprep.com/stable/batch-commodity-quotes"
        return self._make_fmp_api_request(url)

    def get_batch_crypto_quotes(self):
        """
        Retrieves batch quote data for all cryptocurrencies.
        """
        url = "https://financialmodelingprep.com/stable/batch-crypto-quotes"
        return self._make_fmp_api_request(url)

    def get_batch_forex_quotes(self):
        """
        Retrieves batch quote data for all forex pairs.
        """
        url = "https://financialmodelingprep.com/stable/batch-forex-quotes"
        return self._make_fmp_api_request(url)

    def get_batch_index_quotes(self):
        """
        Retrieves batch quote data for all market indices.
        """
        url = "https://financialmodelingprep.com/stable/batch-index-quotes"
        return self._make_fmp_api_request(url)

    # Financial Statements & Ratios Endpoints
    def get_latest_financial_statements(self, ticker: str):
        """
        Retrieves the latest financial statements for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/latest-financial-statements?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_income_statement_ttm(self, ticker: str):
        """
        Retrieves trailing twelve months (TTM) income statement for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period=ttm"
        return self._make_fmp_api_request(url)

    def get_balance_sheet_ttm(self, ticker: str):
        """
        Retrieves trailing twelve months (TTM) balance sheet for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period=ttm"
        return self._make_fmp_api_request(url)

    def get_cash_flow_statement_ttm(self, ticker: str):
        """
        Retrieves trailing twelve months (TTM) cash flow statement for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period=ttm"
        return self._make_fmp_api_request(url)

    def get_key_metrics_ttm(self, ticker: str):
        """
        Retrieves trailing twelve months (TTM) key metrics for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}"
        return self._make_fmp_api_request(url)

    def get_ratios_ttm(self, ticker: str):
        """
        Retrieves trailing twelve months (TTM) financial ratios for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}"
        return self._make_fmp_api_request(url)

    def get_owner_earnings(self, ticker: str):
        """
        Retrieves owner earnings data for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/owner-earnings?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_enterprise_values(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves enterprise values for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v3/enterprise-values/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_income_statement_growth(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves income statement growth metrics for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v3/income-statement-growth/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_balance_sheet_growth(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves balance sheet growth metrics for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement-growth/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_cash_flow_statement_growth(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves cash flow statement growth metrics for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement-growth/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    def get_financial_growth(self, ticker: str, period: str = 'quarter'):
        """
        Retrieves overall financial growth metrics for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v3/financial-growth/{ticker}?period={period}"
        return self._make_fmp_api_request(url)

    # Economics Endpoints
    def get_treasury_rates(self, from_date: str = None, to_date: str = None):
        """
        Retrieves treasury rates data.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/api/v4/treasury"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_economic_indicators(self, name: str, from_date: str = None, to_date: str = None):
        """
        Retrieves economic indicator data by name.

        Args:
            name (str): The economic indicator name (e.g., 'GDP', 'realGDP', 'unemploymentRate').
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/api/v4/economic?name={name}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_economic_calendar(self, from_date: str = None, to_date: str = None):
        """
        Retrieves economic calendar events.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/api/v3/economic_calendar"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_market_risk_premium(self):
        """
        Retrieves market risk premium data.
        """
        url = "https://financialmodelingprep.com/api/v4/market_risk_premium"
        return self._make_fmp_api_request(url)

    # Earnings, Dividends & Splits Endpoints
    def get_dividends_calendar(self, from_date: str = None, to_date: str = None):
        """
        Retrieves dividend calendar for upcoming dividends.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/api/v3/stock_dividend_calendar"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_earnings(self, ticker: str):
        """
        Retrieves earnings data for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/earnings/{ticker}"
        return self._make_fmp_api_request(url)

    def get_earnings_calendar(self, from_date: str = None, to_date: str = None):
        """
        Retrieves earnings calendar for upcoming earnings reports.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/api/v3/earning_calendar"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_ipos_calendar(self, from_date: str = None, to_date: str = None):
        """
        Retrieves IPO calendar for upcoming initial public offerings.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/api/v3/ipo_calendar"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_ipos_disclosure(self, ticker: str):
        """
        Retrieves IPO disclosure information for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/ipos-disclosure?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_ipos_prospectus(self, ticker: str):
        """
        Retrieves IPO prospectus information for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/ipos-prospectus?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_stock_splits(self, ticker: str):
        """
        Retrieves historical stock splits for a given ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_split/{ticker}"
        return self._make_fmp_api_request(url)

    def get_stock_splits_calendar(self, from_date: str = None, to_date: str = None):
        """
        Retrieves stock splits calendar for upcoming splits.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/api/v3/stock_split_calendar"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    # Earnings Transcript Endpoints
    def get_latest_earnings_transcript(self, ticker: str):
        """
        Retrieves the latest earnings call transcript for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/earning-call-transcript-latest?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_earnings_transcript_dates(self, ticker: str):
        """
        Retrieves available earnings call transcript dates for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/earning-call-transcript-dates?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_earnings_transcript_list(self):
        """
        Retrieves a list of all available earnings call transcripts.
        """
        url = "https://financialmodelingprep.com/stable/earnings-transcript-list"
        return self._make_fmp_api_request(url)

    # News Endpoints
    def get_latest_press_releases(self, page: int = 0, limit: int = 1000):
        """
        Retrieves the latest press releases.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Maximum number of results to return. Defaults to 1000.
        """
        url = f"https://financialmodelingprep.com/stable/news/press-releases-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_latest_stock_news(self, page: int = 0, limit: int = 1000):
        """
        Retrieves the latest stock news.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Maximum number of results to return. Defaults to 1000.
        """
        url = f"https://financialmodelingprep.com/stable/news/stock-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_latest_crypto_news(self, page: int = 0, limit: int = 1000):
        """
        Retrieves the latest cryptocurrency news.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Maximum number of results to return. Defaults to 1000.
        """
        url = f"https://financialmodelingprep.com/stable/news/crypto-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_latest_forex_news(self, page: int = 0, limit: int = 1000):
        """
        Retrieves the latest forex news.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Maximum number of results to return. Defaults to 1000.
        """
        url = f"https://financialmodelingprep.com/stable/news/forex-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_crypto_news(self, symbols: str = None, limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Retrieves crypto news with optional filters.

        Args:
            symbols (str, optional): Comma-separated list of crypto symbols.
            limit (int): Maximum number of results to return. Defaults to 1000.
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/news/crypto?limit={limit}"
        if symbols:
            url += f"&symbols={symbols}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    def get_forex_news(self, symbols: str = None, limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Retrieves forex news with optional filters.

        Args:
            symbols (str, optional): Comma-separated list of forex pairs.
            limit (int): Maximum number of results to return. Defaults to 1000.
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/news/forex?limit={limit}"
        if symbols:
            url += f"&symbols={symbols}"
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        return self._make_fmp_api_request(url)

    # Form 13F / Institutional Ownership Endpoints
    def get_institutional_ownership_latest(self):
        """
        Retrieves the latest institutional ownership filings.
        """
        url = "https://financialmodelingprep.com/stable/institutional-ownership/latest"
        return self._make_fmp_api_request(url)

    def get_institutional_ownership_extract(self, cik: str, year: int, quarter: int):
        """
        Retrieves institutional ownership extract for a specific CIK, year, and quarter.

        Args:
            cik (str): The CIK number of the institution.
            year (int): The year (e.g., 2024).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/extract?cik={cik}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_institutional_ownership_dates(self, cik: str):
        """
        Retrieves available filing dates for a given institution CIK.

        Args:
            cik (str): The CIK number of the institution.
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/dates?cik={cik}"
        return self._make_fmp_api_request(url)

    def get_institutional_holder_performance(self, ticker: str, year: int, quarter: int):
        """
        Retrieves institutional holder performance summary for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            year (int): The year (e.g., 2024).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/holder-performance-summary?symbol={ticker}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_institutional_holder_industry_breakdown(self, cik: str, year: int, quarter: int):
        """
        Retrieves institutional holder industry breakdown.

        Args:
            cik (str): The CIK number of the institution.
            year (int): The year (e.g., 2024).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/holder-industry-breakdown?cik={cik}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_institutional_industry_summary(self, industry: str, year: int, quarter: int):
        """
        Retrieves institutional ownership summary by industry.

        Args:
            industry (str): The industry name.
            year (int): The year (e.g., 2024).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/institutional-ownership/industry-summary?industry={industry}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    # Analyst Endpoints
    def get_ratings_snapshot(self, ticker: str):
        """
        Retrieves the current analyst ratings snapshot for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/ratings-snapshot?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_price_target_consensus(self, ticker: str):
        """
        Retrieves the price target consensus for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/price-target-consensus?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_grades_consensus(self, ticker: str):
        """
        Retrieves the analyst grades consensus for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/grades-consensus?symbol={ticker}"
        return self._make_fmp_api_request(url)

    # Technical Indicators Endpoints
    def get_technical_indicator_sma(self, ticker: str, period: int = 10, interval: str = '1day'):
        """
        Retrieves Simple Moving Average (SMA) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 10.
            interval (str): The time interval (e.g., '1min', '5min', '15min', '30min', '1hour', '4hour', '1day'). Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=sma&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_ema(self, ticker: str, period: int = 10, interval: str = '1day'):
        """
        Retrieves Exponential Moving Average (EMA) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 10.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=ema&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_wma(self, ticker: str, period: int = 10, interval: str = '1day'):
        """
        Retrieves Weighted Moving Average (WMA) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 10.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=wma&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_dema(self, ticker: str, period: int = 10, interval: str = '1day'):
        """
        Retrieves Double Exponential Moving Average (DEMA) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 10.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=dema&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_tema(self, ticker: str, period: int = 10, interval: str = '1day'):
        """
        Retrieves Triple Exponential Moving Average (TEMA) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 10.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=tema&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_rsi(self, ticker: str, period: int = 14, interval: str = '1day'):
        """
        Retrieves Relative Strength Index (RSI) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 14.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=rsi&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_stddev(self, ticker: str, period: int = 10, interval: str = '1day'):
        """
        Retrieves Standard Deviation technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 10.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=standardDeviation&period={period}"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_williams(self, ticker: str, interval: str = '1day'):
        """
        Retrieves Williams %R technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=williams"
        return self._make_fmp_api_request(url)

    def get_technical_indicator_adx(self, ticker: str, period: int = 14, interval: str = '1day'):
        """
        Retrieves Average Directional Index (ADX) technical indicator.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            period (int): The period for calculation. Defaults to 14.
            interval (str): The time interval. Defaults to '1day'.
        """
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{ticker}?type=adx&period={period}"
        return self._make_fmp_api_request(url)

    # ETF & Mutual Funds Endpoints
    def get_etf_asset_exposure(self, ticker: str):
        """
        Retrieves asset exposure breakdown for a given ETF.

        Args:
            ticker (str): The ETF ticker symbol (e.g., 'SPY').
        """
        url = f"https://financialmodelingprep.com/stable/etf/asset-exposure?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_etf_sector_weightings(self, ticker: str):
        """
        Retrieves sector weightings for a given ETF.

        Args:
            ticker (str): The ETF ticker symbol (e.g., 'SPY').
        """
        url = f"https://financialmodelingprep.com/stable/etf/sector-weightings?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_funds_disclosure_holders_latest(self):
        """
        Retrieves the latest mutual fund disclosure holders.
        """
        url = "https://financialmodelingprep.com/stable/funds/disclosure-holders-latest"
        return self._make_fmp_api_request(url)

    def get_funds_disclosure(self, cik: str, year: int, quarter: int):
        """
        Retrieves mutual fund disclosure for a specific CIK, year, and quarter.

        Args:
            cik (str): The CIK number of the fund.
            year (int): The year (e.g., 2024).
            quarter (int): The quarter (1-4).
        """
        url = f"https://financialmodelingprep.com/stable/funds/disclosure?cik={cik}&year={year}&quarter={quarter}"
        return self._make_fmp_api_request(url)

    def get_funds_disclosure_holders_search(self, name: str):
        """
        Searches for mutual fund disclosure holders by name.

        Args:
            name (str): The fund name to search for.
        """
        url = f"https://financialmodelingprep.com/stable/funds/disclosure-holders-search?name={name}"
        return self._make_fmp_api_request(url)

    def get_funds_disclosure_dates(self, cik: str):
        """
        Retrieves available disclosure dates for a given mutual fund CIK.

        Args:
            cik (str): The CIK number of the fund.
        """
        url = f"https://financialmodelingprep.com/stable/funds/disclosure-dates?cik={cik}"
        return self._make_fmp_api_request(url)

    # SEC Filings & Industry Classification Endpoints
    def get_sec_filings_8k(self, ticker: str, page: int = 0, limit: int = 100):
        """
        Retrieves 8-K SEC filings for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-8k?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_sec_filings_financials(self, ticker: str, page: int = 0, limit: int = 100):
        """
        Retrieves financial SEC filings (10-K, 10-Q) for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-financials?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_sec_filings_by_form_type(self, form_type: str, page: int = 0, limit: int = 100):
        """
        Searches SEC filings by form type.

        Args:
            form_type (str): The SEC form type (e.g., '10-K', '10-Q', '8-K', 'DEF 14A').
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-search/form-type?formType={form_type}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_sec_filings_by_symbol(self, ticker: str, page: int = 0, limit: int = 100):
        """
        Searches SEC filings by stock ticker symbol.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-search/symbol?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_sec_filings_by_cik(self, cik: str, page: int = 0, limit: int = 100):
        """
        Searches SEC filings by CIK number.

        Args:
            cik (str): The CIK number (e.g., '0000320193' for Apple).
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-search/cik?cik={cik}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_sec_company_by_name(self, name: str):
        """
        Searches for SEC company information by company name.

        Args:
            name (str): The company name to search for.
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-company-search/name?name={name}"
        return self._make_fmp_api_request(url)

    def get_sec_company_by_symbol(self, ticker: str):
        """
        Retrieves SEC company information by stock ticker symbol.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-company-search/symbol?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_sec_company_by_cik(self, cik: str):
        """
        Retrieves SEC company information by CIK number.

        Args:
            cik (str): The CIK number (e.g., '0000320193' for Apple).
        """
        url = f"https://financialmodelingprep.com/stable/sec-filings-company-search/cik?cik={cik}"
        return self._make_fmp_api_request(url)

    def get_sec_profile(self, ticker: str):
        """
        Retrieves SEC profile for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/sec-profile?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_sic_classification_list(self):
        """
        Retrieves the list of Standard Industrial Classification (SIC) codes.
        """
        url = "https://financialmodelingprep.com/stable/standard-industrial-classification-list"
        return self._make_fmp_api_request(url)

    def get_industry_classification_search(self, industry: str):
        """
        Searches for companies by industry classification.

        Args:
            industry (str): The industry name to search for.
        """
        url = f"https://financialmodelingprep.com/stable/industry-classification-search?industry={industry}"
        return self._make_fmp_api_request(url)

    def get_all_industry_classifications(self):
        """
        Retrieves all available industry classifications.
        """
        url = "https://financialmodelingprep.com/stable/all-industry-classification"
        return self._make_fmp_api_request(url)

    # Insider Trades Endpoints
    def get_insider_trading_latest(self):
        """
        Retrieves the latest insider trading transactions.
        """
        url = "https://financialmodelingprep.com/stable/insider-trading/latest"
        return self._make_fmp_api_request(url)

    def get_insider_trading_search(self, ticker: str, page: int = 0, limit: int = 100):
        """
        Searches insider trading transactions by stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/insider-trading/search?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_insider_trading_by_name(self, name: str, page: int = 0, limit: int = 100):
        """
        Searches insider trading transactions by reporting person name.

        Args:
            name (str): The name of the reporting person.
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/insider-trading/reporting-name?name={name}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_insider_trading_transaction_types(self):
        """
        Retrieves list of insider trading transaction types.
        """
        url = "https://financialmodelingprep.com/stable/insider-trading-transaction-type"
        return self._make_fmp_api_request(url)

    def get_insider_trading_statistics(self, ticker: str):
        """
        Retrieves insider trading statistics for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/insider-trading/statistics?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_acquisition_of_beneficial_ownership(self, ticker: str, page: int = 0, limit: int = 100):
        """
        Retrieves Form 4 beneficial ownership acquisitions for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/acquisition-of-beneficial-ownership?symbol={ticker}&page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    # Market Hours Endpoints
    def get_exchange_market_hours(self, exchange: str):
        """
        Retrieves market hours for a specific exchange.

        Args:
            exchange (str): The exchange code (e.g., 'NYSE', 'NASDAQ').
        """
        url = f"https://financialmodelingprep.com/stable/exchange-market-hours?exchange={exchange}"
        return self._make_fmp_api_request(url)

    def get_holidays_by_exchange(self, exchange: str, year: int):
        """
        Retrieves holidays for a specific exchange and year.

        Args:
            exchange (str): The exchange code (e.g., 'NYSE', 'NASDAQ').
            year (int): The year (e.g., 2024).
        """
        url = f"https://financialmodelingprep.com/stable/holidays-by-exchange?exchange={exchange}&year={year}"
        return self._make_fmp_api_request(url)

    def get_all_exchange_market_hours(self):
        """
        Retrieves market hours for all exchanges.
        """
        url = "https://financialmodelingprep.com/stable/all-exchange-market-hours"
        return self._make_fmp_api_request(url)

    # Commodity Endpoints
    def get_commodities_list(self):
        """
        Retrieves list of all available commodities.
        """
        url = "https://financialmodelingprep.com/stable/commodities-list"
        return self._make_fmp_api_request(url)

    # Discounted Cash Flow Endpoints
    def get_discounted_cash_flow(self, ticker: str):
        """
        Retrieves discounted cash flow (DCF) valuation for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/api/v3/discounted-cash-flow/{ticker}"
        return self._make_fmp_api_request(url)

    def get_levered_discounted_cash_flow(self, ticker: str):
        """
        Retrieves levered discounted cash flow valuation for a given stock.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/levered-discounted-cash-flow?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_custom_discounted_cash_flow(self, ticker: str, years: int = 5, growth_rate: float = None, discount_rate: float = None):
        """
        Retrieves custom discounted cash flow valuation with specified parameters.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            years (int): Number of years to project. Defaults to 5.
            growth_rate (float, optional): Custom growth rate as decimal (e.g., 0.05 for 5%).
            discount_rate (float, optional): Custom discount rate as decimal (e.g., 0.10 for 10%).
        """
        url = f"https://financialmodelingprep.com/stable/custom-discounted-cash-flow?symbol={ticker}&years={years}"
        if growth_rate is not None:
            url += f"&growthRate={growth_rate}"
        if discount_rate is not None:
            url += f"&discountRate={discount_rate}"
        return self._make_fmp_api_request(url)

    def get_custom_levered_discounted_cash_flow(self, ticker: str, years: int = 5, growth_rate: float = None, discount_rate: float = None):
        """
        Retrieves custom levered discounted cash flow valuation with specified parameters.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
            years (int): Number of years to project. Defaults to 5.
            growth_rate (float, optional): Custom growth rate as decimal (e.g., 0.05 for 5%).
            discount_rate (float, optional): Custom discount rate as decimal (e.g., 0.10 for 10%).
        """
        url = f"https://financialmodelingprep.com/stable/custom-levered-discounted-cash-flow?symbol={ticker}&years={years}"
        if growth_rate is not None:
            url += f"&growthRate={growth_rate}"
        if discount_rate is not None:
            url += f"&discountRate={discount_rate}"
        return self._make_fmp_api_request(url)

    # Forex Endpoints
    def get_forex_list(self):
        """
        Retrieves list of all available forex pairs.
        """
        url = "https://financialmodelingprep.com/stable/forex-list"
        return self._make_fmp_api_request(url)

    def get_forex_historical_prices(self, pair: str, from_date: str = None, to_date: str = None):
        """
        Retrieves historical end-of-day prices for a forex pair.

        Args:
            pair (str): The forex pair symbol (e.g., 'EURUSD', 'GBPUSD', 'USDJPY').
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.

        Returns:
            dict: Contains 'symbol' and 'historical' list with date, open, high, low, close, volume.
        """
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{pair}"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    # Crypto Endpoints
    def get_cryptocurrency_list(self):
        """
        Retrieves list of all available cryptocurrencies.
        """
        url = "https://financialmodelingprep.com/stable/cryptocurrency-list"
        return self._make_fmp_api_request(url)

    # Senate & House Trading Endpoints
    def get_senate_trading_latest(self):
        """
        Retrieves the latest Senate trading disclosures.
        """
        url = "https://financialmodelingprep.com/stable/senate-latest"
        return self._make_fmp_api_request(url)

    def get_house_trading_latest(self):
        """
        Retrieves the latest House trading disclosures.
        """
        url = "https://financialmodelingprep.com/stable/house-latest"
        return self._make_fmp_api_request(url)

    def get_senate_trades(self, ticker: str):
        """
        Retrieves Senate trading disclosures for a specific stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/senate-trades?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_senate_trades_by_name(self, name: str):
        """
        Retrieves Senate trading disclosures by senator name.

        Args:
            name (str): The senator's name.
        """
        url = f"https://financialmodelingprep.com/stable/senate-trades-by-name?name={name}"
        return self._make_fmp_api_request(url)

    def get_house_trades(self, ticker: str):
        """
        Retrieves House trading disclosures for a specific stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/house-trades?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_house_trades_by_name(self, name: str):
        """
        Retrieves House trading disclosures by representative name.

        Args:
            name (str): The representative's name.
        """
        url = f"https://financialmodelingprep.com/stable/house-trades-by-name?name={name}"
        return self._make_fmp_api_request(url)

    # ESG Endpoints
    def get_esg_ratings(self, ticker: str):
        """
        Retrieves ESG ratings for a given stock ticker.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'AAPL').
        """
        url = f"https://financialmodelingprep.com/stable/esg-ratings?symbol={ticker}"
        return self._make_fmp_api_request(url)

    def get_esg_benchmark(self, year: int):
        """
        Retrieves ESG benchmark data for a given year.

        Args:
            year (int): The year (e.g., 2024).
        """
        url = f"https://financialmodelingprep.com/stable/esg-benchmark?year={year}"
        return self._make_fmp_api_request(url)

    # Commitment Of Traders Endpoints
    def get_commitment_of_traders_report(self, from_date: str = None, to_date: str = None):
        """
        Retrieves Commitment of Traders (COT) report data.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/stable/commitment-of-traders-report"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_commitment_of_traders_analysis(self, from_date: str = None, to_date: str = None):
        """
        Retrieves Commitment of Traders analysis data.

        Args:
            from_date (str, optional): Start date in YYYY-MM-DD format.
            to_date (str, optional): End date in YYYY-MM-DD format.
        """
        url = "https://financialmodelingprep.com/stable/commitment-of-traders-analysis"
        if from_date:
            url += f"?from={from_date}"
            if to_date:
                url += f"&to={to_date}"
        elif to_date:
            url += f"?to={to_date}"
        return self._make_fmp_api_request(url)

    def get_commitment_of_traders_list(self):
        """
        Retrieves list of available Commitment of Traders reports.
        """
        url = "https://financialmodelingprep.com/stable/commitment-of-traders-list"
        return self._make_fmp_api_request(url)

    # Fundraisers & Crowdfunding Endpoints
    def get_crowdfunding_offerings_latest(self, page: int = 0, limit: int = 100):
        """
        Retrieves the latest crowdfunding offerings.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/crowdfunding-offerings-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_crowdfunding_offerings_search(self, name: str):
        """
        Searches crowdfunding offerings by company name.

        Args:
            name (str): The company name to search for.
        """
        url = f"https://financialmodelingprep.com/stable/crowdfunding-offerings-search?name={name}"
        return self._make_fmp_api_request(url)

    def get_crowdfunding_offerings(self, cik: str):
        """
        Retrieves crowdfunding offerings for a specific CIK.

        Args:
            cik (str): The CIK number.
        """
        url = f"https://financialmodelingprep.com/stable/crowdfunding-offerings?cik={cik}"
        return self._make_fmp_api_request(url)

    def get_fundraising_latest(self, page: int = 0, limit: int = 100):
        """
        Retrieves the latest fundraising data.

        Args:
            page (int): Page number for pagination. Defaults to 0.
            limit (int): Number of records per page. Defaults to 100.
        """
        url = f"https://financialmodelingprep.com/stable/fundraising-latest?page={page}&limit={limit}"
        return self._make_fmp_api_request(url)

    def get_fundraising_search(self, name: str):
        """
        Searches fundraising data by company name.

        Args:
            name (str): The company name to search for.
        """
        url = f"https://financialmodelingprep.com/stable/fundraising-search?name={name}"
        return self._make_fmp_api_request(url)

    def get_fundraising(self, cik: str):
        """
        Retrieves fundraising data for a specific CIK.

        Args:
            cik (str): The CIK number.
        """
        url = f"https://financialmodelingprep.com/stable/fundraising?cik={cik}"
        return self._make_fmp_api_request(url)

    # Bulk Endpoints
    def get_profile_bulk(self, page: int = 0):
        """
        Retrieves company profiles in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/profile-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_rating_bulk(self, page: int = 0):
        """
        Retrieves analyst ratings in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/rating-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_dcf_bulk(self, page: int = 0):
        """
        Retrieves discounted cash flow valuations in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/dcf-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_scores_bulk(self, page: int = 0):
        """
        Retrieves financial scores in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/scores-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_price_target_summary_bulk(self, page: int = 0):
        """
        Retrieves price target summaries in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/price-target-summary-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_etf_holder_bulk(self, page: int = 0):
        """
        Retrieves ETF holder data in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/etf-holder-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_upgrades_downgrades_consensus_bulk(self, page: int = 0):
        """
        Retrieves analyst upgrades/downgrades consensus in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/upgrades-downgrades-consensus-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_key_metrics_ttm_bulk(self, page: int = 0):
        """
        Retrieves TTM key metrics in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/key-metrics-ttm-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_ratios_ttm_bulk(self, page: int = 0):
        """
        Retrieves TTM financial ratios in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/ratios-ttm-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_peers_bulk(self, page: int = 0):
        """
        Retrieves stock peers data in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/peers-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_earnings_surprises_bulk(self, page: int = 0):
        """
        Retrieves earnings surprises in bulk.

        Args:
            page (int): Page number for pagination. Defaults to 0.
        """
        url = f"https://financialmodelingprep.com/stable/earnings-surprises-bulk?page={page}"
        return self._make_fmp_api_request(url)

    def get_income_statement_bulk(self, year: int, period: str = 'quarter'):
        """
        Retrieves income statements in bulk for a specific year and period.

        Args:
            year (int): The year (e.g., 2024).
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v4/income-statement-bulk?year={year}&period={period}"
        return self._make_fmp_api_request(url)

    def get_income_statement_growth_bulk(self, year: int, period: str = 'quarter'):
        """
        Retrieves income statement growth in bulk for a specific year and period.

        Args:
            year (int): The year (e.g., 2024).
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v4/income-statement-growth-bulk?year={year}&period={period}"
        return self._make_fmp_api_request(url)

    def get_balance_sheet_statement_bulk(self, year: int, period: str = 'quarter'):
        """
        Retrieves balance sheets in bulk for a specific year and period.

        Args:
            year (int): The year (e.g., 2024).
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v4/balance-sheet-statement-bulk?year={year}&period={period}"
        return self._make_fmp_api_request(url)

    def get_balance_sheet_statement_growth_bulk(self, year: int, period: str = 'quarter'):
        """
        Retrieves balance sheet growth in bulk for a specific year and period.

        Args:
            year (int): The year (e.g., 2024).
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v4/balance-sheet-statement-growth-bulk?year={year}&period={period}"
        return self._make_fmp_api_request(url)

    def get_cash_flow_statement_bulk(self, year: int, period: str = 'quarter'):
        """
        Retrieves cash flow statements in bulk for a specific year and period.

        Args:
            year (int): The year (e.g., 2024).
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v4/cash-flow-statement-bulk?year={year}&period={period}"
        return self._make_fmp_api_request(url)

    def get_cash_flow_statement_growth_bulk(self, year: int, period: str = 'quarter'):
        """
        Retrieves cash flow statement growth in bulk for a specific year and period.

        Args:
            year (int): The year (e.g., 2024).
            period (str): The reporting period, 'annual' or 'quarter'. Defaults to 'quarter'.
        """
        url = f"https://financialmodelingprep.com/api/v4/cash-flow-statement-growth-bulk?year={year}&period={period}"
        return self._make_fmp_api_request(url)

    def get_eod_bulk(self, date: str):
        """
        Retrieves end-of-day prices in bulk for a specific date.

        Args:
            date (str): The date in YYYY-MM-DD format.
        """
        url = f"https://financialmodelingprep.com/stable/eod-bulk?date={date}"
        return self._make_fmp_api_request(url)


