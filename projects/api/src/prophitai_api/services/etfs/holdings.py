"""Service layer for ETF holdings data."""

from typing import Dict, Any

from prophitai_data.clients.fmp import FMP_API_DATA


class ETFHoldingsService:
    """Service for fetching and formatting ETF holdings data."""

    def __init__(self, symbol: str):
        """
        Initialize the ETF holdings service.

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

    def get_holdings(self) -> Dict[str, Any]:
        """
        Fetch ETF holdings data.

        Returns:
            Dict containing payload (holdings data) and counts for response envelope

        Raises:
            ValueError: If no holdings data found for symbol
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_etf_holdings(ticker=self.symbol)

        if not raw_data:
            raise ValueError(f"No holdings data found for ETF: {self.symbol}")

        if isinstance(raw_data, list) and len(raw_data) == 0:
            raise ValueError(f"No holdings data found for ETF: {self.symbol}")

        # Reason: Return FMP data as-is, following KISS principle
        # Only exclude updatedAt field
        data = self._format_holdings_data(raw_data)

        payload = {
            "symbol": self.symbol,
            "holdings": data,
        }

        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}

    @staticmethod
    def _format_holdings_data(raw_data: Any) -> list:
        """
        Format raw FMP API holdings data.

        Args:
            raw_data: Raw data from FMP API

        Returns:
            List of holdings with updatedAt field removed
        """
        if not isinstance(raw_data, list):
            return []

        # Reason: Return FMP data as-is, only exclude updatedAt field
        formatted = []
        for record in raw_data:
            if isinstance(record, dict):
                formatted.append({k: v for k, v in record.items() if k != "updatedAt"})

        return formatted
