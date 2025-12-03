# """
# Populates the EquityScreener table with calculated metrics for all tickers.

# Reads tickers from tickers.csv, processes them in parallel batches of 10,
# calculates momentum/performance/risk metrics and TTM ratios, then upserts to DB.
# """
# import csv
# import logging
# from pathlib import Path
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from tkinter import E
# from uuid import UUID

# import pandas as pd
# from sqlalchemy.dialects.postgresql import insert

# from app.db.core.db_config import MarketSession
# from app.db.core.models.market_data_models import Ticker, EquityScreener
# from app.core.calculations.factors.momentum import MomentumFactors
# from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
# from app.core.calculations.returns.calculator import ReturnsCalculator
# from app.core.calculations.risk.calculator import RiskCalculator
# from app.core.calculations.performance.calculator import PerformanceCalculator
# from app.utils.ticker_utils import get_sector_etf
# from app.utils.time_utils import get_current_utc_time, get_utc_days_ago
# from app.db.core.pull_fmp_data import FMP_API_DATA

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# BATCH_SIZE = 10
# CSV_PATH = Path(__file__).parent / "tickers.csv"

# # FMP API key -> EquityScreener column name mapping
# RATIO_KEY_MAP = {
#     'dividendYielTTM': 'dividend_yield_ttm',
#     'peRatioTTM': 'pe_ratio_ttm',
#     'pegRatioTTM': 'peg_ratio_ttm',
#     'priceToBookRatioTTM': 'price_to_book_ratio_ttm',
#     'priceToSalesRatioTTM': 'price_to_sales_ratio_ttm',
#     'priceToFreeCashFlowsRatioTTM': 'price_to_free_cash_flows_ratio_ttm',
#     'priceToOperatingCashFlowsRatioTTM': 'price_to_operating_cash_flows_ratio_ttm',
#     'enterpriseValueMultipleTTM': 'enterprise_value_multiple_ttm',
#     'payoutRatioTTM': 'payout_ratio_ttm',
#     'grossProfitMarginTTM': 'gross_profit_margin_ttm',
#     'operatingProfitMarginTTM': 'operating_profit_margin_ttm',
#     'pretaxProfitMarginTTM': 'pretax_profit_margin_ttm',
#     'netProfitMarginTTM': 'net_profit_margin_ttm',
#     'returnOnAssetsTTM': 'return_on_assets_ttm',
#     'returnOnEquityTTM': 'return_on_equity_ttm',
#     'returnOnCapitalEmployedTTM': 'return_on_capital_employed_ttm',
#     'operatingCashFlowSalesRatioTTM': 'operating_cash_flow_sales_ratio_ttm',
#     'freeCashFlowOperatingCashFlowRatioTTM': 'free_cash_flow_operating_cash_flow_ratio_ttm',
#     'capitalExpenditureCoverageRatioTTM': 'capital_expenditure_coverage_ratio_ttm',
#     'dividendPaidAndCapexCoverageRatioTTM': 'dividend_paid_and_capex_coverage_ratio_ttm',
#     'debtRatioTTM': 'debt_ratio_ttm',
#     'debtEquityRatioTTM': 'debt_equity_ratio_ttm',
#     'longTermDebtToCapitalizationTTM': 'long_term_debt_to_capitalization_ttm',
#     'totalDebtToCapitalizationTTM': 'total_debt_to_capitalization_ttm',
#     'interestCoverageTTM': 'interest_coverage_ttm',
#     'cashFlowToDebtRatioTTM': 'cash_flow_to_debt_ratio_ttm',
#     'shortTermCoverageRatiosTTM': 'short_term_coverage_ratios_ttm',
#     'companyEquityMultiplierTTM': 'company_equity_multiplier_ttm',
#     'quickRatioTTM': 'quick_ratio_ttm',
#     'cashRatioTTM': 'cash_ratio_ttm',
#     'cashConversionCycleTTM': 'cash_conversion_cycle_ttm',
#     'receivablesTurnoverTTM': 'receivables_turnover_ttm',
#     'payablesTurnoverTTM': 'payables_turnover_ttm',
#     'inventoryTurnoverTTM': 'inventory_turnover_ttm',
#     'assetTurnoverTTM': 'asset_turnover_ttm',
# }


