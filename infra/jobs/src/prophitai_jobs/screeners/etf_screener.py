"""
ETF Screener Updater

Updates the ETF screener table with current calculated metrics including
performance, risk, and ETF-specific data like expense ratios and NAV.
"""
import threading
import time
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import (
    Ticker,
    ETFInfo,
    ETFScreener,
)
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers
from prophitai_calculations.performance.returns import calc_annualized_return, calc_alpha
from prophitai_calculations.risk.distribution import calc_volatility
from prophitai_calculations.risk.benchmark import calc_beta
from prophitai_shared.time_utils import get_current_utc_time, get_utc_days_ago
from prophitai_jobs.screeners.base import safe_round, safe_divide


class UpdateETFScreenerTable:
    """Updates the ETF screener table with current metrics."""

    def __init__(self):
        self.lock = threading.Lock()
        self.total_updated = 0
        self.total_errors = 0

    def _get_etf_tickers(self) -> List[Tuple[str, str]]:
        """Query all actively trading ETF tickers."""
        with MarketSession() as session:
            tickers = session.query(Ticker.id, Ticker.ticker).filter(
                Ticker.is_etf == True,
                Ticker.is_actively_trading == True
            ).all()
        return [(str(t.id), t.ticker) for t in tickers]

    def _get_etf_metadata(self, ticker_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch ETF metadata from Ticker and ETFInfo tables."""
        metadata = {}
        with MarketSession() as session:
            results = (
                session.query(Ticker, ETFInfo)
                .outerjoin(ETFInfo, Ticker.id == ETFInfo.ticker_id)
                .filter(Ticker.id.in_([UUID(tid) for tid in ticker_ids]))
                .all()
            )
            for ticker, etf_info in results:
                ticker_id_str = str(ticker.id)
                metadata[ticker_id_str] = {
                    'ticker': ticker.ticker,
                    'industry': ticker.industry,
                    'sub_industry': ticker.sub_industry,
                    'market_cap': float(ticker.market_cap) if ticker.market_cap else None,
                    'dollar_volume': float(ticker.dollar_volume) if ticker.dollar_volume else None,
                    'expense_ratio': etf_info.expenseRatio if etf_info else None,
                    'nav': etf_info.nav if etf_info else None,
                }
        return metadata

    def _upsert_records(self, records: List[Dict[str, Any]]) -> int:
        """Bulk upsert records to ETFScreener table."""
        if not records:
            return 0

        with MarketSession() as session:
            stmt = insert(ETFScreener).values(records)
            update_columns = {
                col: stmt.excluded[col]
                for col in records[0].keys()
                if col != 'ticker_id'
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id'],
                set_=update_columns
            )
            session.execute(stmt)
            session.commit()
        return len(records)

    def run_update(self, lookback_days: int = 365) -> None:
        """
        Run the ETF screener update.

        Args:
            lookback_days: Number of days to look back for price data
        """
        print(f"\n{'='*70}")
        print("ETF SCREENER UPDATE")
        print(f"{'='*70}")

        start_time = time.time()

        # Get ETF tickers
        etf_tickers = self._get_etf_tickers()
        total_etfs = len(etf_tickers)
        print(f"Found {total_etfs} actively trading ETFs")

        if not etf_tickers:
            print("No ETFs to update")
            return

        # Get date range
        end_date = get_current_utc_time().strftime('%Y-%m-%d')
        start_date = get_utc_days_ago(lookback_days).strftime('%Y-%m-%d')

        # Build ticker list and mapping
        ticker_to_id = {ticker: tid for tid, ticker in etf_tickers}
        tickers = list(ticker_to_id.keys())
        ticker_ids = list(ticker_to_id.values())

        # Add SPY for beta/alpha calculation
        all_tickers = tickers + ['SPY'] if 'SPY' not in tickers else tickers

        print(f"Fetching price data from {start_date} to {end_date}...")
        price_data = fetch_bulk_ohlcv_data_for_tickers(
            all_tickers, start_date, end_date,
            frequency='daily'
        )
        print(f"Fetched data for {len(price_data)} tickers")

        # Get SPY returns
        spy_returns = None
        if 'SPY' in price_data:
            spy_df = price_data['SPY']
            if 'adj_close' in spy_df.columns:
                spy_returns = spy_df['adj_close'].pct_change(fill_method=None).dropna()

        # Get metadata
        metadata = self._get_etf_metadata(ticker_ids)

        # Fetch dividend yields from FMP
        print("Fetching dividend yields from FMP API...")
        fmp_api = FMP_API_DATA()
        dividend_yields = {}
        for ticker in tickers:
            try:
                ratios = fmp_api.get_ratios_ttm(ticker)
                if ratios and len(ratios) > 0:
                    dividend_yields[ticker] = ratios[0].get('dividendYielTTM')
            except Exception:
                pass

        # Calculate metrics
        print("Calculating metrics...")
        records = []
        for ticker_id, ticker in etf_tickers:
            if ticker not in price_data:
                with self.lock:
                    self.total_errors += 1
                continue

            df = price_data[ticker]
            if 'adj_close' not in df.columns or df['adj_close'].dropna().empty:
                with self.lock:
                    self.total_errors += 1
                continue

            returns = df['adj_close'].pct_change(fill_method=None).dropna()

            # Calculate metrics
            ann_ret = calc_annualized_return(returns)
            ann_vol = calc_volatility(returns, annualize=True)
            info_ratio = safe_divide(ann_ret, ann_vol)

            beta = None
            alpha = None
            if spy_returns is not None and len(returns) > 10:
                beta = calc_beta(returns, spy_returns)
                alpha = calc_alpha(returns, spy_returns)

            meta = metadata.get(ticker_id, {})

            record = {
                'ticker_id': UUID(ticker_id),
                'updated_at': get_current_utc_time(),
                'industry': meta.get('industry'),
                'sub_industry': meta.get('sub_industry'),
                'expense_ratio': meta.get('expense_ratio'),
                'nav': meta.get('nav'),
                'ann_vol': safe_round(ann_vol),
                'ann_ret': safe_round(ann_ret),
                'information_ratio': safe_round(info_ratio),
                'beta': safe_round(beta),
                'alpha': safe_round(alpha),
                'dividend_yield_ttm': dividend_yields.get(ticker),
                'market_cap': Decimal(str(meta['market_cap'])) if meta.get('market_cap') else None,
                'dollar_volume': Decimal(str(meta['dollar_volume'])) if meta.get('dollar_volume') else None,
            }
            records.append(record)

            with self.lock:
                self.total_updated += 1
                if self.total_updated % 100 == 0:
                    print(f"Progress: {self.total_updated}/{total_etfs}")

        # Upsert to database
        upserted = self._upsert_records(records)

        # Summary
        duration = time.time() - start_time
        print(f"\n{'='*70}")
        print("ETF SCREENER UPDATE SUMMARY")
        print(f"{'='*70}")
        print(f"Total ETFs processed: {total_etfs}")
        print(f"Successfully updated: {self.total_updated}")
        print(f"Errors: {self.total_errors}")
        print(f"Records upserted: {upserted}")
        print(f"Time taken: {duration:.2f} seconds")
        print(f"{'='*70}\n")


def run():
    """Entry point for ETF screener update."""
    UpdateETFScreenerTable().run_update()
