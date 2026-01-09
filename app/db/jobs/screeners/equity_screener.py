"""
Equity Screener Updater

Updates the Equity screener table with current calculated metrics including
momentum, performance, risk, growth, and fundamental ratios.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import (
    Ticker,
    EquityScreener,
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.factors.momentum import MomentumFactors
from app.utils.ticker_utils import get_sector_etf
from app.utils.time_utils import get_current_utc_time, get_utc_days_ago
from app.db.jobs.screeners.base import safe_round, safe_divide, RATIO_KEY_MAP


class UpdateEquityScreenerTable:
    """Updates the Equity screener table with current metrics."""

    def __init__(self):
        self.lock = threading.Lock()
        self.total_updated = 0
        self.total_errors = 0

    def _get_equity_tickers(self) -> List[Tuple[str, str, Optional[str]]]:
        """Query all actively trading equity tickers."""
        with MarketSession() as session:
            tickers = session.query(Ticker.id, Ticker.ticker, Ticker.sector).filter(
                Ticker.is_etf == False,
                Ticker.is_actively_trading == True
            ).all()
        return [(str(t.id), t.ticker, t.sector) for t in tickers]

    def _calculate_cagr(
        self,
        end_value: Optional[float],
        start_value: Optional[float],
        years: int
    ) -> Optional[float]:
        """Calculate Compound Annual Growth Rate."""
        if end_value is None or start_value is None or years <= 0:
            return None
        if start_value <= 0 or end_value <= 0:
            return None
        try:
            cagr = (end_value / start_value) ** (1 / years) - 1
            return safe_round(cagr)
        except Exception:
            return None

    def _calculate_pct_change(
        self,
        current: Optional[float],
        previous: Optional[float]
    ) -> Optional[float]:
        """Calculate percentage change."""
        if current is None or previous is None or previous == 0:
            return None
        try:
            return safe_round((current - previous) / abs(previous))
        except Exception:
            return None

    def _calculate_growth_metrics(
        self,
        ticker: str,
        fmp_api: FMP_API_DATA
    ) -> Dict[str, Optional[float]]:
        """Calculate growth metrics from FMP financial statements."""
        growth = {
            'ebit_cagr_5yr': None,
            'ebit_cagr_3yr': None,
            'revenue_cagr_3yr': None,
            'ebit_growth_yoy': None,
            'eps_growth_yoy': None,
            'fcf_growth_yoy': None,
            'operating_margin_change_yoy': None,
            'roce_change_5yr': None,
        }

        try:
            # Get income statements
            income_stmts = fmp_api.get_income_statements(ticker, period='annual')
            if income_stmts and len(income_stmts) >= 2:
                # EBIT CAGR
                if len(income_stmts) >= 5:
                    growth['ebit_cagr_5yr'] = self._calculate_cagr(
                        income_stmts[0].get('operatingIncome'),
                        income_stmts[4].get('operatingIncome'),
                        5
                    )
                if len(income_stmts) >= 3:
                    growth['ebit_cagr_3yr'] = self._calculate_cagr(
                        income_stmts[0].get('operatingIncome'),
                        income_stmts[2].get('operatingIncome'),
                        3
                    )
                    growth['revenue_cagr_3yr'] = self._calculate_cagr(
                        income_stmts[0].get('revenue'),
                        income_stmts[2].get('revenue'),
                        3
                    )

                # YoY growth
                growth['ebit_growth_yoy'] = self._calculate_pct_change(
                    income_stmts[0].get('operatingIncome'),
                    income_stmts[1].get('operatingIncome')
                )
                growth['eps_growth_yoy'] = self._calculate_pct_change(
                    income_stmts[0].get('eps'),
                    income_stmts[1].get('eps')
                )

                # Operating margin change YoY
                curr_margin = safe_divide(
                    income_stmts[0].get('operatingIncome'),
                    income_stmts[0].get('revenue')
                )
                prev_margin = safe_divide(
                    income_stmts[1].get('operatingIncome'),
                    income_stmts[1].get('revenue')
                )
                if curr_margin is not None and prev_margin is not None:
                    growth['operating_margin_change_yoy'] = safe_round(curr_margin - prev_margin)

            # Get cash flow statements for FCF growth
            cf_stmts = fmp_api.get_cash_flow_statements(ticker, period='annual')
            if cf_stmts and len(cf_stmts) >= 2:
                growth['fcf_growth_yoy'] = self._calculate_pct_change(
                    cf_stmts[0].get('freeCashFlow'),
                    cf_stmts[1].get('freeCashFlow')
                )

            # Get ratios for ROCE change
            ratios = fmp_api.get_financial_ratios(ticker, period='annual')
            if ratios and len(ratios) >= 6:
                curr_roce = ratios[0].get('returnOnCapitalEmployed')
                prev_roce = ratios[5].get('returnOnCapitalEmployed')
                if curr_roce is not None and prev_roce is not None:
                    growth['roce_change_5yr'] = safe_round(curr_roce - prev_roce)

        except Exception:
            pass

        return growth

    def _process_single_ticker(
        self,
        ticker_data: Tuple[str, str, Optional[str]]
    ) -> Optional[Dict[str, Any]]:
        """Process a single ticker and return the record."""
        ticker_id, ticker, sector = ticker_data

        try:
            # Create thread-local FMP API instance
            fmp_api = FMP_API_DATA()

            # Get sector ETF
            sector_etf = get_sector_etf(sector) if sector else None

            # Fetch price data
            start_date = get_utc_days_ago(365).strftime('%Y-%m-%d')
            end_date = get_current_utc_time().strftime('%Y-%m-%d')

            tickers_to_fetch = [ticker, 'SPY']
            if sector_etf:
                tickers_to_fetch.append(sector_etf)

            price_data = fetch_bulk_ohlcv_data_for_tickers(
                tickers_to_fetch, start_date, end_date,
                frequency='daily', returns=True
            )

            if ticker not in price_data:
                return None

            df = price_data[ticker]
            if 'returns' not in df.columns or df['returns'].dropna().empty:
                return None

            returns = df['returns'].dropna()
            spy_returns = None
            sector_returns = None

            if 'SPY' in price_data and 'returns' in price_data['SPY'].columns:
                spy_returns = price_data['SPY']['returns'].dropna()
            if sector_etf and sector_etf in price_data and 'returns' in price_data[sector_etf].columns:
                sector_returns = price_data[sector_etf]['returns'].dropna()

            # Calculate momentum metrics
            mf = MomentumFactors(df['close'])
            momentum_1m = safe_round(mf.one_month_return())
            momentum_3m = safe_round(mf.three_month_return())
            momentum_6m = safe_round(mf.six_month_return())

            # Calculate performance metrics
            ann_return = ReturnsCalculator.annualized_return(returns)
            ann_vol = RiskCalculator.annualized_volatility(returns)
            info_ratio = safe_divide(ann_return, ann_vol)

            # Calculate beta/alpha vs SPY
            beta_vs_spy = None
            alpha_vs_spy = None
            if spy_returns is not None and len(returns) > 10:
                beta_vs_spy = RiskCalculator.beta(returns, spy_returns)
                alpha_vs_spy = PerformanceCalculator.alpha(returns, spy_returns)

            # Calculate beta/alpha vs sector
            beta_vs_sector = None
            alpha_vs_sector = None
            if sector_returns is not None and len(returns) > 10:
                beta_vs_sector = RiskCalculator.beta(returns, sector_returns)
                alpha_vs_sector = PerformanceCalculator.alpha(returns, sector_returns)

            # Fetch TTM ratios from FMP
            raw_ratios = fmp_api.get_ratios_ttm(ticker)
            ratios = raw_ratios[0] if raw_ratios and len(raw_ratios) > 0 else {}

            # Calculate growth metrics
            growth = self._calculate_growth_metrics(ticker, fmp_api)

            # Build record
            record = {
                'ticker_id': UUID(ticker_id),
                'updated_at': get_current_utc_time(),
                'momentum_1m': momentum_1m,
                'momentum_3m': momentum_3m,
                'momentum_6m': momentum_6m,
                'ann_return': safe_round(ann_return),
                'ann_vol': safe_round(ann_vol),
                'beta_vs_spy': safe_round(beta_vs_spy),
                'beta_vs_sector': safe_round(beta_vs_sector),
                'alpha_vs_spy': safe_round(alpha_vs_spy),
                'alpha_vs_sector': safe_round(alpha_vs_sector),
                'information_ratio': safe_round(info_ratio),
                **growth,
            }

            # Map FMP ratios to DB columns
            for fmp_key, db_column in RATIO_KEY_MAP.items():
                record[db_column] = ratios.get(fmp_key)

            return record

        except Exception:
            return None

    def _upsert_records(self, records: List[Dict[str, Any]]) -> int:
        """Bulk upsert records to EquityScreener table."""
        if not records:
            return 0

        with MarketSession() as session:
            stmt = insert(EquityScreener).values(records)
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

    def run_update(self, max_workers: int = 5, batch_size: int = 50) -> None:
        """
        Run the equity screener update with parallel processing.

        Args:
            max_workers: Number of parallel threads to use
            batch_size: Number of records to upsert per batch
        """
        print(f"\n{'='*70}")
        print("EQUITY SCREENER UPDATE")
        print(f"{'='*70}")

        start_time = time.time()

        # Get equity tickers
        equity_tickers = self._get_equity_tickers()
        total_equities = len(equity_tickers)
        print(f"Found {total_equities} actively trading equities")

        if not equity_tickers:
            print("No equities to update")
            return

        print(f"Processing with {max_workers} workers...")

        records = []
        processed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self._process_single_ticker, ticker_data): ticker_data[1]
                for ticker_data in equity_tickers
            }

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                processed += 1

                try:
                    result = future.result()
                    if result:
                        records.append(result)
                        with self.lock:
                            self.total_updated += 1
                    else:
                        with self.lock:
                            self.total_errors += 1
                except Exception:
                    with self.lock:
                        self.total_errors += 1

                # Progress reporting
                if processed % 100 == 0:
                    print(f"Progress: {processed}/{total_equities} - "
                          f"Updated: {self.total_updated}, Errors: {self.total_errors}")

                # Batch upsert
                if len(records) >= batch_size:
                    self._upsert_records(records)
                    records = []

        # Upsert remaining records
        if records:
            self._upsert_records(records)

        # Summary
        duration = time.time() - start_time
        print(f"\n{'='*70}")
        print("EQUITY SCREENER UPDATE SUMMARY")
        print(f"{'='*70}")
        print(f"Total equities processed: {total_equities}")
        print(f"Successfully updated: {self.total_updated}")
        print(f"Errors: {self.total_errors}")
        print(f"Time taken: {duration:.2f} seconds")
        if total_equities > 0:
            print(f"Average time per ticker: {duration/total_equities:.3f} seconds")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    updater = UpdateEquityScreenerTable()
    updater.run_update(max_workers=5)
