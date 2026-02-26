"""
ETF Screener Data Builder

Reads ETF tickers from etf.csv, pulls price data, and calculates metrics
for the ETFScreener table: ann_vol, ann_ret, information_ratio, beta, etc.
"""

import pandas as pd
import numpy as np
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, ETFInfo, ETFScreener
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.utils.time_utils import get_current_utc_time, get_utc_days_ago
from sqlalchemy.dialects.postgresql import insert


def load_etfs_from_csv(csv_path: str = "etf.csv") -> pd.DataFrame:
    """Load ETF tickers and IDs from CSV file."""
    return pd.read_csv(csv_path)


def get_etf_metadata(ticker_ids: list[str]) -> dict:
    """
    Fetch ETF metadata from database (industry, sub_industry, expense_ratio, nav, market_cap, dollar_volume).
    Returns dict keyed by ticker_id.
    """
    metadata = {}

    with MarketSession() as session:
        # Query Ticker and ETFInfo tables
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


def calculate_etf_metrics(etf_df: pd.DataFrame, lookback_days: int = 365) -> list[dict]:
    """
    Calculate performance metrics for all ETFs.

    Metrics calculated:
    - ann_ret: Annualized return
    - ann_vol: Annualized volatility
    - information_ratio: ann_ret / ann_vol
    - beta: Beta vs SPY
    """
    # Get date range
    end_date = get_current_utc_time().strftime('%Y-%m-%d')
    start_date = get_utc_days_ago(lookback_days).strftime('%Y-%m-%d')

    # Get list of tickers
    tickers = etf_df['ticker'].tolist()
    ticker_to_id = dict(zip(etf_df['ticker'], etf_df['ticker_id']))

    # Add SPY for beta calculation
    all_tickers = tickers + ['SPY'] if 'SPY' not in tickers else tickers

    print(f"Fetching price data for {len(tickers)} ETFs from {start_date} to {end_date}...")

    # Fetch price data with returns
    price_data = fetch_bulk_ohlcv_data_for_tickers(
        all_tickers,
        start_date,
        end_date,
        frequency='daily',
    )

    print(f"Successfully fetched data for {len(price_data)} tickers")

    # Get SPY returns for beta calculation
    spy_returns = None
    if 'SPY' in price_data:
        spy_df = price_data['SPY']
        if 'adj_close' in spy_df.columns:
            spy_returns = spy_df['adj_close'].pct_change().dropna()

    # Get ETF metadata
    ticker_ids = etf_df['ticker_id'].tolist()
    metadata = get_etf_metadata(ticker_ids)

    # Calculate metrics for each ETF
    results = []

    for _, row in etf_df.iterrows():
        ticker = row['ticker']
        ticker_id = row['ticker_id']

        if ticker not in price_data:
            print(f"  {ticker}: No price data available")
            continue

        df = price_data[ticker]

        if 'adj_close' not in df.columns or df['adj_close'].dropna().empty:
            print(f"  {ticker}: No price data")
            continue

        returns = df['adj_close'].pct_change().dropna()

        # Calculate metrics
        ann_ret = ReturnsCalculator.annualized_return(returns)
        ann_vol = RiskCalculator.annualized_volatility(returns)

        # Information ratio
        info_ratio = None
        if ann_vol and ann_vol > 0 and not np.isnan(ann_vol):
            info_ratio = ann_ret / ann_vol if not np.isnan(ann_ret) else None

        # Beta vs SPY
        beta = None
        if spy_returns is not None and len(returns) > 10:
            beta = RiskCalculator.beta(returns, spy_returns)
            if np.isnan(beta):
                beta = None

        # Get metadata
        meta = metadata.get(ticker_id, {})

        record = {
            'ticker_id': UUID(ticker_id),
            'updated_at': get_current_utc_time(),
            'industry': meta.get('industry'),
            'sub_industry': meta.get('sub_industry'),
            'expense_ratio': meta.get('expense_ratio'),
            'nav': meta.get('nav'),
            'ann_vol': round(ann_vol, 4) if ann_vol and not np.isnan(ann_vol) else None,
            'ann_ret': round(ann_ret, 4) if ann_ret and not np.isnan(ann_ret) else None,
            'information_ratio': round(info_ratio, 4) if info_ratio and not np.isnan(info_ratio) else None,
            'beta': round(beta, 4) if beta else None,
            'market_cap': meta.get('market_cap'),
            'dollar_volume': meta.get('dollar_volume'),
        }

        results.append(record)
        print(f"  {ticker}: ann_ret={record['ann_ret']}, ann_vol={record['ann_vol']}, beta={record['beta']}")

    return results


def upsert_etf_screener_data(records: list[dict]) -> None:
    """Bulk upsert records to ETFScreener table."""
    if not records:
        print("No records to upsert")
        return

    with MarketSession() as session:
        stmt = insert(ETFScreener).values(records)

        # On conflict, update all columns except ticker_id
        update_columns = {col: stmt.excluded[col] for col in records[0].keys() if col != 'ticker_id'}

        stmt = stmt.on_conflict_do_update(
            index_elements=['ticker_id'],
            set_=update_columns
        )

        session.execute(stmt)
        session.commit()
        print(f"Upserted {len(records)} records to ETFScreener")


def main():
    """Main entry point."""
    # Load ETFs from CSV
    print("Loading ETFs from etf.csv...")
    etf_df = load_etfs_from_csv()
    print(f"Loaded {len(etf_df)} ETFs")

    # Calculate metrics
    print("\nCalculating ETF metrics...")
    records = calculate_etf_metrics(etf_df)

    print(f"\nSuccessfully calculated metrics for {len(records)} ETFs")

    # Preview results
    if records:
        print("\n=== Sample Results ===")
        for record in records[:5]:
            print(f"Ticker ID: {record['ticker_id']}")
            print(f"  Industry: {record['industry']}")
            print(f"  Ann Return: {record['ann_ret']}")
            print(f"  Ann Vol: {record['ann_vol']}")
            print(f"  Info Ratio: {record['information_ratio']}")
            print(f"  Beta: {record['beta']}")
            print(f"  Expense Ratio: {record['expense_ratio']}")
            print()

    # Uncomment to save to database
    upsert_etf_screener_data(records)

    return records
