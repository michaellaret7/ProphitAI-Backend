"""Service for technical indicators and pivot points calculation."""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timedelta

from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.technical.indicators import TechnicalIndicators
from app.core.calculations.technical.pivot_points import PivotPoints
from app.utils.time_utils import get_current_utc_time


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
        tech = TechnicalIndicators(ohlcv_df)

        result = {}

        # Define available indicators with their calculation methods
        available_indicators = {
            "rsi": lambda: tech.rsi(period=14),
            "macd": lambda: tech.macd(),
            "bollinger_bands": lambda: tech.bollinger_bands(),
            "stoch": lambda: tech.stoch(),
            "stoch_rsi": lambda: tech.stoch_rsi(),
            "adx": lambda: tech.adx(),
            "williams_r": lambda: tech.williams_r(),
            "cci": lambda: tech.cci(),
            "atr": lambda: tech.atr(),
            "ultimate_oscillator": lambda: tech.ultimate_oscillator(),
            "roc": lambda: tech.roc(),
            "bull_bear_power": lambda: tech.bull_bear_power(),
            "vwap": lambda: tech.vwap(),
            "donchian_channels": lambda: tech.donchian_channels(),
            "keltner_channels": lambda: tech.keltner_channels(),
            "parabolic_sar": lambda: tech.parabolic_sar(),
            "moving_averages": lambda: tech.moving_averages(
                lookbacks=[20, 50, 100, 200], ma_type="sma"
            ),
        }

        # If specific indicators requested, calculate only those
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
            # Calculate all indicators
            for name, calc_func in available_indicators.items():
                try:
                    result[name] = self._format_indicator_output(calc_func())
                except Exception as e:
                    # Some indicators might fail (e.g., VWAP without volume)
                    result[name] = {"error": str(e)}

        return result

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
            # Single value series
            return [
                {"date": str(date.date()), "value": float(value) if pd.notna(value) else None}
                for date, value in data.items()
            ]
        elif isinstance(data, pd.DataFrame):
            # Multiple columns (e.g., MACD, Bollinger Bands)
            result = []
            for date, row in data.iterrows():
                entry = {"date": str(date.date())}
                for col, value in row.items():
                    entry[col] = float(value) if pd.notna(value) else None
                result.append(entry)
            return result
        else:
            return []


class PivotPointService:
    """Service for calculating pivot points for a ticker."""

    def __init__(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        pivot_type: str = "classic",
    ):
        """
        Initialize the pivot point service.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            pivot_type: Type of pivot points (classic, fibonacci, camarilla, woodie, demark)
        """
        self.ticker = self._validate_ticker(ticker)
        self.start_date = start_date
        self.end_date = end_date
        self._validate_dates()
        self.pivot_type = pivot_type.lower()
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

    def calculate_pivot_points(self) -> List[Dict[str, Any]]:
        """
        Calculate pivot points for the ticker.

        Returns:
            List of dictionaries with pivot point data
        """
        ohlcv_df = self._fetch_ohlcv_data()
        pivot = PivotPoints(ohlcv_df)

        # Map pivot types to calculation methods
        pivot_methods = {
            "classic": pivot.classic,
            "fibonacci": pivot.fibonacci,
            "camarilla": pivot.camarilla,
            "woodie": pivot.woodie,
            "demark": pivot.demark,
        }

        if self.pivot_type not in pivot_methods:
            raise ValueError(
                f"Unknown pivot type: {self.pivot_type}. "
                f"Available: {list(pivot_methods.keys())}"
            )

        pivot_df = pivot_methods[self.pivot_type]()

        # Format output
        result = []
        for date, row in pivot_df.iterrows():
            entry = {"date": str(date.date())}
            for col, value in row.items():
                entry[col] = float(value) if pd.notna(value) else None
            result.append(entry)

        return result
