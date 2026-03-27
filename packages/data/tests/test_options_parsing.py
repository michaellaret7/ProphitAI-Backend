"""Tests for OSI option symbol decoding.

Validates that decode_osi correctly parses standard OSI symbols into
(root, expiration, type, strike) tuples and returns a None-tuple for
malformed inputs.
"""

import pytest

from prophitai_data.clients.options.service import decode_osi


class TestDecodeOsi:
    """Parse OSI option symbols into structured components."""

    def test_valid_call(self):
        """Standard call option symbol is decoded correctly."""
        root, exp, opt_type, strike = decode_osi("AAPL250117C00150000")
        assert root == "AAPL"
        assert exp == "2025-01-17"
        assert opt_type == "call"
        assert strike == pytest.approx(150.0)

    def test_valid_put(self):
        """Standard put option symbol is decoded correctly."""
        root, exp, opt_type, strike = decode_osi("MSFT240315P00350000")
        assert root == "MSFT"
        assert exp == "2024-03-15"
        assert opt_type == "put"
        assert strike == pytest.approx(350.0)

    def test_fractional_strike(self):
        """Strike prices with fractional dollars are preserved."""
        root, exp, opt_type, strike = decode_osi("TSLA251219C00247500")
        assert root == "TSLA"
        assert exp == "2025-12-19"
        assert opt_type == "call"
        assert strike == pytest.approx(247.5)

    def test_invalid_symbol(self):
        """An unparseable string returns the None-tuple."""
        result = decode_osi("NOTANOPTION")
        assert result == (None, None, None, None)

    def test_empty_string(self):
        """An empty string returns the None-tuple."""
        result = decode_osi("")
        assert result == (None, None, None, None)

    def test_single_char_root(self):
        """A one-letter underlying (e.g. 'F') is parsed correctly."""
        root, exp, opt_type, strike = decode_osi("F250117C00012000")
        assert root == "F"
        assert exp == "2025-01-17"
        assert opt_type == "call"
        assert strike == pytest.approx(12.0)
