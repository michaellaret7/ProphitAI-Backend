"""Service layer for macro data endpoints."""

from typing import Dict, Any, Optional
from datetime import date

from app.repositories.macro import (
    get_commodity_prices,
    get_government_bond_rates,
    get_economic_indicators,
    get_economic_calendar,
)


class CommodityPriceService:
    """Service for fetching and formatting commodity price data."""

    def __init__(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the commodity price service.

        Args:
            symbol: Commodity symbol (e.g., "GCUSD" for gold)
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.symbol = self._validate_symbol(symbol)
        self.start_date = self._parse_date(start_date) if start_date else None
        self.end_date = self._parse_date(end_date) if end_date else None

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        """Validate commodity symbol format."""
        if not symbol or not symbol.strip():
            raise ValueError("Commodity symbol cannot be empty")

        symbol = symbol.strip().upper()

        # Reason: Commodity symbols can contain letters and sometimes numbers
        if not all(c.isalnum() for c in symbol):
            raise ValueError(f"Invalid commodity symbol: {symbol}")

        return symbol

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """
        Parse date string to date object.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            date object

        Raises:
            ValueError: If date format is invalid
        """
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD") from e

    def get_prices(self) -> Dict[str, Any]:
        """
        Fetch commodity price data.

        Returns:
            Dict containing payload (OHLCV data) and counts for response envelope

        Raises:
            ValueError: If no price data found for symbol
        """
        # Fetch data from repository
        df = get_commodity_prices(
            symbol=self.symbol,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        if df.empty:
            raise ValueError(f"No price data found for commodity: {self.symbol}")

        # Transform DataFrame to API response format
        data = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "open": float(row["open"]) if row["open"] is not None else None,
                "high": float(row["high"]) if row["high"] is not None else None,
                "low": float(row["low"]) if row["low"] is not None else None,
                "close": float(row["close"]) if row["close"] is not None else None,
                "volume": float(row["volume"]) if row["volume"] is not None else None,
            }
            for _, row in df.iterrows()
        ]

        payload = {
            "symbol": self.symbol,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        # Build counts metadata
        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}


class GovernmentBondRatesService:
    """Service for fetching and formatting government bond rates (yield curve) data."""

    def __init__(
        self,
        country: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the government bond rates service.

        Args:
            country: Country code - 2-letter (e.g., "ES" for Spain) or 3-letter (e.g., "USA" for United States)
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.country = self._validate_country(country)
        self.start_date = self._parse_date(start_date) if start_date else None
        self.end_date = self._parse_date(end_date) if end_date else None

    @staticmethod
    def _validate_country(country: str) -> str:
        """Validate country code format."""
        if not country or not country.strip():
            raise ValueError("Country code cannot be empty")

        country = country.strip().upper()

        # Reason: Accept both ISO 3166-1 alpha-2 (2-letter) and alpha-3 (3-letter) codes
        # Database has mixed formats: most are 2-letter (DE, ES, FR) but USA is 3-letter
        if not country.isalpha() or not (2 <= len(country) <= 3):
            raise ValueError(f"Invalid country code: {country}. Expected 2 or 3-letter ISO code")

        return country

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """
        Parse date string to date object.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            date object

        Raises:
            ValueError: If date format is invalid
        """
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD") from e

    def get_rates(self) -> Dict[str, Any]:
        """
        Fetch government bond rates data.

        Returns:
            Dict containing payload (yield curve data) and counts for response envelope

        Raises:
            ValueError: If no rates data found for country
        """
        # Fetch data from repository
        df = get_government_bond_rates(
            country=self.country,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        if df.empty:
            raise ValueError(f"No bond rates data found for country: {self.country}")

        # Transform DataFrame to API response format
        data = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "m1": float(row["m1"]) if row["m1"] is not None else None,
                "m2": float(row["m2"]) if row["m2"] is not None else None,
                "m3": float(row["m3"]) if row["m3"] is not None else None,
                "m6": float(row["m6"]) if row["m6"] is not None else None,
                "y1": float(row["y1"]) if row["y1"] is not None else None,
                "y2": float(row["y2"]) if row["y2"] is not None else None,
                "y3": float(row["y3"]) if row["y3"] is not None else None,
                "y5": float(row["y5"]) if row["y5"] is not None else None,
                "y7": float(row["y7"]) if row["y7"] is not None else None,
                "y10": float(row["y10"]) if row["y10"] is not None else None,
                "y20": float(row["y20"]) if row["y20"] is not None else None,
                "y30": float(row["y30"]) if row["y30"] is not None else None,
            }
            for _, row in df.iterrows()
        ]

        payload = {
            "country": self.country,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        # Build counts metadata
        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}