# def load_tickers_from_csv() -> list[dict]:
#     """Load tickers and their IDs from the CSV file."""
#     tickers = []
#     with open(CSV_PATH, 'r') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             tickers.append({'ticker': row['ticker'], 'id': row['id']})
#     return tickers


# def calculate_ebit_cagr(fmp_api: FMP_API_DATA, ticker: str, years: int) -> float | None:
#     """Calculate EBIT CAGR from annual income statements.

#     CAGR is only valid for profitable companies. Returns None if:
#     - Insufficient data
#     - Either EBIT value is missing or zero
#     - Either EBIT value is negative (unprofitable companies excluded from growth screens)

#     Reason: CAGR assumes compounding which is invalid for negative values.
#     "Losing less money" is not growth - unprofitable companies should be
#     evaluated using different metrics (loss improvement %, EBIT delta, etc.).
#     """
#     income_statements = fmp_api.get_income_statements(ticker, period='annual')

#     if not income_statements or len(income_statements) < years:
#         return None

#     ending_ebit = income_statements[0].get('operatingIncome')
#     beginning_ebit = income_statements[years - 1].get('operatingIncome')

#     if not ending_ebit or not beginning_ebit:
#         return None

#     # CAGR only valid when both values are positive (profitable company)
#     # Unprofitable companies (negative EBIT) should be excluded from growth screens
#     if beginning_ebit <= 0 or ending_ebit <= 0:
#         return None

#     cagr = (ending_ebit / beginning_ebit) ** (1 / years) - 1
#     return round(cagr, 4)


# def process_single_ticker(ticker: str, ticker_id: str) -> dict | None:
#     """
#     Calculate all metrics for a single ticker.

#     Returns dict with all EquityScreener fields, or None on error.
#     """
#     try:
#         fmp_api = FMP_API_DATA()

#         # Get sector ETF for the ticker
#         with MarketSession() as session:
#             ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker).first()
#             if not ticker_obj or not ticker_obj.sector:
#                 logger.warning(f"{ticker}: No sector found, skipping")
#                 return None
#             sector_etf = get_sector_etf(ticker_obj.sector)
#             if not sector_etf:
#                 logger.warning(f"{ticker}: No sector ETF for sector '{ticker_obj.sector}', skipping")
#                 return None

#         # Fetch price data for last 365 days
#         start_date = get_utc_days_ago(365).strftime('%Y-%m-%d')
#         end_date = get_current_utc_time().strftime('%Y-%m-%d')

#         price_data = fetch_bulk_ohlcv_data_for_tickers(
#             [ticker, 'SPY', sector_etf],
#             start_date,
#             end_date,
#             frequency='daily',
#             returns=True
#         )

#         if ticker not in price_data:
#             logger.warning(f"{ticker}: No price data available")
#             return None

#         df = pd.DataFrame(price_data[ticker])
#         spy_df = pd.DataFrame(price_data.get('SPY', []))
#         sector_df = pd.DataFrame(price_data.get(sector_etf, []))

#         if df.empty or spy_df.empty or sector_df.empty:
#             logger.warning(f"{ticker}: Insufficient price data")
#             return None

#         # Calculate momentum metrics
#         mf = MomentumFactors(df['close'])
#         momentum_1m = round(mf.one_month_return(), 4)
#         momentum_3m = round(mf.three_month_return(), 4)
#         momentum_6m = round(mf.six_month_return(), 4)

#         # Calculate performance metrics
#         ann_return = round(ReturnsCalculator.annualized_return(df['returns']), 4)
#         ann_vol = round(RiskCalculator.annualized_volatility(df['returns']), 4)

