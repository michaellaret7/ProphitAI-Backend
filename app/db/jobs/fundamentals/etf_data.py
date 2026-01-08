"""
ETF Data Updater

Updates ETF-specific and dividend data for tickers:
- ETF holdings
- ETF info
- Dividends

Part of the fundamentals update job, split for maintainability.
"""
from sqlalchemy.dialects.postgresql import insert

from app.db.core.models.market_data_models import (
    Ticker,
    ETFHolding,
    ETFInfo,
    Dividend,
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.db.jobs.base_updater import BaseUpdater


class ETFDataUpdater:
    """
    Updates ETF-specific and dividend data for a single ticker.

    Handles ETF holdings, ETF info, and dividends.
    Designed to be called per-ticker within a parallel processing context.
    """

    def __init__(self):
        self._safe_decimal = BaseUpdater.safe_decimal
        self._safe_date = BaseUpdater.safe_date
        self._safe_datetime = BaseUpdater.safe_datetime

    def update_etf_holdings(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update ETF holdings data (only for ETF tickers).

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error, 0 if not an ETF
        """
        try:
            # First check if this is an ETF
            ticker = session.query(Ticker).filter(Ticker.id == ticker_id).first()
            if not ticker or not ticker.is_etf:
                return 0

            data = fmp_api.get_etf_holdings(ticker_symbol)
            if not data:
                return 0

            # Delete existing holdings for this ETF
            session.query(ETFHolding).filter(ETFHolding.ticker_id == ticker_id).delete()
            session.flush()

            # Use a dictionary to deduplicate holdings by asset symbol
            unique_holdings = {}
            for item in data[:500]:  # Limit to top 500 holdings
                asset = item.get('asset', '').strip()

                if not asset:
                    continue

                # Keep the one with higher weight
                if asset in unique_holdings:
                    existing_weight = unique_holdings[asset].get('weightPercentage', 0) or 0
                    new_weight = item.get('weightPercentage', 0) or 0
                    if new_weight <= existing_weight:
                        continue

                unique_holdings[asset] = {
                    'ticker_id': ticker_id,
                    'asset': asset,
                    'name': item.get('name'),
                    'isin': item.get('isin'),
                    'securityCusip': item.get('cusip'),
                    'sharesNumber': self._safe_decimal(item.get('sharesNumber')),
                    'weightPercentage': item.get('weightPercentage'),
                    'marketValue': self._safe_decimal(item.get('marketValue')),
                    'updatedAt': self._safe_datetime(item.get('updated'))
                }

            if unique_holdings:
                records = list(unique_holdings.values())
                stmt = insert(ETFHolding).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'asset'],
                    set_={
                        'weightPercentage': stmt.excluded.weightPercentage,
                        'sharesNumber': stmt.excluded.sharesNumber,
                        'marketValue': stmt.excluded.marketValue,
                        'updatedAt': stmt.excluded.updatedAt
                    }
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating ETF holdings for {ticker_symbol}: {str(e)}")
            return -1

    def update_etf_info(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update ETF info data (only for ETF tickers).

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error, 0 if not an ETF
        """
        try:
            # First check if this is an ETF
            ticker = session.query(Ticker).filter(Ticker.id == ticker_id).first()
            if not ticker or not ticker.is_etf:
                return 0

            data = fmp_api.get_etf_info(ticker_symbol)
            if not data or not isinstance(data, list) or len(data) == 0:
                return 0

            info = data[0]

            record = {
                'ticker_id': ticker_id,
                'name': info.get('name'),
                'description': info.get('description'),
                'isin': info.get('isin'),
                'assetClass': info.get('assetClass'),
                'securityCusip': info.get('cusip'),
                'domicile': info.get('domicile'),
                'website': info.get('website'),
                'etfCompany': info.get('etfCompany'),
                'expenseRatio': info.get('expenseRatio'),
                'assetsUnderManagement': self._safe_decimal(info.get('aum')),
                'avgVolume': info.get('avgVolume'),
                'inceptionDate': self._safe_date(info.get('inceptionDate')),
                'nav': info.get('nav'),
                'navCurrency': info.get('navCurrency'),
                'holdingsCount': info.get('holdingsCount'),
                'updatedAt': self._safe_datetime(info.get('updated')),
                'sectorsList': info.get('sectorsList')
            }

            stmt = insert(ETFInfo).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id'],
                set_=dict(stmt.excluded)
            )
            session.execute(stmt)
            return 1

        except Exception as e:
            print(f"Error updating ETF info for {ticker_symbol}: {str(e)}")
            return -1

    def update_dividends(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update dividend data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_dividends(ticker_symbol)
            if not data:
                return 0

            records = []
            for item in data[:100]:  # Last 100 dividend records
                record = {
                    'ticker_id': ticker_id,
                    'date': self._safe_date(item.get('date')),
                    'recordDate': self._safe_date(item.get('recordDate')),
                    'paymentDate': self._safe_date(item.get('paymentDate')),
                    'declarationDate': self._safe_date(item.get('declarationDate')),
                    'adjDividend': item.get('adjDividend'),
                    'dividend': item.get('dividend'),
                    'yield_': item.get('yield'),
                    'frequency': item.get('frequency')
                }
                if record['date']:
                    records.append(record)

            if records:
                stmt = insert(Dividend).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating dividends for {ticker_symbol}: {str(e)}")
            return -1

    def update_all(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> dict:
        """
        Update all ETF and dividend data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Dictionary with counts for each data type
        """
        return {
            'etf_holdings': self.update_etf_holdings(ticker_id, ticker_symbol, session, fmp_api),
            'etf_info': self.update_etf_info(ticker_id, ticker_symbol, session, fmp_api),
            'dividends': self.update_dividends(ticker_id, ticker_symbol, session, fmp_api),
        }
