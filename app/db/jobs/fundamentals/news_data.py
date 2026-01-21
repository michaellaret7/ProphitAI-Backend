"""
News Data Updater

Updates news and transcript data for tickers:
- Press releases
- Stock news
- Price target news
- Stock grade news
- Earnings transcripts

Part of the fundamentals update job, split for maintainability.
"""
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert

from app.db.core.models.market_data_models import (
    PressRelease,
    StockNews,
    PriceTargetNews,
    StockGradeNews,
    EarningsTranscript,
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.db.jobs.base_updater import BaseUpdater


class NewsDataUpdater:
    """
    Updates news and transcript data for a single ticker.

    Handles press releases, stock news, price target news, stock grade news,
    and earnings transcripts.
    Designed to be called per-ticker within a parallel processing context.
    """

    def __init__(self):
        self._safe_datetime = BaseUpdater.safe_datetime
        self._safe_date = BaseUpdater.safe_date

    def update_press_releases(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update press releases for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted, -1 on error
        """
        try:
            data = fmp_api.get_press_releases(ticker_symbol, limit=100)
            if not data:
                return 0

            # Use a dictionary to deduplicate by URL
            unique_records = {}
            for item in data[:100]:
                url = item.get('url', '')[:512]
                if url and url not in unique_records:
                    unique_records[url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'publisher': item.get('publisher'),
                        'title': item.get('title'),
                        'image': item.get('image'),
                        'site': item.get('site'),
                        'text': item.get('text'),
                        'url': url
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(PressRelease).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'url']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0

        except Exception as e:
            print(f"Error updating press releases for {ticker_symbol}: {str(e)}")
            return -1

    def update_stock_news(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update stock news for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted, -1 on error
        """
        try:
            data = fmp_api.get_stock_news(ticker_symbol, limit=100)
            if not data:
                return 0

            unique_records = {}
            for item in data[:100]:
                url = item.get('url', '')[:512]
                if url and url not in unique_records:
                    unique_records[url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'publisher': item.get('publisher'),
                        'title': item.get('title'),
                        'image': item.get('image'),
                        'site': item.get('site'),
                        'text': item.get('text'),
                        'url': url
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(StockNews).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'url']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0

        except Exception as e:
            print(f"Error updating stock news for {ticker_symbol}: {str(e)}")
            return -1

    def update_price_target_news(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update price target news for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted, -1 on error
        """
        try:
            data = fmp_api.get_price_target_news(ticker_symbol, limit=100)
            if not data:
                return 0

            unique_records = {}
            for item in data[:100]:
                news_url = item.get('newsURL', '')[:512]
                if news_url and news_url not in unique_records:
                    unique_records[news_url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'newsURL': news_url,
                        'newsTitle': item.get('newsTitle'),
                        'analystName': item.get('analystName'),
                        'priceTarget': item.get('priceTarget'),
                        'adjPriceTarget': item.get('adjPriceTarget'),
                        'priceWhenPosted': item.get('priceWhenPosted'),
                        'newsPublisher': item.get('newsPublisher'),
                        'newsBaseURL': item.get('newsBaseURL'),
                        'analystCompany': item.get('analystCompany')
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(PriceTargetNews).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'newsURL']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0

        except Exception as e:
            print(f"Error updating price target news for {ticker_symbol}: {str(e)}")
            return -1

    def update_stock_grade_news(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update stock grade news for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted, -1 on error
        """
        try:
            data = fmp_api.get_stock_grade_news(ticker_symbol, limit=100)
            if not data:
                return 0

            unique_records = {}
            for item in data[:100]:
                news_url = item.get('newsURL', '')[:512]
                if news_url and news_url not in unique_records:
                    unique_records[news_url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'newsURL': news_url,
                        'newsTitle': item.get('newsTitle'),
                        'newsBaseURL': item.get('newsBaseURL'),
                        'newsPublisher': item.get('newsPublisher'),
                        'newGrade': item.get('newGrade'),
                        'previousGrade': item.get('previousGrade'),
                        'gradingCompany': item.get('gradingCompany'),
                        'action': item.get('action'),
                        'priceWhenPosted': item.get('priceWhenPosted')
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(StockGradeNews).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'newsURL']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0

        except Exception as e:
            print(f"Error updating stock grade news for {ticker_symbol}: {str(e)}")
            return -1

    def update_earnings_transcripts(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update earnings transcripts using FMP's transcript dates endpoint.

        Fetches available transcript dates from the API, then retrieves
        transcripts that don't already exist in the database.
        Limited to the most recent 8 transcripts (2 years).

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of transcripts added, -1 on error
        """
        try:
            # Get available transcript dates from FMP API
            available_dates = fmp_api.get_earnings_transcript_dates(ticker_symbol)
            if not available_dates:
                return 0

            transcripts_added = 0

            # Process the most recent 8 transcripts
            for item in available_dates[:8]:
                year = item.get('year')
                quarter = item.get('quarter')

                if not year or not quarter:
                    continue

                period_str = f'Q{quarter}'

                # Check if transcript already exists
                existing = session.query(EarningsTranscript).filter(
                    and_(
                        EarningsTranscript.ticker_id == ticker_id,
                        EarningsTranscript.year == year,
                        EarningsTranscript.period == period_str
                    )
                ).first()

                if not existing:
                    # Fetch transcript from API
                    data = fmp_api.get_earnings_transcript(ticker_symbol, year, quarter)

                    # Handle both list and dict responses from API
                    transcript_data = None
                    if data:
                        if isinstance(data, list) and len(data) > 0:
                            transcript_data = data[0]
                        elif isinstance(data, dict):
                            transcript_data = data

                    # Check if we have valid transcript data with content
                    if transcript_data and transcript_data.get('content'):
                        record = {
                            'ticker_id': ticker_id,
                            'period': period_str,
                            'year': year,
                            'date': self._safe_date(transcript_data.get('date')),
                            'content': transcript_data.get('content')
                        }

                        stmt = insert(EarningsTranscript).values(record)
                        session.execute(stmt)
                        transcripts_added += 1

            return transcripts_added

        except Exception as e:
            print(f"Error updating earnings transcripts for {ticker_symbol}: {str(e)}")
            return -1

    def update_all(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> dict:
        """
        Update all news data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Dictionary with counts for each data type
        """
        return {
            'press_releases': self.update_press_releases(ticker_id, ticker_symbol, session, fmp_api),
            'stock_news': self.update_stock_news(ticker_id, ticker_symbol, session, fmp_api),
            'price_target_news': self.update_price_target_news(ticker_id, ticker_symbol, session, fmp_api),
            'stock_grade_news': self.update_stock_grade_news(ticker_id, ticker_symbol, session, fmp_api),
            'earnings_transcripts': self.update_earnings_transcripts(ticker_id, ticker_symbol, session, fmp_api),
        }