#         # Calculate beta metrics
#         beta_vs_spy = round(RiskCalculator.beta(df['returns'], spy_df['returns']), 4)
#         beta_vs_sector = round(RiskCalculator.beta(df['returns'], sector_df['returns']), 4)

#         # Calculate alpha metrics
#         alpha_vs_spy = round(PerformanceCalculator.alpha_jensen(df['returns'], spy_df['returns']), 4)
#         alpha_vs_sector = round(PerformanceCalculator.alpha_jensen(df['returns'], sector_df['returns']), 4)

#         # Fetch TTM ratios from FMP
#         raw_ratios = fmp_api.get_ratios_ttm(ticker)
#         if raw_ratios and len(raw_ratios) > 0:
#             raw_ratios = raw_ratios[0]
#         else:
#             raw_ratios = {}

#         # Calculate EBIT CAGR
#         ebit_cagr_5yr = calculate_ebit_cagr(fmp_api, ticker, years=5)
#         ebit_cagr_3yr = calculate_ebit_cagr(fmp_api, ticker, years=3)

#         # Build the record
#         record = {
#             'ticker_id': UUID(ticker_id),
#             'updated_at': get_current_utc_time(),
#             'momentum_1m': momentum_1m,
#             'momentum_3m': momentum_3m,
#             'momentum_6m': momentum_6m,
#             'ann_return': ann_return,
#             'ann_vol': ann_vol,
#             'beta_vs_spy': beta_vs_spy,
#             'beta_vs_sector': beta_vs_sector,
#             'alpha_vs_spy': alpha_vs_spy,
#             'alpha_vs_sector': alpha_vs_sector,
#             'ebit_cagr_5yr': ebit_cagr_5yr,
#             'ebit_cagr_3yr': ebit_cagr_3yr,
#         }

#         # Map FMP ratios to DB columns
#         for fmp_key, db_column in RATIO_KEY_MAP.items():
#             record[db_column] = raw_ratios.get(fmp_key)

#         logger.info(f"{ticker}: Successfully processed")
#         return record

#     except Exception as e:
#         logger.error(f"{ticker}: Error processing - {e}")
#         return None


# def process_batch(batch: list[dict]) -> list[dict]:
#     """Process a batch of tickers concurrently using ThreadPoolExecutor."""
#     results = []

#     with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
#         future_to_ticker = {
#             executor.submit(process_single_ticker, item['ticker'], item['id']): item['ticker']
#             for item in batch
#         }

#         for future in as_completed(future_to_ticker):
#             ticker = future_to_ticker[future]
#             try:
#                 result = future.result()
#                 if result:
#                     results.append(result)
#             except Exception as e:
#                 logger.error(f"{ticker}: Unexpected error - {e}")

#     return results


# def upsert_screener_data(records: list[dict]) -> None:
#     """Bulk upsert records to EquityScreener table."""
#     if not records:
#         return

#     with MarketSession() as session:
#         stmt = insert(EquityScreener).values(records)

#         # On conflict, update all columns except ticker_id
#         update_columns = {col: stmt.excluded[col] for col in records[0].keys() if col != 'ticker_id'}

#         stmt = stmt.on_conflict_do_update(
#             index_elements=['ticker_id'],
#             set_=update_columns
#         )

#         session.execute(stmt)
#         session.commit()
#         logger.info(f"Upserted {len(records)} records to EquityScreener")


# def run_screener_build() -> None:
#     """Main entry point - processes all tickers and populates EquityScreener."""
#     tickers = load_tickers_from_csv()
#     total_tickers = len(tickers)
#     total_batches = (total_tickers + BATCH_SIZE - 1) // BATCH_SIZE

#     logger.info(f"Starting screener build: {total_tickers} tickers in {total_batches} batches")

#     success_count = 0
#     failure_count = 0

#     for batch_num in range(total_batches):
#         start_idx = batch_num * BATCH_SIZE
#         end_idx = min(start_idx + BATCH_SIZE, total_tickers)
#         batch = tickers[start_idx:end_idx]

#         results = process_batch(batch)

