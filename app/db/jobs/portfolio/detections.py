from typing import Tuple, Dict, Any
from app.db.jobs.portfolio.utils import classify_and_add_tickers
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_current_utc_time
import pandas as pd
from app.db.core.db_config import MarketSession
from datetime import datetime

DRIFT_THRESHOLD = 0.00005 # -> 5%
DRAWDOWN_THRESHOLD = -0.10 # -> 10%

def detect_allocation_drift(positions: Dict[str, float], preferences: Dict[str, float], market_session: MarketSession) -> Tuple[bool, Dict[str, dict]]:
    """
    Detect if portfolio allocations have drifted from target preferences.

    Returns:
        Tuple containing:
            - has_drift: True if any sector has drifted beyond threshold
            - drifted_sectors: Dict of sectors with drift details including
                current_allocation, target_allocation, and drift amount
    """
    allocations = classify_and_add_tickers(positions, market_session)

    drifted_sectors = {}
    for sector, allocation in allocations.items():
        preference = preferences.get(sector, 0.0)
        diff = allocation - preference
        if abs(diff) > DRIFT_THRESHOLD:
            drifted_sectors[sector] = {
                "current_allocation": allocation,
                "target_allocation": preference,
                "drift": diff
            }

    has_drift = len(drifted_sectors) > 0

    return has_drift, drifted_sectors

def detect_drawdowns(positions: Dict[str, float], portfolio_created_date: datetime) -> Dict[str, Any]:
    """
    Detect positions currently in drawdown below threshold.
    Returns only flagged positions that breach the threshold.
    """
    price_data = fetch_bulk_ohlcv_data_for_tickers(
        tickers=positions.keys(),
        start_date_str=portfolio_created_date.strftime('%Y-%m-%d'),
        end_date_str=get_current_utc_time().strftime('%Y-%m-%d'),
        frequency='daily',
        returns=True
    )
    
    returns_df = pd.DataFrame()

    for ticker, data in price_data.items():
        returns_df[ticker] = data['returns']
        
    returns_df = returns_df.dropna()
    
    # Cumulative wealth index
    cumulative_wealth = (1 + returns_df).cumprod()
    
    # High water mark and drawdown series
    high_water_mark = cumulative_wealth.cummax()
    drawdown_series = (cumulative_wealth - high_water_mark) / high_water_mark
    
    # Current and max drawdowns
    current_drawdowns = drawdown_series.iloc[-1]
    max_drawdowns = drawdown_series.min()
    
    # Only flagged positions (convert to native Python floats)
    flagged_positions = {
        ticker: {
            'current_drawdown': float(current_drawdowns[ticker]),
            'max_drawdown': float(max_drawdowns[ticker]),
            'peak_date': cumulative_wealth[ticker].idxmax().strftime('%Y-%m-%d'),
        }
        for ticker in current_drawdowns.index
        if current_drawdowns[ticker] < DRAWDOWN_THRESHOLD
    }
    
    return {
        'flagged_positions': flagged_positions,
        'needs_reevaluation': len(flagged_positions) > 0,
        'threshold': DRAWDOWN_THRESHOLD
    }