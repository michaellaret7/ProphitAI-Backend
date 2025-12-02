import asyncio
import pandas as pd
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from app.core.agentic_framework.tool_lib.common.responses import success_response
from datetime import datetime
from typing import Optional
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.core.calculations.risk.calculator import RiskCalculator

df = pd.DataFrame()

# 1. Get Base Data from DB
with MarketSession() as session:
    results = session.query(Ticker).filter(
        Ticker.is_actively_trading == True, 
        Ticker.is_etf == False, 
        Ticker.market_cap > 10_000_000_000,
        # Use .in_() to match multiple values
        Ticker.sub_industry.in_([
            'application_software',
            'technology_hardware_storage_and_peripherals',
            'semiconductors'
        ])
    ).all()

# Convert DB results to a DataFrame immediately
# Ensure 'ticker' column is renamed to 'symbol' for easy merging later if needed, or keep as 'ticker'
base_data_list = [serialize_sqlalchemy_obj(row) for row in results]
base_df = pd.DataFrame(base_data_list)
# Standardize the join column name
if 'ticker' in base_df.columns:
    base_df.rename(columns={'ticker': 'symbol'}, inplace=True)

# Helper list for the async function
target_tickers = base_df['symbol'].tolist()

print(f"Processing {len(target_tickers)} tickers...")

async def get_ttm_ratios(tickers: list[str]):
    fmp_api = FMP_API_DATA()
    semaphore = asyncio.Semaphore(10)

    async def fetch_ticker_data(ticker):
        async with semaphore:
            try:
                # Fetch TTM and Quarterly data concurrently
                ttm_future = asyncio.to_thread(fmp_api.get_ratios_ttm, ticker)
                quart_future = asyncio.to_thread(fmp_api.get_financial_ratios, ticker, period='quarter')
                
                ttm_data, quart_data = await asyncio.gather(ttm_future, quart_future)

                combined_row = {'symbol': ticker} # Start with key

                # 1. Add TTM Data
                if ttm_data and isinstance(ttm_data, list) and len(ttm_data) > 0:
                    combined_row.update(ttm_data[0])
                
                # 2. Add Recent Quarterly Data
                if quart_data and isinstance(quart_data, list) and len(quart_data) > 0:
                    # We take the most recent quarter (index 0)
                    recent_q = quart_data[0]
                    for k, v in recent_q.items():
                        # If key exists (from TTM), rename it to distinguish
                        if k in combined_row and k != 'symbol':
                            combined_row[f"quart_{k}"] = v
                        else:
                            combined_row[k] = v
                
                return combined_row

            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
                return None

    tasks = [fetch_ticker_data(t) for t in tickers]
    fetched_results = await asyncio.gather(*tasks)
    
    # Filter None
    valid_results = [r for r in fetched_results if r is not None]
    
    return pd.DataFrame(valid_results)

# Run Async Fetch
api_df = asyncio.run(get_ttm_ratios(target_tickers))

# Final Merge: Left join to keep all DB rows, adding API data where available
final_df = pd.merge(base_df, api_df, on='symbol', how='left')

print(final_df.head())
print(f"Final columns: {len(final_df.columns)}")
for item in final_df.columns:
    print(item)


def screen_stocks(df: pd.DataFrame, max_pe: float = 25.0, max_pb: float = 3.0, min_roce: float = 0.001):
    """
    Screens the DataFrame for stocks matching P/E and P/B criteria.
    
    Args:
        df (pd.DataFrame): The dataframe containing financial data.
        max_pe (float): Maximum Price to Earnings ratio allowed.
        max_pb (float): Maximum Price to Book ratio allowed.
        
    Returns:
        pd.DataFrame: A filtered DataFrame with only matching stocks.
    """
    
    # Ensure we have numeric data for the columns we care about
    # We prioritize TTM values, but you can swap these for quarterly ones (e.g., 'quart_peRatio')
    target_pe_col = 'peRatioTTM' 
    target_pb_col = 'priceToBookRatioTTM'
    target_roce_col = 'returnOnCapitalEmployed'

    # Check if columns exist
    if target_pe_col not in df.columns or target_pb_col not in df.columns:
        print(f"Error: Required columns {target_pe_col} or {target_pb_col} or {target_roce_col} not found.")
        return pd.DataFrame()

    # Clean/Convert to numeric, coercing errors to NaN (so we can drop them)
    df[target_pe_col] = pd.to_numeric(df[target_pe_col], errors='coerce')
    df[target_pb_col] = pd.to_numeric(df[target_pb_col], errors='coerce')
    df[target_roce_col] = pd.to_numeric(df[target_roce_col], errors='coerce')

    mask = (
        (df[target_pe_col] > 0) & 
        (df[target_pe_col] <= max_pe) & 
        (df[target_pb_col] <= max_pb) &
        (df[target_roce_col] >= min_roce)
    )
    
    filtered_df = df[mask].copy()
    
    return filtered_df

# --- Usage Example ---
screened_df = screen_stocks(final_df, max_pe=20, max_pb=5, min_roce=0.001)
print(f"Found {len(screened_df)} matches:")
print(screened_df[['symbol', 'peRatioTTM', 'priceToBookRatioTTM', 'sub_industry', 'returnOnCapitalEmployed']])

for item in screened_df.columns:
    print(item)




from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

with MarketSession() as session:
    # Get all unique sectors for ETFs only
    tickers = session.query(Ticker).filter(Ticker.is_etf.is_(True), Ticker.sector == 'etf').all()
    for ticker in tickers:
        print(ticker.ticker)