#         batch_success = len(results)
#         batch_failure = len(batch) - batch_success
#         success_count += batch_success
#         failure_count += batch_failure

#         if results:
#             upsert_screener_data(results)

#         logger.info(f"Batch {batch_num + 1}/{total_batches}: {batch_success} success, {batch_failure} failed")

#     logger.info(f"Screener build complete: {success_count} success, {failure_count} failed out of {total_tickers}")


# def test_single_ticker() -> None:
#     """Test function - processes only the first ticker from the CSV and pushes to DB."""
#     tickers = load_tickers_from_csv()

#     if not tickers:
#         logger.error("No tickers found in CSV")
#         return

#     first_ticker = tickers[0]
#     logger.info(f"Testing with first ticker: {first_ticker['ticker']} (ID: {first_ticker['id']})")

#     result = process_single_ticker(first_ticker['ticker'], first_ticker['id'])

#     if result:
#         upsert_screener_data([result])
#         logger.info(f"Test successful - {first_ticker['ticker']} pushed to EquityScreener")
#         logger.info(f"Record: {result}")
#     else:
#         logger.error(f"Test failed - could not process {first_ticker['ticker']}")


# if __name__ == "__main__":
#     from app.utils.serialize_output import serialize_sqlalchemy_obj
#     with MarketSession() as session:
#         result = session.query(EquityScreener, Ticker).join(Ticker).filter(
#             Ticker.market_cap > 1_000_000_000,
#             Ticker.is_actively_trading == True,
#             Ticker.is_etf == False,
#             EquityScreener.alpha_vs_sector > 0.2,
#             EquityScreener.beta_vs_sector < 0.7,
#             EquityScreener.ebit_cagr_5yr > 0.2
#         ).first()

#         print(serialize_sqlalchemy_obj(result[0]))
#         print(result[0].ticker.ticker)


# """
# Screener Metrics Calculator

# Calculates NEW metrics for the equity screener (not already in EquityScreener table):
# 1. Information Ratio (ann_return / ann_vol)
# 2. 3yr Revenue CAGR
# 3. YoY EBIT Growth (%)
# 4. YoY Operating Margin Change (ppt)
# 5. 5-yr ROCE Change (ppt)
# 6. YoY EPS Growth (%)
# 7. YoY FCF Growth (%)

# Note: PEG, Operating Margin, ROCE, Interest Coverage, OCF/Sales are already
# available in EquityScreener from ratios-ttm data.
# """
# from __future__ import annotations

# from dataclasses import dataclass
# from typing import Optional, List

# import numpy as np

# from app.core.calculations.core.data_service import DataService
# from app.core.calculations.core.models import FundamentalData
# from app.core.calculations.core.helpers import sort_rows_desc_by_date, safe_divide


# @dataclass
# class ScreenerMetrics:
#     """Container for calculated screener metrics."""
#     ticker: str
#     information_ratio: Optional[float] = None
#     revenue_cagr_3yr: Optional[float] = None
#     ebit_growth_yoy: Optional[float] = None
#     operating_margin_change_yoy: Optional[float] = None
#     roce_change_5yr: Optional[float] = None
#     eps_growth_yoy: Optional[float] = None
#     fcf_growth_yoy: Optional[float] = None


# class ScreenerMetricsCalculator:
#     """
#     Calculates NEW screener metrics from fundamental data.

#     Data Requirements:
#     - ann_return, ann_vol: From existing EquityScreener (for information_ratio)
#     - Income statements (annual, 5+ years): For revenue CAGR, EBIT growth, EPS growth, margin changes
#     - Cash flow statements (annual, 2+ years): For FCF growth
#     - Financial ratios (annual, 5+ years): For ROCE change
#     - Balance sheets (annual, 5+ years): Fallback for ROCE calculation
#     """

#     def __init__(
#         self,
#         ticker: str,
#         data_service: Optional[DataService] = None,
#         fundamental_data: Optional[FundamentalData] = None,
#         ann_return: Optional[float] = None,
#         ann_vol: Optional[float] = None,
#     ):
#         self.ticker = ticker.upper()
#         self.ds = data_service or DataService()
#         self.ann_return = ann_return
#         self.ann_vol = ann_vol

