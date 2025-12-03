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

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, EquityScreener
from app.core.calculations.factors.momentum import MomentumFactors
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.utils.ticker_utils import get_sector_etf
from app.utils.time_utils import get_current_utc_time, get_utc_days_ago
from app.db.core.pull_fmp_data import FMP_API_DATA

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


    