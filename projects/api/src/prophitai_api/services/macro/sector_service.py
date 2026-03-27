"""Service layer for sector and industry metrics endpoints."""

from typing import Dict, Any, Optional
from datetime import date

from prophitai_data.clients.fmp import FMP_API_DATA

#TODO: Add this data to the database and then pull the data from the db instead of using the FMP API

# Standard GICS sector names used by FMP API
VALID_SECTORS = {
    "Technology",
    "Healthcare",
    "Financial Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Industrials",
    "Energy",
    "Utilities",
    "Real Estate",
    "Basic Materials",
    "Communication Services",
}

class SectorPerformanceService:
    """Service for fetching and formatting historical sector performance data."""

    def __init__(
        self,
        sector: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the sector performance service.

        Args:
            sector: Sector name (e.g., "Technology", "Healthcare")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.sector = self._validate_sector(sector)
        self.start_date = self._parse_date(start_date) if start_date else None
        self.end_date = self._parse_date(end_date) if end_date else None

    @staticmethod
    def _validate_sector(sector: str) -> str:
        """
        Validate sector name against known GICS sectors.

        Args:
            sector: Sector name to validate

        Returns:
            Validated sector name

        Raises:
            ValueError: If sector is empty or invalid
        """
        if not sector or not sector.strip():
            raise ValueError("Sector name cannot be empty")

        sector = sector.strip()

        # Reason: Accept case-insensitive sector names for better UX
        # Match against VALID_SECTORS using case-insensitive comparison
        sector_lower = sector.lower()
        for valid_sector in VALID_SECTORS:
            if valid_sector.lower() == sector_lower:
                return valid_sector

        # If no match found, raise error with helpful message
        raise ValueError(
            f"Invalid sector: {sector}. "
            f"Valid sectors: {', '.join(sorted(VALID_SECTORS))}"
        )

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
            raise ValueError(
                f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
            ) from e

    def get_performance(self) -> Dict[str, Any]:
        """
        Fetch historical sector performance data.

        Returns:
            Dict containing payload (performance data) and counts for response envelope

        Raises:
            ValueError: If no performance data found for sector
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_historical_sector_performance(
            sector=self.sector,
            from_date=self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            to_date=self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
        )

        if not raw_data:
            raise ValueError(f"No performance data found for sector: {self.sector}")

        # Reason: FMP API returns list of performance records, ensure it's not empty
        if isinstance(raw_data, list) and len(raw_data) == 0:
            raise ValueError(f"No performance data found for sector: {self.sector}")

        # Transform API response to standardized format
        data = self._format_performance_data(raw_data)

        payload = {
            "sector": self.sector,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}

    @staticmethod
    def _format_performance_data(raw_data: Any) -> list:
        """
        Format raw FMP API performance data.

        Args:
            raw_data: Raw data from FMP API

        Returns:
            Formatted list of performance records
        """
        if not isinstance(raw_data, list):
            return []

        # Transform each record to standardized format
        formatted = []
        for record in raw_data:
            if not isinstance(record, dict):
                continue

            # Reason: FMP API returns 'averageChange' not 'changesPercentage'
            formatted_record = {
                "date": record.get("date"),
                "changesPercentage": float(record["averageChange"])
                if record.get("averageChange") is not None
                else None,
            }
            formatted.append(formatted_record)

        return formatted


class SectorPEService:
    """Service for fetching and formatting historical sector P/E ratio data."""

    def __init__(
        self,
        sector: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the sector P/E service.

        Args:
            sector: Sector name (e.g., "Technology", "Healthcare")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.sector = SectorPerformanceService._validate_sector(sector)
        self.start_date = (
            SectorPerformanceService._parse_date(start_date) if start_date else None
        )
        self.end_date = (
            SectorPerformanceService._parse_date(end_date) if end_date else None
        )

    def get_pe_ratios(self) -> Dict[str, Any]:
        """
        Fetch historical sector P/E ratio data.

        Returns:
            Dict containing payload (P/E data) and counts for response envelope

        Raises:
            ValueError: If no P/E data found for sector
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_historical_sector_pe(
            sector=self.sector,
            from_date=self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            to_date=self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
        )

        if not raw_data:
            raise ValueError(f"No P/E data found for sector: {self.sector}")

        if isinstance(raw_data, list) and len(raw_data) == 0:
            raise ValueError(f"No P/E data found for sector: {self.sector}")

        # Transform API response to standardized format
        data = self._format_pe_data(raw_data)

        payload = {
            "sector": self.sector,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}

    @staticmethod
    def _format_pe_data(raw_data: Any) -> list:
        """
        Format raw FMP API P/E data.

        Args:
            raw_data: Raw data from FMP API

        Returns:
            Formatted list of P/E records
        """
        if not isinstance(raw_data, list):
            return []

        formatted = []
        for record in raw_data:
            if not isinstance(record, dict):
                continue

            formatted_record = {
                "date": record.get("date"),
                "pe": float(record["pe"]) if record.get("pe") is not None else None,
            }
            formatted.append(formatted_record)

        return formatted


class IndustryPerformanceService:
    """Service for fetching and formatting historical industry performance data."""

    def __init__(
        self,
        industry: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the industry performance service.

        Args:
            industry: Industry name (e.g., "Software", "Biotechnology")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.industry = self._validate_industry(industry)
        self.start_date = (
            SectorPerformanceService._parse_date(start_date) if start_date else None
        )
        self.end_date = (
            SectorPerformanceService._parse_date(end_date) if end_date else None
        )

    @staticmethod
    def _validate_industry(industry: str) -> str:
        """
        Validate industry name format.

        Args:
            industry: Industry name to validate

        Returns:
            Validated industry name

        Raises:
            ValueError: If industry is empty or contains invalid characters
        """
        if not industry or not industry.strip():
            raise ValueError("Industry name cannot be empty")

        industry = industry.strip()

        # Reason: Industry names can contain letters, spaces, hyphens, and ampersands
        # FMP API uses specific formats like "Software - Application", "Oil & Gas - E&P"
        # Examples: "Software - Application", "Oil & Gas - E&P", "Medical Devices"
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -&")
        if not all(c in allowed_chars for c in industry):
            raise ValueError(
                f"Invalid industry name: {industry}. "
                "Only letters, spaces, hyphens, and ampersands are allowed"
            )

        return industry

    def get_performance(self) -> Dict[str, Any]:
        """
        Fetch historical industry performance data.

        Returns:
            Dict containing payload (performance data) and counts for response envelope

        Raises:
            ValueError: If no performance data found for industry
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_historical_industry_performance(
            industry=self.industry,
            from_date=self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            to_date=self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
        )

        if not raw_data:
            raise ValueError(f"No performance data found for industry: {self.industry}")

        if isinstance(raw_data, list) and len(raw_data) == 0:
            raise ValueError(f"No performance data found for industry: {self.industry}")

        # Transform API response to standardized format
        data = SectorPerformanceService._format_performance_data(raw_data)

        payload = {
            "industry": self.industry,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}


class IndustryPEService:
    """Service for fetching and formatting historical industry P/E ratio data."""

    def __init__(
        self,
        industry: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Initialize the industry P/E service.

        Args:
            industry: Industry name (e.g., "Software", "Biotechnology")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
        """
        self.industry = IndustryPerformanceService._validate_industry(industry)
        self.start_date = (
            SectorPerformanceService._parse_date(start_date) if start_date else None
        )
        self.end_date = (
            SectorPerformanceService._parse_date(end_date) if end_date else None
        )

    def get_pe_ratios(self) -> Dict[str, Any]:
        """
        Fetch historical industry P/E ratio data.

        Returns:
            Dict containing payload (P/E data) and counts for response envelope

        Raises:
            ValueError: If no P/E data found for industry
        """
        # Fetch data from FMP API
        fmp = FMP_API_DATA()
        raw_data = fmp.get_historical_industry_pe(
            industry=self.industry,
            from_date=self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            to_date=self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
        )

        if not raw_data:
            raise ValueError(f"No P/E data found for industry: {self.industry}")

        if isinstance(raw_data, list) and len(raw_data) == 0:
            raise ValueError(f"No P/E data found for industry: {self.industry}")

        # Transform API response to standardized format
        data = SectorPEService._format_pe_data(raw_data)

        payload = {
            "industry": self.industry,
            "startDate": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "endDate": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "data": data,
        }

        counts = {
            "currentItemCount": len(data),
            "itemsPerPage": len(data),
            "startIndex": 1,
            "totalItems": len(data),
        }

        return {"payload": payload, "counts": counts}
