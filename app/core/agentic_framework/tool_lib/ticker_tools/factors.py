from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from typing import Optional, Dict, Any
import numpy as np
from app.core.calculations.factors.growth import GrowthFactors
from app.core.calculations.factors.value import ValueFactors
from app.core.calculations.factors.quality import QualityFactors
from app.core.calculations.factors.momentum import MomentumFactors
from app.core.calculations.factors.volatility import VolatilityFactors
from app.core.calculations.core import DataService
from datetime import datetime, timedelta
from app.utils.simulation_utils import get_end_date, filter_series_by_date
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator


def _convert_numpy_to_python(obj: Any) -> Any:
    """Recursively convert NumPy types to native Python types for YAML serialization.

    Args:
        obj: Object that may contain NumPy types

    Returns:
        Object with NumPy types converted to Python types
    """
    if isinstance(obj, dict):
        return {key: _convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    else:
        return obj

@log_simulation_data_range()
def calculate_ticker_factors(ticker: str, factor: str, _simulation_date: Optional[datetime] = None) -> str:
    """Calculate all factor metrics for a given ticker and factor type.

    Args:
        ticker: Stock ticker symbol
        factor: Factor type to calculate
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents
    """
    # Validate inputs
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.require_enum('factor', factor, ['growth', 'value', 'quality', 'momentum', 'volatility'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values (ticker is already uppercased by validator)
    ticker = v.get('ticker')
    factor = v.get('factor')

    try:
        # Growth, Value, and Quality factors take ticker string directly
        if factor in ["growth", "value", "quality"]:
            if factor == "growth":
                result = GrowthFactors(ticker, as_of_date=_simulation_date).calc_all()
            elif factor == "value":
                result = ValueFactors(ticker, as_of_date=_simulation_date).calc_all()
            else:  # quality
                result = QualityFactors(ticker, as_of_date=_simulation_date).calc_all()

            # Convert NumPy types to Python types for YAML serialization
            result = _convert_numpy_to_python(result)
            return success_response(result)

        # Momentum and Volatility factors need price series
        elif factor in ["momentum", "volatility"]:
            ds = DataService()
            end_date = get_end_date(_simulation_date)
            start_date = end_date - timedelta(days=365)  # ~1 year of data

            # Get price data for ticker (and SPY for market-relative metrics)
            price_data = ds.get_price_data(ticker, start_date, end_date)
            if price_data is None or price_data.frame.empty:
                return error_response(f"No price data available for {ticker}")

            price_series = price_data.frame['close']
            price_series = filter_series_by_date(price_series, _simulation_date)

            # Get SPY data for both momentum and volatility
            spy_data = ds.get_price_data("SPY", start_date, end_date)
            spy_prices = spy_data.frame['close'] if spy_data and not spy_data.frame.empty else None
            spy_prices = filter_series_by_date(spy_prices, _simulation_date)

            if factor == "momentum":
                # Get additional data for momentum calculations
                volume_series = price_data.frame.get('volume', None)
                volume_series = filter_series_by_date(volume_series, _simulation_date)

                # Get dividends if available
                try:
                    divs = ds.get_dividends(ticker, start_date, end_date).series
                    divs = filter_series_by_date(divs, _simulation_date)
                    divs = divs.reindex(price_series.index).fillna(0.0)
                except Exception:
                    divs = None

                result = MomentumFactors(
                    price_series=price_series,
                    volume_series=volume_series,
                    market_price_series=spy_prices,
                    dividends_series=divs
                ).calc_all()
            else:  # volatility
                result = VolatilityFactors(price_series, spy_price_series=spy_prices).calc_all()

            # Convert NumPy types to Python types for YAML serialization
            result = _convert_numpy_to_python(result)
            
            return success_response(result)

        else:
            return error_response(f"Unknown factor: {factor}")
    except Exception as e:
        return error_response(f"Failed to calculate {factor} factors for {ticker}: {str(e)}")


# Tool Schema Constants
CALCULATE_TICKER_FACTORS_DESCRIPTION = (
    "Calculate factor metrics for a given ticker and factor type. Can calculate growth, value, momentum, quality, or volatility factors.\n\n"
    "Example: calculate_ticker_factors(ticker='KO', factor='growth')"
)

CALCULATE_TICKER_FACTORS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ticker symbol to calculate factors for. For example, 'AAPL', 'MSFT', 'KO', etc.",
        },
        "factor": {
            "type": "string",
            "description": "The factor type to calculate. Options are 'growth', 'value', 'momentum', 'quality', or 'volatility'. 'all' DOES NOT EXIST FOR THIS TOOL",
            "enum": ["growth", "value", "momentum", "quality", "volatility"]
        },
    },
    "required": ["ticker", "factor"],
}

CALCULATE_TICKER_FACTORS_TOOL = {
    "name": "calculate_ticker_factors",
    "description": CALCULATE_TICKER_FACTORS_DESCRIPTION,
    "parameters": CALCULATE_TICKER_FACTORS_PARAMETERS,
    "function": calculate_ticker_factors,
}