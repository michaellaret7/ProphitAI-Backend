import pandas as pd
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from typing import Optional, List, Dict, Union, Any
from app.repositories.price_data import get_price_data_daily
from app.core.calculations.technical.indicators import TechnicalIndicators
from app.utils.time_utils import get_current_utc_time
from app.utils.tool_validator import ToolValidator
from app.utils.decorators.tool_validation import log_simulation_data_range
from datetime import datetime


def _convert_df_to_string(df: pd.DataFrame) -> str:
    """Convert DataFrame to string table representation.

    Args:
        df: DataFrame with datetime index and numeric columns

    Returns:
        String representation of the DataFrame as a formatted table.
        Example:
                        close     rsi_14
        date
        2023-09-08  178.4100  84.3159
        2023-09-15  174.9800  80.0157
        ...
    """
    if df.empty:
        return ""

    # Round values for clean display
    df_rounded = df.copy()
    for col in df_rounded.columns:
        if col == 'close':
            df_rounded[col] = df_rounded[col].round(2)
        else:
            df_rounded[col] = df_rounded[col].round(4)

    # Rename index to 'date' for clarity
    df_rounded.index.name = 'date'

    # Convert to string representation
    return df_rounded.to_string()


def _fetch_weekly_ohlcv(
    ticker: str,
    weeks_back: int = 52,
    _simulation_date: Optional[datetime] = None,
    week_ending: str = "W-FRI",
) -> pd.DataFrame:
    """Fetch daily OHLCV from DB and resample to weekly OHLCV.

    Args:
        ticker: Stock ticker symbol
        weeks_back: Number of weeks back to fetch data for
        _simulation_date: INTERNAL USE ONLY - For simulation mode.
                         If provided, uses this as cutoff date instead of current time.
        week_ending: pandas offset alias for week end (e.g., 'W-FRI', 'W-MON').

    Returns:
        DataFrame indexed by week end with columns: open, high, low, close, volume.
    """
    # Use simulation date if provided, otherwise use current UTC time
    end_dt = pd.Timestamp(_simulation_date).normalize() if _simulation_date else pd.Timestamp(get_current_utc_time()).normalize()
    start_dt = end_dt - pd.DateOffset(weeks=weeks_back)

    daily_df = get_price_data_daily(ticker, start_dt.to_pydatetime(), end_dt.to_pydatetime())
    if daily_df is None or daily_df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    daily_df = daily_df.copy()
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df = daily_df.set_index("date").sort_index()

    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    weekly_df = daily_df.resample(week_ending).apply(agg)
    weekly_df = weekly_df.dropna(subset=["open", "high", "low", "close"], how="any")
    return weekly_df