#         # Fetch or use provided fundamental data
#         if fundamental_data is not None:
#             self.fund = fundamental_data
#         else:
#             self.fund = self.ds.get_fundamentals(self.ticker)

#         # Sort statements by date descending (most recent first)
#         self.income_statements = sort_rows_desc_by_date(self.fund.income_statements)
#         self.balance_sheets = sort_rows_desc_by_date(self.fund.balance_sheets)
#         self.cash_flow_statements = sort_rows_desc_by_date(self.fund.cash_flow_statements)
#         self.financial_ratios = sort_rows_desc_by_date(self.fund.financial_ratios)

#     # -------------------- Information Ratio -------------------- #
#     def calc_information_ratio(self) -> float:
#         """Information Ratio = Annualized Return / Annualized Volatility."""
#         if self.ann_return is None or self.ann_vol is None:
#             return np.nan
#         return safe_divide(self.ann_return, self.ann_vol)

#     # -------------------- 3yr Revenue CAGR -------------------- #
#     def calc_revenue_cagr_3yr(self) -> float:
#         """3-year Revenue CAGR from annual income statements."""
#         annual_stmts = self._filter_annual_statements(self.income_statements)
#         if len(annual_stmts) < 4:  # Need current + 3 years ago
#             return np.nan

#         current_rev = getattr(annual_stmts[0], 'revenue', None)
#         rev_3yr_ago = getattr(annual_stmts[3], 'revenue', None)

#         return self._cagr(current_rev, rev_3yr_ago, years=3)

#     # -------------------- YoY EBIT Growth -------------------- #
#     def calc_ebit_growth_yoy(self) -> float:
#         """Year-over-year EBIT growth from annual income statements."""
#         annual_stmts = self._filter_annual_statements(self.income_statements)
#         if len(annual_stmts) < 2:
#             return np.nan

#         # Use operatingIncome as EBIT proxy
#         current_ebit = getattr(annual_stmts[0], 'operatingIncome', None)
#         prev_ebit = getattr(annual_stmts[1], 'operatingIncome', None)

#         return self._pct_change(current_ebit, prev_ebit)

#     # -------------------- YoY EPS Growth -------------------- #
#     def calc_eps_growth_yoy(self) -> float:
#         """Year-over-year EPS growth from annual income statements."""
#         annual_stmts = self._filter_annual_statements(self.income_statements)
#         if len(annual_stmts) < 2:
#             return np.nan

#         current_eps = getattr(annual_stmts[0], 'eps', None)
#         prev_eps = getattr(annual_stmts[1], 'eps', None)

#         return self._pct_change(current_eps, prev_eps)

#     # -------------------- YoY FCF Growth -------------------- #
#     def calc_fcf_growth_yoy(self) -> float:
#         """Year-over-year Free Cash Flow growth from annual cash flow statements."""
#         annual_stmts = self._filter_annual_statements(self.cash_flow_statements)
#         if len(annual_stmts) < 2:
#             return np.nan

#         current_fcf = getattr(annual_stmts[0], 'freeCashFlow', None)
#         prev_fcf = getattr(annual_stmts[1], 'freeCashFlow', None)

#         return self._pct_change(current_fcf, prev_fcf)

#     # -------------------- YoY Operating Margin Change -------------------- #
#     def calc_operating_margin_change_yoy(self) -> float:
#         """Year-over-year change in operating margin (percentage points)."""
#         annual_ratios = self._filter_annual_statements(self.financial_ratios)
#         if len(annual_ratios) >= 2:
#             current_margin = self._safe_get_attr(annual_ratios[0], 'operatingProfitMargin')
#             prev_margin = self._safe_get_attr(annual_ratios[1], 'operatingProfitMargin')
#             if not np.isnan(current_margin) and not np.isnan(prev_margin):
#                 return current_margin - prev_margin

