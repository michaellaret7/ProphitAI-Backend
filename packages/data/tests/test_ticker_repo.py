"""Tests for pure-logic ticker utilities: get_sector_etf and SECTOR_ETF_MAP.

These functions are simple dict lookups with no database dependency.
"""

import pytest

from prophitai_data.repositories.ticker import get_sector_etf, SECTOR_ETF_MAP


class TestSectorEtfMap:
    """Validate the static SECTOR_ETF_MAP mapping."""

    def test_all_eleven_sectors_mapped(self):
        """GICS has 11 sectors; the map must contain exactly 11 entries."""
        assert len(SECTOR_ETF_MAP) == 11

    def test_information_technology(self):
        """Information Technology maps to XLK."""
        assert SECTOR_ETF_MAP["equity_sector_information_technology"] == "XLK"

    def test_financials(self):
        """Financials maps to XLF."""
        assert SECTOR_ETF_MAP["equity_sector_financials"] == "XLF"

    def test_health_care(self):
        """Health Care maps to XLV."""
        assert SECTOR_ETF_MAP["equity_sector_health_care"] == "XLV"


class TestGetSectorEtf:
    """Validate the get_sector_etf() lookup function."""

    def test_returns_xlk_for_info_tech(self):
        """Known sector returns the correct ETF ticker."""
        assert get_sector_etf("equity_sector_information_technology") == "XLK"

    def test_returns_xlf_for_financials(self):
        """Known sector returns the correct ETF ticker."""
        assert get_sector_etf("equity_sector_financials") == "XLF"

    def test_returns_none_for_unknown_sector(self):
        """An unrecognised sector key returns None."""
        assert get_sector_etf("equity_sector_crypto") is None

    def test_returns_none_for_empty_string(self):
        """An empty string returns None."""
        assert get_sector_etf("") is None