@log_simulation_data_range()
def run_technicals(
    ticker: str,
    indicators: List[str],
    weeks_back: int = 52,
    _simulation_date: Optional[datetime] = None,
) -> str:
    """Run specific technical indicators for a given ticker on weekly price data.

    Args:
        ticker: Stock ticker symbol
        indicators: List of indicator names to calculate. Available indicators:
            - 'rsi': Relative Strength Index (default period=14)
            - 'stoch': Stochastic Oscillator (%K and %D)
            - 'stoch_rsi': Stochastic RSI
            - 'macd': MACD line, Signal, and Histogram
            - 'bollinger_bands': Bollinger Bands (default period=20, std=2.0)
            - 'adx': Average Directional Index with +DI and -DI
            - 'williams_r': Williams %R (default period=14)
            - 'cci': Commodity Channel Index (default period=14)
            - 'atr': Average True Range (default period=14)
            - 'highs_lows': Rolling highest high and lowest low (default period=14)
            - 'ultimate_oscillator': Ultimate Oscillator
            - 'roc': Rate of Change (default period=10)
            - 'bull_bear_power': Elder's Bull and Bear Power
            - 'vwap': Volume Weighted Average Price
            - 'donchian_channels': Donchian Channels (default period=20)
            - 'keltner_channels': Keltner Channels (default period=20)
            - 'parabolic_sar': Parabolic SAR
            - 'moving_averages': Moving averages (SMA 5, 10, 26, 52)
        weeks_back: Number of weeks back to analyze (default 52)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents.
                         If provided, uses this as cutoff date instead of current time.

    Returns:
        YAML string with success status and indicator data as formatted tables. Format:
        {
            "success": true,
            "data": {
                "rsi": "            close     rsi_14\ndate\n2023-09-08  178.41  84.3159\n...",
                "adx": "            close     adx  plus_di  minus_di\ndate\n2023-09-08  178.41  25.67  20.50  15.30\n..."
            }
        }

    Example:
        >>> result = run_technicals('AAPL', ['adx', 'rsi'], weeks_back=26)
    """
    # Validate inputs
    v = ToolValidator()
    v.require_ticker('ticker', ticker)

    # Validate indicators parameter
    if not isinstance(indicators, list):
        v.errors.append(
            f"Invalid type for 'indicators': expected list, got {type(indicators).__name__}. "
            f"Example: indicators=['rsi', 'adx']"
        )
    elif len(indicators) == 0:
        v.errors.append(
            "Empty indicators list. Please provide at least one indicator. "
            "Example: indicators=['rsi', 'adx']"
        )
    elif not all(isinstance(ind, str) for ind in indicators):
        v.errors.append(
            "All indicators must be strings. "
            "Example: indicators=['rsi', 'adx']"
        )

    v.optional_numeric('weeks_back', weeks_back, default=52, min_val=1, positive_only=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    weeks_back = v.get('weeks_back')

    # Available indicators
    available_indicators = {
        'rsi', 'stoch', 'stoch_rsi', 'macd', 'bollinger_bands', 'adx',
        'williams_r', 'cci', 'atr', 'highs_lows', 'ultimate_oscillator',
        'roc', 'bull_bear_power', 'vwap', 'donchian_channels',
        'keltner_channels', 'parabolic_sar', 'moving_averages'
    }

    # Validate indicator names
    invalid_indicators = []
    for ind in indicators:
        if ind.lower().strip() not in available_indicators:
            invalid_indicators.append(ind)

    if invalid_indicators:
        return error_response(
            f"Unknown indicators: {', '.join(invalid_indicators)}. "
            f"Available indicators: {', '.join(sorted(available_indicators))}"
        )

    try:
        # Fetch weekly OHLCV data
        weekly_df = _fetch_weekly_ohlcv(ticker, weeks_back, _simulation_date)
        if weekly_df.empty:
            return error_response(f"No price data available for {ticker}")

        # Initialize technical indicators calculator
        tech = TechnicalIndicators(weekly_df)
        results: Dict[str, str] = {}

        # Map of indicator names to calculation functions
        indicator_map = {
            'rsi': lambda: tech.rsi(period=14).to_frame(name='rsi_14'),
            'stoch': lambda: tech.stoch(k_period=9, d_period=6),
            'stoch_rsi': lambda: tech.stoch_rsi(period=14).to_frame(name='stochrsi_14'),
            'macd': lambda: tech.macd(),
            'bollinger_bands': lambda: tech.bollinger_bands(period=20, num_std=2.0),
            'adx': lambda: tech.adx(period=14),
            'williams_r': lambda: tech.williams_r(period=14).to_frame(name='williams_r_14'),
            'cci': lambda: tech.cci(period=14).to_frame(name='cci_14'),
            'atr': lambda: tech.atr(period=14).to_frame(name='atr_14'),
            'highs_lows': lambda: tech.highs_lows(period=14),
            'ultimate_oscillator': lambda: tech.ultimate_oscillator().to_frame(name='ultimate_oscillator'),
            'roc': lambda: tech.roc(period=10).to_frame(name='roc_10'),
            'bull_bear_power': lambda: tech.bull_bear_power(period=13),
            'vwap': lambda: tech.vwap().to_frame(name='vwap'),
            'donchian_channels': lambda: tech.donchian_channels(period=20),
            'keltner_channels': lambda: tech.keltner_channels(period=20, multiplier=2.0),
            'parabolic_sar': lambda: tech.parabolic_sar().to_frame(name='psar'),
            'moving_averages': lambda: tech.moving_averages([5, 10, 26, 52], ma_type='sma'),
        }

        # Calculate requested indicators
        for indicator in indicators:
            indicator_lower = indicator.lower().strip()

            # Calculate the indicator
            indicator_df = indicator_map[indicator_lower]()

            # Add close price as first column for context (if not already present)
            if isinstance(indicator_df, pd.DataFrame) and 'close' not in indicator_df.columns:
                indicator_df.insert(0, 'close', weekly_df['close'])
            elif isinstance(indicator_df, pd.Series):
                # Convert Series to DataFrame with close price
                temp_df = pd.DataFrame({'close': weekly_df['close']})
                temp_df[indicator_df.name] = indicator_df
                indicator_df = temp_df

            # Drop rows where all indicator columns (excluding 'close') are NaN
            # This allows keeping rows where some indicators are NaN but others have values
            indicator_cols = [col for col in indicator_df.columns if col != 'close']
            if indicator_cols:
                # Drop rows where all indicator values are NaN (keep partial data)
                indicator_df = indicator_df.dropna(subset=indicator_cols, how='all')
            else:
                # If there's only the close column, keep all rows
                pass

            # Convert to string table format
            results[indicator_lower] = _convert_df_to_string(indicator_df)

        return success_response(results)

    except Exception as e:
        return error_response(f"Failed to calculate technical indicators for {ticker}: {str(e)}")


# Tool schema for agent registration
TECHNICALS_DESCRIPTION = (
    "Run technical indicators on weekly price data for a given ticker. "
    "Returns time series data as formatted tables with dates (index), close prices, and calculated indicator values. "
    "All data is resampled to weekly frequency (Friday close). "
    "Each indicator returns a table string with date as the index and columns for close price and indicator values. "
    "\n\n"
    "Available indicators:\n"
    "- rsi: Relative Strength Index (14-period)\n"
    "- stoch: Stochastic Oscillator (%K and %D, 9/6 periods)\n"
    "- stoch_rsi: Stochastic RSI (14-period)\n"
    "- macd: MACD line, Signal, and Histogram\n"
    "- bollinger_bands: Bollinger Bands (20-period, 2 std dev)\n"
    "- adx: Average Directional Index with +DI and -DI (14-period)\n"
    "- williams_r: Williams %R (14-period)\n"
    "- cci: Commodity Channel Index (14-period)\n"
    "- atr: Average True Range (14-period)\n"
    "- highs_lows: Rolling highest high and lowest low (14-period)\n"
    "- ultimate_oscillator: Ultimate Oscillator\n"
    "- roc: Rate of Change (10-period)\n"
    "- bull_bear_power: Elder's Bull and Bear Power (13-period)\n"
    "- vwap: Volume Weighted Average Price\n"
    "- donchian_channels: Donchian Channels (20-period)\n"
    "- keltner_channels: Keltner Channels (20-period, 2x multiplier)\n"
    "- parabolic_sar: Parabolic SAR\n"
    "- moving_averages: Simple Moving Averages (5, 10, 26, 52 weeks)\n"
    "\n"
    "Returns YAML with structure: {success: true, data: {indicator_name: '<formatted table string>'}}"
)

TECHNICALS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT')"
        },
        "indicators": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "List of technical indicators to calculate. Choose from: "
                "rsi, stoch, stoch_rsi, macd, bollinger_bands, adx, williams_r, "
                "cci, atr, highs_lows, ultimate_oscillator, roc, bull_bear_power, "
                "vwap, donchian_channels, keltner_channels, parabolic_sar, moving_averages"
            )
        },
        "weeks_back": {
            "type": "integer",
            "default": 52,
            "description": "Number of weeks of historical data to analyze (default: 52 weeks = 1 year)"
        }
    },
    "required": ["ticker", "indicators"],
    "additionalProperties": False
}

TECHNICALS_TOOL = {
    "name": "run_technicals",
    "description": TECHNICALS_DESCRIPTION,
    "parameters": TECHNICALS_PARAMETERS,
    "function": run_technicals,
}


if __name__ == "__main__":
    results = run_technicals("AAPL", indicators=['bollinger_bands', 'bull_bear_power', 'moving_averages'], weeks_back=20, _simulation_date=datetime(2024, 1, 1))
    print(results)