#         # Fallback: calculate from income statements
#         annual_stmts = self._filter_annual_statements(self.income_statements)
#         if len(annual_stmts) < 2:
#             return np.nan

#         curr_op_income = getattr(annual_stmts[0], 'operatingIncome', None)
#         curr_revenue = getattr(annual_stmts[0], 'revenue', None)
#         prev_op_income = getattr(annual_stmts[1], 'operatingIncome', None)
#         prev_revenue = getattr(annual_stmts[1], 'revenue', None)

#         curr_margin = safe_divide(curr_op_income, curr_revenue)
#         prev_margin = safe_divide(prev_op_income, prev_revenue)

#         if np.isnan(curr_margin) or np.isnan(prev_margin):
#             return np.nan

#         return curr_margin - prev_margin

#     # -------------------- 5-yr ROCE Change -------------------- #
#     def calc_roce_change_5yr(self) -> float:
#         """5-year change in ROCE (percentage points)."""
#         annual_ratios = self._filter_annual_statements(self.financial_ratios)
#         if len(annual_ratios) >= 6:
#             current_roce = self._safe_get_attr(annual_ratios[0], 'returnOnCapitalEmployed')
#             roce_5yr_ago = self._safe_get_attr(annual_ratios[5], 'returnOnCapitalEmployed')
#             if not np.isnan(current_roce) and not np.isnan(roce_5yr_ago):
#                 return current_roce - roce_5yr_ago

#         # Fallback: calculate ROCE from statements
#         # ROCE = EBIT / (Total Assets - Current Liabilities)
#         annual_income = self._filter_annual_statements(self.income_statements)
#         annual_balance = self._filter_annual_statements(self.balance_sheets)

#         if len(annual_income) < 6 or len(annual_balance) < 6:
#             return np.nan

#         curr_roce = self._calc_roce(annual_income[0], annual_balance[0])
#         prev_roce = self._calc_roce(annual_income[5], annual_balance[5])

#         if np.isnan(curr_roce) or np.isnan(prev_roce):
#             return np.nan

#         return curr_roce - prev_roce

#     def _calc_roce(self, income_stmt, balance_sheet) -> float:
#         """Calculate ROCE from income statement and balance sheet."""
#         ebit = getattr(income_stmt, 'operatingIncome', None)
#         total_assets = getattr(balance_sheet, 'totalAssets', None)
#         current_liab = getattr(balance_sheet, 'totalCurrentLiabilities', None)

#         if ebit is None or total_assets is None or current_liab is None:
#             return np.nan

#         capital_employed = float(total_assets) - float(current_liab)
#         return safe_divide(ebit, capital_employed)

#     # -------------------- Helper Methods -------------------- #
#     def _filter_annual_statements(self, statements: List) -> List:
#         """Filter statements to only annual (not quarterly) based on date gaps."""
#         if not statements or len(statements) < 2:
#             return statements

#         dates = [getattr(s, 'date', None) for s in statements if getattr(s, 'date', None)]
#         if len(dates) < 2:
#             return statements

#         # If gap between first two is ~90 days, it's quarterly
#         gap = abs((dates[0] - dates[1]).days)
#         if 60 <= gap <= 120:
#             return statements[::4]  # Take every 4th for annual

#         return statements

#     @staticmethod
#     def _cagr(end_value: Optional[float], start_value: Optional[float], years: float) -> float:
#         """Calculate Compound Annual Growth Rate."""
#         if end_value is None or start_value is None or years <= 0:
#             return np.nan
#         try:
#             if float(start_value) <= 0 or float(end_value) <= 0:
#                 return np.nan
#             return (float(end_value) / float(start_value)) ** (1.0 / years) - 1.0
#         except Exception:
#             return np.nan

#     @staticmethod
#     def _pct_change(current: Optional[float], previous: Optional[float]) -> float:
#         """Calculate percentage change."""
#         if current is None or previous is None:
#             return np.nan
#         try:
#             if float(previous) == 0:
#                 return np.nan
#             return (float(current) - float(previous)) / abs(float(previous))
#         except Exception:
#             return np.nan

