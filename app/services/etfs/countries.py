"""Service layer for ETF country weightings."""

from typing import Dict, Any

from app.db.core.pull_fmp_data import FMP_API_DATA


class ETFCountryWeightingsService:
    """Service for fetching and formatting ETF country concentration data."""

    def __init__(self, symbol: str):
        """
        Initialize the ETF country weightings service.

        Args:
            symbol: ETF ticker symbol (e.g., "SPY", "QQQ")
        """
        self.symbol = self._validate_symbol(symbol)

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        """
        Validate ETF ticker symbol format.

        Args:
            symbol: Ticker symbol to validate

        Returns:
            Validated and normalized symbol (uppercase)

        Raises:
            ValueError: If symbol is empty or contains invalid characters
        """
        if not symbol or not symbol.strip():
            raise ValueError("ETF symbol cannot be empty")

        symbol = symbol.strip().upper()

        # Reason: Ticker symbols contain only letters and hyphens
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ-")
        if not all(c in allowed_chars for c in symbol):
            raise ValueError(
                f"Invalid symbol: {symbol}. "
                "Only letters and hyphens are allowed"
            )

        return symbol

    def get_country_weightings(self) -> Dict[str, Any]:
        """
        Fetch ETF country weightings data.

        Returns:
            Dict containing payload (country weightings) and counts for response envelope

        Raises:
            ValueError: If no country weightings data found for symbol
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_etf_country_weightings(ticker=self.symbol)

        if not raw_data:
            raise ValueError(f"No country weightings found for ETF: {self.symbol}")

        if isinstance(raw_data, list) and len(raw_data) == 0:
            raise ValueError(f"No country weightings found for ETF: {self.symbol}")

        # Reason: Return FMP data as-is, following KISS principle
        data = self._format_country_data(raw_data)

        payload = {
            "symbol": self.symbol,
            "countryWeightings": data,
        }

        counts = {
            "currentItemCount": len(data) if isinstance(data, list) else 1,
            "itemsPerPage": len(data) if isinstance(data, list) else 1,
            "startIndex": 1,
            "totalItems": len(data) if isinstance(data, list) else 1,
        }

        return {"payload": payload, "counts": counts}

    @staticmethod
    def _format_country_data(raw_data: Any) -> Any:
        """
        Format raw FMP API country weightings data.

        Args:
            raw_data: Raw data from FMP API

        Returns:
            Formatted country weightings data with updatedAt field removed
        """
        if isinstance(raw_data, list):
            # List of country weightings
            formatted = []
            for record in raw_data:
                if isinstance(record, dict):
                    formatted.append({k: v for k, v in record.items() if k != "updatedAt"})
            return formatted
        elif isinstance(raw_data, dict):
            # Single object
            return {k: v for k, v in raw_data.items() if k != "updatedAt"}
        else:
            return raw_data


