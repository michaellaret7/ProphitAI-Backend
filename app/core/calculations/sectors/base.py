"""Base functions for sector/industry/sub-industry calculations following DRY principles."""

from typing import Literal, List, Callable, Optional
from functools import wraps
import pandas as pd
from app.db.core.models.market_data_models import Ticker
from app.db.core.db_config import MarketSession
from app.utils.decorators.database import with_session
from app.core.calculations.factors.growth import GrowthFactors
from app.core.calculations.factors.value import ValueFactors
from app.core.calculations.factors.momentum import MomentumFactors
from app.core.calculations.factors.quality import QualityFactors
from app.core.calculations.factors.volatility import VolatilityFactors
from app.core.calculations.core.helpers import winsorize_series
from datetime import datetime, timedelta
from app.utils.time_utils import get_current_utc_time

GroupingLevel = Literal["sector", "industry", "sub_industry"]

@with_session('market')
def get_tickers_by_grouping(grouping_value: str, grouping_level: GroupingLevel, session=None) -> List[str]:
    """Get tickers for a given grouping level and value.
    
    Args:
        grouping_value: The value to filter by (e.g., "technology", "software", "systems_software")
        grouping_level: The level to group by ("sector", "industry", or "sub_industry")
    
    Returns:
        List of ticker symbols
    """
    # Normalize the grouping value
    grouping_value = grouping_value.lower()
    
    # Query based on grouping level
    if grouping_level == "sector":
        tickers = session.query(Ticker).filter(Ticker.sector == grouping_value).all()
    elif grouping_level == "industry":
        tickers = session.query(Ticker).filter(Ticker.industry == grouping_value).all()
    elif grouping_level == "sub_industry":
        tickers = session.query(Ticker).filter(Ticker.sub_industry == grouping_value).all()
    else:
        raise ValueError(f"Invalid grouping level: {grouping_level}")
    
    # Extract ticker symbols
    tickers_list = [ticker.ticker for ticker in tickers]
    return tickers_list

# ------------------------- Decorators ------------------------- #
def winsorized_median(func: Callable[..., pd.DataFrame]) -> Callable[..., pd.Series]:
    """Decorator that winsorizes DataFrame results and returns the median.
    
    Expects the wrapped function to return a DataFrame with numeric columns.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> pd.Series:
        # Get the DataFrame from the original function
        factor_data = func(*args, **kwargs)
        
        # Winsorize each column to handle extreme outliers
        winsorized_data = factor_data.copy()
        for col in winsorized_data.columns:
            winsorized_data[col] = winsorize_series(winsorized_data[col])
        
        # Return median of winsorized data
        return winsorized_data.median()
    
    return wrapper

# ------------------------- Function Factory ------------------------- #
def create_factor_calculator(factor_type: str):
    """Factory to create factor calculation functions for any grouping level.

    Args:
        factor_type: One of 'growth', 'value', 'momentum', 'quality', 'volatility'

    Returns:
        Function that calculates factors for a given grouping
    """
    def calculator(grouping_value: str, grouping_level: GroupingLevel, as_of_date: Optional[datetime] = None) -> pd.Series:
        """Calculate winsorized median factors for a grouping."""
        tickers = get_tickers_by_grouping(grouping_value, grouping_level)

        if factor_type == 'growth':
            return calc_growth_factors(tickers, as_of_date=as_of_date)
        elif factor_type == 'value':
            return calc_value_factors(tickers, as_of_date=as_of_date)
        elif factor_type == 'momentum':
            return calc_momentum_factors(tickers)
        elif factor_type == 'quality':
            return calc_quality_factors(tickers, as_of_date=as_of_date)
        elif factor_type == 'volatility':
            return calc_volatility_factors(tickers)
        else:
            raise ValueError(f"Unknown factor type: {factor_type}")

    return calculator

# ------------------------- Functions ------------------------- #
@winsorized_median
def calc_growth_factors(tickers: List[str], as_of_date: Optional[datetime] = None) -> pd.DataFrame:
    """Calculate winsorized median growth factors for a list of tickers.

    Args:
        tickers: List of ticker symbols
        as_of_date: Optional as-of date for simulation mode

    Returns:
        Series with winsorized median of each growth factor
    """
    return GrowthFactors.calc_all_bulk(tickers, as_of_date=as_of_date)

@winsorized_median
def calc_value_factors(tickers: List[str], as_of_date: Optional[datetime] = None) -> pd.DataFrame:
    """Calculate winsorized median value factors for a list of tickers.

    Args:
        tickers: List of ticker symbols
        as_of_date: Optional as-of date for simulation mode

    Returns:
        Series with winsorized median of each value factor
    """
    return ValueFactors.calc_all_bulk(tickers, as_of_date=as_of_date)

@winsorized_median
def calc_momentum_factors(tickers: List[str]) -> pd.DataFrame:
    """Calculate winsorized median momentum factors for a list of tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        Series with winsorized median of each momentum factor
    """
    # Use last 3 years of data for momentum calculations (industry standard)
    from app.core.calculations.core.config import DEFAULT_LOOKBACK_LONG
    end_date = get_current_utc_time()
    start_date = end_date - timedelta(days=int(DEFAULT_LOOKBACK_LONG * 365 / 252))
    return MomentumFactors.calc_all_bulk(tickers, start_date, end_date)

@winsorized_median
def calc_quality_factors(tickers: List[str], as_of_date: Optional[datetime] = None) -> pd.DataFrame:
    """Calculate winsorized median quality factors for a list of tickers.

    Args:
        tickers: List of ticker symbols
        as_of_date: Optional as-of date for simulation mode

    Returns:
        Series with winsorized median of each quality factor
    """
    return QualityFactors.calc_all_bulk(tickers, as_of_date=as_of_date)

@winsorized_median
def calc_volatility_factors(tickers: List[str]) -> pd.DataFrame:
    """Calculate winsorized median volatility factors for a list of tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        Series with winsorized median of each volatility factor
    """
    # Use last 3 years of data for volatility calculations (industry standard)
    from app.core.calculations.core.config import DEFAULT_LOOKBACK_LONG
    end_date = get_current_utc_time()
    start_date = end_date - timedelta(days=int(DEFAULT_LOOKBACK_LONG * 365 / 252))
    return VolatilityFactors.calc_all_bulk(tickers, start_date, end_date)
