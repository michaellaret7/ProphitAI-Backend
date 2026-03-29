"""Service layer for ETF information and metadata."""

from typing import Dict, Any

from prophitai_data.clients.fmp import FMP_API_DATA


class ETFInfoService:
    """Service for fetching and formatting ETF information and metadata."""

    def __init__(self, symbol: str):
        """
        Initialize the ETF info service.

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

    def get_info(self) -> Dict[str, Any]:
        """
        Fetch ETF information and metadata.

        Returns:
            Dict containing payload (ETF info) and counts for response envelope

        Raises:
            ValueError: If no info data found for symbol
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_etf_info(ticker=self.symbol)

        if not raw_data:
            raise ValueError(f"No information found for ETF: {self.symbol}")

        # Reason: FMP API returns list with single ETF info object
        if isinstance(raw_data, list):
            if len(raw_data) == 0:
                raise ValueError(f"No information found for ETF: {self.symbol}")
            # Extract first element if list
            raw_data = raw_data[0]

        # Transform API response to standardized format
        data = self._format_info_data(raw_data)

        payload = {
            "symbol": self.symbol,
            "info": data,
        }

        counts = {
            "currentItemCount": 1,
            "itemsPerPage": 1,
            "startIndex": 1,
            "totalItems": 1,
        }

        return {"payload": payload, "counts": counts}

    @staticmethod
    def _format_info_data(raw_data: Any) -> Dict[str, Any]:
        """
        Format raw FMP API ETF info data.

        Args:
            raw_data: Raw data from FMP API

        Returns:
            Formatted ETF info dictionary
        """
        if not isinstance(raw_data, dict):
            return {}

        # Reason: Return FMP data as-is, following KISS principle
        # Only exclude internal fields like updatedAt that are not user-facing
        formatted = {k: v for k, v in raw_data.items() if k != "updatedAt"}

        return formatted

    def get_overview(self) -> Dict[str, Any]:
        """
        Get condensed overview of ETF with key metrics only.

        Returns:
            Dict with essential ETF information
        """
        full_info = self.get_info()
        etf_data = full_info["payload"]["info"]

        # Extract only key metrics for overview using correct FMP field names
        overview = {
            "symbol": etf_data.get("symbol"),
            "name": etf_data.get("name"),
            "description": etf_data.get("description"),
            "assetClass": etf_data.get("assetClass"),
            "etfCompany": etf_data.get("etfCompany"),
            "inceptionDate": etf_data.get("inceptionDate"),
            "metrics": {
                "assetsUnderManagement": etf_data.get("assetsUnderManagement"),
                "expenseRatio": etf_data.get("expenseRatio"),
                "avgVolume": etf_data.get("avgVolume"),
                "holdingsCount": etf_data.get("holdingsCount"),
                "nav": etf_data.get("nav"),
            },
        }

        payload = {
            "symbol": self.symbol,
            "overview": overview,
        }

        counts = {
            "currentItemCount": 1,
            "itemsPerPage": 1,
            "startIndex": 1,
            "totalItems": 1,
        }

        return {"payload": payload, "counts": counts}

    def get_exposure(self) -> Dict[str, Any]:
        """
        Get sector and geographic exposure details.

        Returns:
            Dict with exposure breakdown
        """
        full_info = self.get_info()
        etf_data = full_info["payload"]["info"]

        exposure = {
            "symbol": etf_data.get("symbol"),
            "name": etf_data.get("name"),
            "domicile": etf_data.get("domicile"),
            "sectorsList": etf_data.get("sectorsList", []),
            "holdingsCount": etf_data.get("holdingsCount"),
        }

        payload = {
            "symbol": self.symbol,
            "exposure": exposure,
        }

        counts = {
            "currentItemCount": 1,
            "itemsPerPage": 1,
            "startIndex": 1,
            "totalItems": 1,
        }

        return {"payload": payload, "counts": counts}