class EconomicIndicatorService:
    """Service for fetching and formatting economic indicator data."""

    def __init__(
        self,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the economic indicator service.

        Args:
            indicator: Indicator name (e.g., "GDP", "CPI", "unemployment_rate")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.indicator = self._validate_indicator(indicator)
        self.start_date = self._parse_date(start_date) if start_date else None
        self.end_date = self._parse_date(end_date) if end_date else None

    @staticmethod
    def _validate_indicator(indicator: str) -> str:
        """Validate indicator name format."""
        if not indicator or not indicator.strip():
            raise ValueError("Indicator name cannot be empty")

        indicator = indicator.strip()

        # Reason: Indicator names can contain letters, numbers, and underscores
        if not all(c.isalnum() or c == "_" for c in indicator):
            raise ValueError(f"Invalid indicator name: {indicator}")

        return indicator

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """
        Parse date string to date object.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            date object

        Raises:
            ValueError: If date format is invalid
        """
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD") from e

    def get_indicator_data(self) -> Dict[str, Any]:
        """
        Fetch economic indicator data.

        Returns:
            Dict containing payload (time series data) and counts for response envelope

        Raises:
            ValueError: If no data found for indicator
        """
        # Fetch data from repository
        df = get_economic_indicators(
            indicator=self.indicator,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        if df.empty:
            raise ValueError(f"No data found for indicator: {self.indicator}")

        # Transform DataFrame to API response format
        data = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "value": float(row["value"]) if row["value"] is not None else None,
            }
            for _, row in df.iterrows()
        ]

        payload = {
            "indicator": self.indicator,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        # Build counts metadata
        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}


class EconomicCalendarService:
    """Service for fetching and formatting economic calendar events data."""

    def __init__(
        self,
        country: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event: Optional[str] = None,
    ):
        """
        Initialize the economic calendar service.

        Args:
            country: Country code (e.g., "US", "UK", "CA", "FR", "DE", "IT", "JP")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            event: Event name filter - partial match, case-insensitive (optional)
        """
        self.country = self._validate_country(country)
        self.start_date = self._parse_date(start_date) if start_date else None
        self.end_date = self._parse_date(end_date) if end_date else None
        self.event = event.strip() if event else None

    @staticmethod
    def _validate_country(country: str) -> str:
        """Validate country code format."""
        if not country or not country.strip():
            raise ValueError("Country code cannot be empty")

        country = country.strip().upper()

        # Reason: Economic calendar uses 2-letter ISO codes (US, UK, CA, FR, DE, IT, JP)
        if not country.isalpha() or len(country) != 2:
            raise ValueError(
                f"Invalid country code: {country}. Expected 2-letter code (US, UK, CA, FR, DE, IT, JP)"
            )

        # Validate against supported G7 countries
        valid_countries = {"US", "UK", "CA", "FR", "DE", "IT", "JP"}
        if country not in valid_countries:
            raise ValueError(
                f"Country {country} not supported. Supported countries: {', '.join(sorted(valid_countries))}"
            )

        return country

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """
        Parse date string to date object.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            date object

        Raises:
            ValueError: If date format is invalid
        """
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD") from e

    def get_calendar_events(self) -> Dict[str, Any]:
        """
        Fetch economic calendar events.

        Returns:
            Dict containing payload (events data) and counts for response envelope

        Raises:
            ValueError: If no calendar events found for country
        """
        # Fetch data from repository
        df = get_economic_calendar(
            country=self.country,
            start_date=self.start_date,
            end_date=self.end_date,
            event=self.event,
        )

        if df.empty:
            raise ValueError(f"No economic calendar events found for country: {self.country}")

        # Transform DataFrame to API response format
        data = [
            {
                "eventId": int(row["event_id"]),
                "date": row["date"].strftime("%Y-%m-%d %H:%M:%S"),
                "event": row["event"],
                "country": row["country"],
                "currency": row["currency"],
                "actual": float(row["actual"]) if row["actual"] is not None else None,
                "previous": float(row["previous"]) if row["previous"] is not None else None,
                "estimate": float(row["estimate"]) if row["estimate"] is not None else None,
                "change": float(row["change"]) if row["change"] is not None else None,
                "changePercentage": float(row["change_percentage"])
                if row["change_percentage"] is not None
                else None,
                "impact": row["impact"],
            }
            for _, row in df.iterrows()
        ]

        payload = {
            "country": self.country,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "eventFilter": self.event,
            "data": data,
        }

        # Build counts metadata
        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}