from typing import Dict, List
import pandas as pd
from datetime import datetime, timedelta
from app.repositories.prophit_alts_data import get_fund_final_positions
from app.utils.time_utils import get_current_utc_time
from app.repositories.price_data import get_price_data_daily
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.core.config import DEFAULT_LOOKBACK_1Y


class AltsCorrelationService:
    """
    Service to compute correlation matrix for alts fund holdings.

    Uses price returns to calculate pairwise correlations between
    all positions in the fund portfolio.

    Args:
        fund_name: Name of the fund (e.g., "consumer_staples_fund")
    """

    def __init__(self, fund_name: str):
        self.fund_name = fund_name

    def get_correlation_matrix(self) -> Dict[str, any]:
        """
        Calculate correlation matrix for fund holdings.

        Returns:
            Dict with correlation data in format:
            {
                "matrix": {...},  # Full correlation matrix
                "pairs": [...]    # Pairwise correlations
            }
        """
        # Get fund positions from database
        positions = get_fund_final_positions(fund_name=self.fund_name)

        if not positions:
            raise ValueError(f"No positions found for fund: {self.fund_name}")

        # Extract tickers
        tickers = [p.get('ticker_name') for p in positions if p.get('ticker_name')]

        if len(tickers) < 2:
            raise ValueError(f"Need at least 2 tickers to compute correlation matrix, found {len(tickers)}")

        # Fetch price data for all tickers (using UTC time)
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=DEFAULT_LOOKBACK_1Y)

        ticker_returns: Dict[str, pd.Series] = {}
        failed_tickers = []

        for ticker in tickers:
            try:
                df = get_price_data_daily(ticker, start_date, end_date)
                if df is None or df.empty:
                    failed_tickers.append(ticker)
                    continue

                df['date'] = pd.to_datetime(df['date'])
                close = df.set_index('date')['close']
                returns = ReturnsCalculator.daily_price_returns(close)

                if not returns.empty:
                    ticker_returns[ticker] = returns
                else:
                    failed_tickers.append(ticker)
            except Exception as e:
                failed_tickers.append(ticker)
                print(f"Error fetching/processing {ticker}: {e}")

        if len(ticker_returns) < 2:
            raise ValueError(
                f"Insufficient data to compute correlations. "
                f"Successfully fetched: {len(ticker_returns)}, "
                f"Failed: {failed_tickers}"
            )

        # Build returns dataframe
        returns_df = pd.concat(ticker_returns, axis=1)

        # Calculate correlation matrix
        corr_matrix = CorrelationAnalysis.correlation_matrix(returns_df)

        if corr_matrix is None or corr_matrix.empty:
            raise ValueError("Failed to compute correlation matrix")

        # Round to 3 decimals
        corr_matrix = corr_matrix.round(3)

        # Build full matrix output
        matrix_dict = {}
        for ticker in corr_matrix.index:
            matrix_dict[ticker] = corr_matrix.loc[ticker].to_dict()

        # Build pairwise correlations (upper triangle only)
        pairs = []
        tickers_ordered = list(corr_matrix.columns)
        for i, ticker1 in enumerate(tickers_ordered):
            for j in range(i + 1, len(tickers_ordered)):
                ticker2 = tickers_ordered[j]
                corr_value = float(corr_matrix.loc[ticker1, ticker2])
                pairs.append({
                    "ticker1": ticker1,
                    "ticker2": ticker2,
                    "correlation": corr_value
                })

        # Sort pairs by absolute correlation (highest first)
        pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)

        return {
            "matrix": matrix_dict,
            "pairs": pairs,
            "metadata": {
                "total_tickers": len(tickers_ordered),
                "failed_tickers": failed_tickers if failed_tickers else None,
                "lookback_days": DEFAULT_LOOKBACK_1Y,
                "date_range": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            }
        }


if __name__ == "__main__":
    fund_name = "consumer_staples_fund"
    service = AltsCorrelationService(fund_name)
    result = service.get_correlation_matrix()
    print("Matrix:", result['matrix'])
    print("\nTop 10 Correlations:", result['pairs'][:10])
    print("\nMetadata:", result['metadata'])