"""
Analyst Data Updater

Updates analyst-related data for tickers:
- Analyst estimates
- Stock grades (individual and summary)
- Rating scores
- Analyst recommendations
- Price target summaries

Part of the fundamentals update job, split for maintainability.
"""
import json

from sqlalchemy.dialects.postgresql import insert

from prophitai_data.db.models.market import (
    AnalystEstimate,
    StockGradesIndividual,
    StockGradesSummary,
    Rating,
    AnalystRecommendation,
    PriceTargetSummary,
)
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_data.jobs.base import BaseUpdater


class AnalystDataUpdater:
    """
    Updates analyst-related data for a single ticker.

    Handles analyst estimates, stock grades, ratings, recommendations,
    and price target summaries.
    Designed to be called per-ticker within a parallel processing context.
    """

    def __init__(self):
        self._safe_decimal = BaseUpdater.safe_decimal
        self._safe_date = BaseUpdater.safe_date

    def update_analyst_estimates(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update analyst estimates data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_analyst_estimates(ticker_symbol, period='quarter')
            if not data:
                return 0

            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'revenueLow': self._safe_decimal(item.get('revenueLow')),
                        'revenueHigh': self._safe_decimal(item.get('revenueHigh')),
                        'revenueAvg': self._safe_decimal(item.get('revenueAvg')),
                        'ebitdaLow': self._safe_decimal(item.get('ebitdaLow')),
                        'ebitdaHigh': self._safe_decimal(item.get('ebitdaHigh')),
                        'ebitdaAvg': self._safe_decimal(item.get('ebitdaAvg')),
                        'ebitLow': self._safe_decimal(item.get('ebitLow')),
                        'ebitHigh': self._safe_decimal(item.get('ebitHigh')),
                        'ebitAvg': self._safe_decimal(item.get('ebitAvg')),
                        'netIncomeLow': self._safe_decimal(item.get('netIncomeLow')),
                        'netIncomeHigh': self._safe_decimal(item.get('netIncomeHigh')),
                        'netIncomeAvg': self._safe_decimal(item.get('netIncomeAvg')),
                        'sgaExpenseLow': self._safe_decimal(item.get('sgaExpenseLow')),
                        'sgaExpenseHigh': self._safe_decimal(item.get('sgaExpenseHigh')),
                        'sgaExpenseAvg': self._safe_decimal(item.get('sgaExpenseAvg')),
                        'epsAvg': item.get('epsAvg'),
                        'epsHigh': item.get('epsHigh'),
                        'epsLow': item.get('epsLow'),
                        'numAnalystsRevenue': item.get('numberAnalystEstimatedRevenue'),
                        'numAnalystsEps': item.get('numberAnalystEstimatedEps')
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(AnalystEstimate).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating analyst estimates for {ticker_symbol}: {str(e)}")
            return -1

    def update_stock_grades(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update stock grades (individual and summary) for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Total number of records inserted/updated, -1 on error
        """
        try:
            # Update individual grades
            individual_data = fmp_api.get_stock_grades_individual(ticker_symbol, limit=100)
            individual_count = 0

            if individual_data:
                # Use a dictionary to deduplicate records by (date, normalized grading company)
                unique_records = {}
                for item in individual_data[:100]:
                    date = self._safe_date(item.get('date'))
                    # Normalize grading company name to avoid duplicates
                    grading_company = item.get('gradingCompany', '').strip().lower()

                    if date and grading_company:
                        key = (date, grading_company)

                        if key not in unique_records:
                            unique_records[key] = {
                                'ticker_id': ticker_id,
                                'date': date,
                                'gradingCompany': item.get('gradingCompany', ''),
                                'previousGrade': item.get('previousGrade'),
                                'newGrade': item.get('newGrade'),
                                'action': item.get('action')
                            }

                if unique_records:
                    records = list(unique_records.values())
                    stmt = insert(StockGradesIndividual).values(records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker_id', 'date', 'gradingCompany'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    individual_count = len(records)

            # Update summary grades
            summary_data = fmp_api.get_stock_grades_summary(ticker_symbol, limit=20)
            summary_count = 0

            if summary_data:
                records = []
                for item in summary_data[:20]:
                    record = {
                        'ticker_id': ticker_id,
                        'date': self._safe_date(item.get('date')),
                        'analystRatingsStrongBuy': item.get('strongBuy'),
                        'analystRatingsBuy': item.get('buy'),
                        'analystRatingsHold': item.get('hold'),
                        'analystRatingsSell': item.get('sell'),
                        'analystRatingsStrongSell': item.get('strongSell')
                    }
                    if record['date']:
                        records.append(record)

                if records:
                    stmt = insert(StockGradesSummary).values(records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker_id', 'date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    summary_count = len(records)

            return individual_count + summary_count

        except Exception as e:
            print(f"Error updating stock grades for {ticker_symbol}: {str(e)}")
            return -1

    def update_rating_scores(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update rating scores for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_rating_scores(ticker_symbol, limit=20)
            if not data:
                return 0

            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'rating': item.get('symbol'),
                        'overallScore': item.get('score'),
                        'discountedCashFlowScore': item.get('discountedCashFlowScore'),
                        'returnOnEquityScore': item.get('returnOnEquityScore'),
                        'returnOnAssetsScore': item.get('returnOnAssetsScore'),
                        'debtToEquityScore': item.get('debtToEquityScore'),
                        'priceToEarningsScore': item.get('priceToEarningsScore'),
                        'priceToBookScore': item.get('priceToBookScore')
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(Rating).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating rating scores for {ticker_symbol}: {str(e)}")
            return -1

    def update_analyst_recommendations(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update analyst recommendations for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_analyst_recommendations(ticker_symbol)
            if not data:
                return 0

            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'rating': item.get('rating'),
                        'ratingScore': item.get('ratingScore'),
                        'ratingRecommendation': item.get('ratingRecommendation'),
                        'ratingDetailsDCFScore': item.get('ratingDetailsDCFScore'),
                        'ratingDetailsDCFRecommendation': item.get('ratingDetailsDCFRecommendation'),
                        'ratingDetailsROEScore': item.get('ratingDetailsROEScore'),
                        'ratingDetailsROERecommendation': item.get('ratingDetailsROERecommendation'),
                        'ratingDetailsROAScore': item.get('ratingDetailsROAScore'),
                        'ratingDetailsROARecommendation': item.get('ratingDetailsROARecommendation'),
                        'ratingDetailsDEScore': item.get('ratingDetailsDEScore'),
                        'ratingDetailsDERecommendation': item.get('ratingDetailsDERecommendation'),
                        'ratingDetailsPEScore': item.get('ratingDetailsPEScore'),
                        'ratingDetailsPERecommendation': item.get('ratingDetailsPERecommendation'),
                        'ratingDetailsPBScore': item.get('ratingDetailsPBScore'),
                        'ratingDetailsPBRecommendation': item.get('ratingDetailsPBRecommendation')
                    }

            records = list(unique_records.values())

            if records:
                stmt = insert(AnalystRecommendation).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating analyst recommendations for {ticker_symbol}: {str(e)}")
            return -1

    def update_price_target_summary(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update price target summary for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_price_target_summary(ticker_symbol)
            if not data or not isinstance(data, list) or len(data) == 0:
                return 0

            summary = data[0]

            record = {
                'ticker_id': ticker_id,
                'lastMonthCount': summary.get('lastMonth'),
                'lastMonthAvgPriceTarget': summary.get('lastMonthAvgPriceTarget'),
                'lastQuarterCount': summary.get('lastQuarter'),
                'lastQuarterAvgPriceTarget': summary.get('lastQuarterAvgPriceTarget'),
                'lastYearCount': summary.get('lastYear'),
                'lastYearAvgPriceTarget': summary.get('lastYearAvgPriceTarget'),
                'allTimeCount': summary.get('allTime'),
                'allTimeAvgPriceTarget': summary.get('allTimeAvgPriceTarget'),
                'publishers': json.dumps(summary.get('publishers', []))
            }

            stmt = insert(PriceTargetSummary).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id'],
                set_=dict(stmt.excluded)
            )
            session.execute(stmt)
            return 1

        except Exception as e:
            print(f"Error updating price target summary for {ticker_symbol}: {str(e)}")
            return -1

    def update_all(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> dict:
        """
        Update all analyst data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Dictionary with counts for each data type
        """
        return {
            'analyst_estimates': self.update_analyst_estimates(ticker_id, ticker_symbol, session, fmp_api),
            'stock_grades': self.update_stock_grades(ticker_id, ticker_symbol, session, fmp_api),
            'rating_scores': self.update_rating_scores(ticker_id, ticker_symbol, session, fmp_api),
            'analyst_recommendations': self.update_analyst_recommendations(ticker_id, ticker_symbol, session, fmp_api),
            'price_targets': self.update_price_target_summary(ticker_id, ticker_symbol, session, fmp_api),
        }
