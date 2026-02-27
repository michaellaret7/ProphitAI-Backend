"""Service for technical indicators calculation."""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_current_utc_time
from app.core.calculations.technicals.momentum import calc_rsi, calc_macd, calc_adx, calc_roc
from app.core.calculations.technicals.volatility import (
    calc_bollinger_bands, calc_atr, calc_donchian_channels, calc_keltner_channels,
)
from app.core.calculations.technicals.volume import calc_vwap, calc_obv, calc_cmf, calc_mfi
from app.core.calculations.technicals.trend import calc_sma, calc_ema


class TechnicalIndicatorService:
    """Service for calculating technical indicators for a ticker."""

    def __init__(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        indicators: Optional[List[str]] = None,
    ):
        """
        Initialize the technical indicator service.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            indicators: List of indicator names to calculate. If None, returns all.
        """
        self.ticker = self._validate_ticker(ticker)
        self.start_date = start_date
        self.end_date = end_date
        self._validate_dates()
        self.indicators = indicators or []
        self._ohlcv_data: Optional[pd.DataFrame] = None

    @staticmethod
    def _validate_ticker(ticker: str) -> str:
        """Validate ticker symbol format."""
        if not ticker or not ticker.strip():
            raise ValueError("Ticker symbol cannot be empty")

        ticker = ticker.strip().upper()

        if not ticker.replace('.', '').replace('-', '').isalpha():
            raise ValueError(f"Invalid ticker symbol: {ticker}")

        if len(ticker) > 10:
            raise ValueError(f"Ticker symbol too long: {ticker}")

        return ticker

    def _validate_dates(self) -> None:
        """Validate date format and logic."""
        try:
            start = datetime.strptime(self.start_date, '%Y-%m-%d')
            end = datetime.strptime(self.end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD format")

        if start >= end:
            raise ValueError("start_date must be before end_date")

        if end.date() > get_current_utc_time().date():
            raise ValueError("end_date cannot be in the future")

        if (end - start).days > 3650:
            raise ValueError("Date range cannot exceed 10 years")

    def _fetch_ohlcv_data(self) -> pd.DataFrame:
        """Fetch OHLCV data for the ticker."""
        if self._ohlcv_data is not None:
            return self._ohlcv_data

        data_map = fetch_bulk_ohlcv_data_for_tickers(
            tickers=[self.ticker],
            start_date_str=self.start_date,
            end_date_str=self.end_date,
        )

        if self.ticker not in data_map or data_map[self.ticker].empty:
            raise ValueError(f"No OHLCV data found for ticker {self.ticker}")

        self._ohlcv_data = data_map[self.ticker]
        return self._ohlcv_data

    def calculate_indicators(self) -> Dict[str, Any]:
        """
        Calculate technical indicators for the ticker.

        Returns:
            Dictionary with indicator data as time series
        """
        ohlcv_df = self._fetch_ohlcv_data()
        close = ohlcv_df['adj_close']
        high = ohlcv_df['high']
        low = ohlcv_df['low']
        volume = ohlcv_df['volume']

        # Define available indicators
        available_indicators = {
            "rsi": lambda: calc_rsi(close, window=14),
            "macd": lambda: self._calc_macd(close),
            "adx": lambda: calc_adx(high, low, close, window=14),
            "roc": lambda: calc_roc(close),
            "bollinger_bands": lambda: self._calc_bollinger(close),
            "atr": lambda: calc_atr(high, low, close, window=14),
            "donchian_channels": lambda: self._calc_donchian(high, low),
            "keltner_channels": lambda: self._calc_keltner(high, low, close),
            "vwap": lambda: calc_vwap(high, low, close, volume),
            "obv": lambda: calc_obv(close, volume),
            "cmf": lambda: calc_cmf(high, low, close, volume),
            "mfi": lambda: calc_mfi(high, low, close, volume),
            "moving_averages": lambda: self._calc_moving_averages(close),
        }

        result = {}

        if self.indicators:
            for indicator in self.indicators:
                if indicator not in available_indicators:
                    raise ValueError(
                        f"Unknown indicator: {indicator}. "
                        f"Available: {list(available_indicators.keys())}"
                    )
                result[indicator] = self._format_indicator_output(
                    available_indicators[indicator]()
                )
        else:
            for name, calc_func in available_indicators.items():
                try:
                    result[name] = self._format_indicator_output(calc_func())
                except Exception as e:
                    result[name] = {"error": str(e)}

        return result

    # ================================
    # --> Helper funcs
    # ================================

    @staticmethod
    def _calc_macd(close: pd.Series) -> pd.DataFrame:
        """Wrap calc_macd tuple into a DataFrame for formatting."""
        macd_line, signal, histogram = calc_macd(close)
        return pd.DataFrame({"macd": macd_line, "signal": signal, "hist": histogram})

    @staticmethod
    def _calc_bollinger(close: pd.Series) -> pd.DataFrame:
        """Wrap calc_bollinger_bands tuple into a DataFrame."""
        upper, middle, lower = calc_bollinger_bands(close)
        return pd.DataFrame({"bb_upper": upper, "bb_middle": middle, "bb_lower": lower})

    @staticmethod
    def _calc_donchian(high: pd.Series, low: pd.Series) -> pd.DataFrame:
        """Wrap calc_donchian_channels tuple into a DataFrame."""
        upper, middle, lower = calc_donchian_channels(high, low)
        return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})

    @staticmethod
    def _calc_keltner(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
        """Wrap calc_keltner_channels tuple into a DataFrame."""
        upper, middle, lower = calc_keltner_channels(high, low, close)
        return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})

    @staticmethod
    def _calc_moving_averages(close: pd.Series) -> pd.DataFrame:
        """Calculate SMA for standard lookback windows."""
        return pd.DataFrame({
            f"sma_{w}": calc_sma(close, window=w)
            for w in [20, 50, 100, 200]
        })

    def _format_indicator_output(
        self, data: pd.Series | pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Format indicator output as a list of dictionaries for API response.

        Args:
            data: Pandas Series or DataFrame with date index

        Returns:
            List of dictionaries with date and values
        """
        if isinstance(data, pd.Series):
            return [
                {"date": str(date.date()), "value": float(value) if pd.notna(value) else None}
                for date, value in data.items()
            ]
        elif isinstance(data, pd.DataFrame):
            result = []
            for date, row in data.iterrows():
                entry = {"date": str(date.date())}
                for col, value in row.items():
                    entry[col] = float(value) if pd.notna(value) else None
                result.append(entry)
            return result
        else:
            return []