#     @staticmethod
#     def _safe_get_attr(obj, attr: str) -> float:
#         """Safely get attribute and convert to float."""
#         try:
#             val = getattr(obj, attr, None)
#             if val is None:
#                 return np.nan
#             return float(val)
#         except Exception:
#             return np.nan

#     # -------------------- Calculate All -------------------- #
#     def calc_all(self) -> ScreenerMetrics:
#         """Calculate all screener metrics."""
#         return ScreenerMetrics(
#             ticker=self.ticker,
#             information_ratio=self._round_or_nan(self.calc_information_ratio()),
#             revenue_cagr_3yr=self._round_or_nan(self.calc_revenue_cagr_3yr()),
#             ebit_growth_yoy=self._round_or_nan(self.calc_ebit_growth_yoy()),
#             operating_margin_change_yoy=self._round_or_nan(self.calc_operating_margin_change_yoy()),
#             roce_change_5yr=self._round_or_nan(self.calc_roce_change_5yr()),
#             eps_growth_yoy=self._round_or_nan(self.calc_eps_growth_yoy()),
#             fcf_growth_yoy=self._round_or_nan(self.calc_fcf_growth_yoy()),
#         )

#     @staticmethod
#     def _round_or_nan(value: float, decimals: int = 4) -> Optional[float]:
#         """Round value or return None if NaN."""
#         if value is None or np.isnan(value) or np.isinf(value):
#             return None
#         return round(value, decimals)


# def update_all_screener_growth_metrics():
#     """
#     Update all records in the equity_screener table with the new growth metrics.
#     Uses ann_return and ann_vol from the existing screener record for information_ratio.
#     """
#     from app.db.core.db_config import MarketSession
#     from app.db.core.models.market_data_models import EquityScreener, Ticker

#     ds = DataService()
#     updated_count = 0
#     error_count = 0

#     with MarketSession() as session:
#         # Get all screener records with their ticker symbols
#         records = (
#             session.query(EquityScreener, Ticker.ticker)
#             .join(Ticker, EquityScreener.ticker_id == Ticker.id)
#             .all()
#         )

#         total = len(records)
#         print(f"Found {total} records to update")

#         for i, (screener_record, ticker_symbol) in enumerate(records):
#             try:
#                 # Get ann_return and ann_vol from existing screener record
#                 ann_return = float(screener_record.ann_return) if screener_record.ann_return else None
#                 ann_vol = float(screener_record.ann_vol) if screener_record.ann_vol else None

#                 # Calculate new metrics
#                 calc = ScreenerMetricsCalculator(
#                     ticker=ticker_symbol,
#                     data_service=ds,
#                     ann_return=ann_return,
#                     ann_vol=ann_vol,
#                 )
#                 metrics = calc.calc_all()

#                 # Update the record
#                 screener_record.information_ratio = metrics.information_ratio
#                 screener_record.revenue_cagr_3yr = metrics.revenue_cagr_3yr
#                 screener_record.ebit_growth_yoy = metrics.ebit_growth_yoy
#                 screener_record.eps_growth_yoy = metrics.eps_growth_yoy
#                 screener_record.fcf_growth_yoy = metrics.fcf_growth_yoy
#                 screener_record.operating_margin_change_yoy = metrics.operating_margin_change_yoy
#                 screener_record.roce_change_5yr = metrics.roce_change_5yr

#                 updated_count += 1

#                 # Progress logging every 50 records
#                 if (i + 1) % 50 == 0:
#                     print(f"Processed {i + 1}/{total} records...")
#                     session.commit()  # Commit in batches

#             except Exception as e:
#                 print(f"Error processing {ticker_symbol}: {e}")
#                 error_count += 1
#                 continue

#         # Final commit
#         session.commit()

#     print(f"\nCompleted: {updated_count} updated, {error_count} errors out of {total} total")



