"""Factor calculation tools for ticker analysis."""

from app.core.atlas.tools.responses import success_response, error_response
from typing import Optional, Any
import numpy as np
from app.core.calculations.factors.growth import GrowthFactors
from app.core.calculations.factors.value import ValueFactors
from app.core.calculations.factors.quality import QualityFactors
from app.core.calculations.factors.momentum import MomentumFactors
from app.core.calculations.factors.volatility import VolatilityFactors
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from datetime import datetime, timedelta
from app.utils.simulation_utils import get_end_date, filter_series_by_date
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator

# Sector to ETF mapping for sector-relative momentum
SECTOR_ETF_MAP = {
    'equity_sector_information_technology': 'XLK',
    'equity_sector_financials': 'XLF',
    'equity_sector_health_care': 'XLV',
    'equity_sector_consumer_discretionary': 'XLY',
    'equity_sector_communication_services': 'XLC',
    'equity_sector_industrials': 'XLI',
    'equity_sector_consumer_staples': 'XLP',
    'equity_sector_energy': 'XLE',
    'equity_sector_utilities': 'XLU',
    'equity_sector_real_estate': 'XLRE',
    'equity_sector_materials': 'XLB'
}


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
            end_date = get_end_date(_simulation_date)
            # Use 450 calendar days (~300 trading days) to ensure all metrics work
            # Reason: 12-month ex-1m needs 273 trading days, idio_momentum_log needs 273
            start_date = end_date - timedelta(days=450)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            # Get price data for ticker and SPY (and optionally sector ETF) in one bulk call
            tickers_to_fetch = [ticker, "SPY"]
            ohlcv_data = fetch_bulk_ohlcv_data_for_tickers(tickers_to_fetch, start_str, end_str)

            price_df = ohlcv_data.get(ticker)
            if price_df is None or price_df.empty:
                return error_response(f"No price data available for {ticker}")

            # Reason: adj_close accounts for dividends, use it for price series
            price_series = price_df['adj_close'] if 'adj_close' in price_df.columns else price_df['close']
            price_series = filter_series_by_date(price_series, _simulation_date)

            # Get SPY data for market-relative metrics
            spy_df = ohlcv_data.get("SPY")
            if spy_df is not None and not spy_df.empty:
                spy_prices = spy_df['adj_close'] if 'adj_close' in spy_df.columns else spy_df['close']
                spy_prices = filter_series_by_date(spy_prices, _simulation_date)
            else:
                spy_prices = None

            if factor == "momentum":
                # Get additional data for momentum calculations
                volume_series = price_df.get('volume', None)
                if volume_series is not None:
                    volume_series = filter_series_by_date(volume_series, _simulation_date)

                # Dividend data no longer needed - adj_close accounts for dividends
                # Reason: adj_close already incorporates dividend adjustments

                # Get sector ETF data for sector-relative momentum
                sector_prices = None
                try:
                    from app.db.core.db_config import MarketSession
                    from app.db.core.models.market_data_models import Ticker as TickerModel
                    with MarketSession() as session:
                        ticker_obj = session.query(TickerModel).filter(
                            TickerModel.ticker == ticker.upper()
                        ).first()
                        if ticker_obj and ticker_obj.sector:
                            sector_etf = SECTOR_ETF_MAP.get(ticker_obj.sector)
                            if sector_etf:
                                sector_data = fetch_bulk_ohlcv_data_for_tickers([sector_etf], start_str, end_str)
                                sector_df = sector_data.get(sector_etf)
                                if sector_df is not None and not sector_df.empty:
                                    sector_prices = sector_df['adj_close'] if 'adj_close' in sector_df.columns else sector_df['close']
                                    sector_prices = filter_series_by_date(sector_prices, _simulation_date)
                except Exception:
                    sector_prices = None

                result = MomentumFactors(
                    price_series=price_series,
                    volume_series=volume_series,
                    market_price_series=spy_prices,
                    sector_price_series=sector_prices,
                    dividends_series=None  # No longer needed with adj_close
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

if __name__ == "__main__":
    print(calculate_ticker_factors(ticker='AAL', factor='volatility'))

# Tool Schema Constants
CALCULATE_TICKER_FACTORS_DESCRIPTION = """Calculate quantitative factor metrics for stock analysis.

**FACTORS:**

1. **MOMENTUM** - Trend & relative strength (trend-following, timing)
   - r12_1/r6_1/r3_1: Academic momentum returns (t-X to t-1). Positive = outperforming
   - pct_from_52w_high: Distance from peak. Near 0 = strong, negative = weak
   - rsi: 0-100 oscillator. >70 overbought, <30 oversold
   - idio_momentum: Stock-specific momentum vs market

2. **VALUE** - Valuation metrics (finding undervalued stocks)
   - trailing_pe/forward_pe: Price/Earnings. Lower = cheaper
   - earnings_yield/fcf_yield: Yield ratios. Higher = more value
   - ev_to_ebitda: Enterprise multiple. Lower = cheaper
   - peg_ratio: PE/Growth. <1 = undervalued vs growth

3. **GROWTH** - Earnings & revenue trajectory (GARP, growth investing)
   - eps_growth_rate/eps_cagr: Historical earnings growth
   - forward_eps_growth: Analyst expectations
   - revenue_growth_rate/sales_ttm_yoy: Top-line growth

4. **QUALITY** - Financial health (avoiding distress, finding moats)
   - roic/roe: Capital efficiency. Higher = better
   - gross_profitability: Novy-Marx quality factor
   - altman_z_score: Bankruptcy risk. >3 safe, <1.8 distress
   - accruals_ratio: Earnings quality. Near 0 = cash-backed

5. **VOLATILITY** - Risk metrics (position sizing, risk management)
   - realized_vol_30d/90d/252d: Price volatility
   - beta_1yr: Market sensitivity. >1 = more volatile
   - max_drawdown_1yr: Largest peak-to-trough decline

Example: calculate_ticker_factors(ticker='AAPL', factor='momentum')"""

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
