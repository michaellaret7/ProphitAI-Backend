"""Tests for FMP API client with mocked HTTP requests.

Validates request logic, retry behavior, error handling,
and URL construction for key endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock

from prophitai_data.clients.fmp import FMP_API_DATA


# ================================
# --> Helper funcs
# ================================

def _make_fmp_client():
    """Create an FMP_API_DATA instance with a test API key."""
    # Reason: conftest sets FMP_API_KEY env var, so __init__ picks it up
    client = FMP_API_DATA()
    assert client.api_key is not None
    return client


def _mock_response(status_code=200, json_data=None, raise_exc=None):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    if raise_exc:
        resp.raise_for_status.side_effect = raise_exc
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestMakeFmpApiRequest:
    """Tests for the internal _make_fmp_api_request method."""

    @patch("prophitai_data.clients.fmp.requests.get")
    def test_success_returns_json(self, mock_get):
        """Successful 200 response returns parsed JSON."""
        expected = [{"symbol": "AAPL", "price": 150.0}]
        mock_get.return_value = _mock_response(json_data=expected)

        client = _make_fmp_client()
        result = client._make_fmp_api_request("https://example.com/api?symbol=AAPL")

        assert result == expected
        assert mock_get.called

    @patch("prophitai_data.clients.fmp.time.sleep")
    @patch("prophitai_data.clients.fmp.requests.get")
    def test_retries_on_429(self, mock_get, mock_sleep):
        """429 response triggers retry with exponential backoff, then succeeds."""
        rate_limit_resp = _mock_response(status_code=429)
        # Reason: raise_for_status should raise on 429 but _make_fmp_api_request
        # checks status_code directly, so we don't need it to raise
        success_resp = _mock_response(json_data=[{"price": 100.0}])

        mock_get.side_effect = [rate_limit_resp, success_resp]

        client = _make_fmp_client()
        result = client._make_fmp_api_request("https://example.com/api")

        assert result == [{"price": 100.0}]
        # Reason: Should have slept once for the 429 retry
        assert mock_sleep.called
        assert mock_get.call_count == 2

    @patch("prophitai_data.clients.fmp.time.sleep")
    @patch("prophitai_data.clients.fmp.requests.get")
    def test_returns_none_on_persistent_failure(self, mock_get, mock_sleep):
        """Repeated exceptions exhaust retries and return None."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("Connection refused")

        client = _make_fmp_client()
        result = client._make_fmp_api_request("https://example.com/api")

        assert result is None
        # Reason: Should have tried max_retries (5) times
        assert mock_get.call_count == 5

    @patch("prophitai_data.clients.fmp.requests.get")
    def test_returns_none_when_no_api_key(self, mock_get):
        """Returns None immediately if api_key is not set."""
        client = _make_fmp_client()
        client.api_key = None

        result = client._make_fmp_api_request("https://example.com/api")

        assert result is None
        assert not mock_get.called


class TestGetFullQuote:
    """Tests for get_full_quote URL construction."""

    @patch("prophitai_data.clients.fmp.requests.get")
    def test_calls_correct_url(self, mock_get):
        """get_full_quote constructs the correct FMP quote URL."""
        mock_get.return_value = _mock_response(json_data=[{"symbol": "AAPL"}])

        client = _make_fmp_client()
        client.get_full_quote("AAPL")

        called_url = mock_get.call_args[0][0]
        assert "https://financialmodelingprep.com/api/v3/quote/AAPL" in called_url
        assert f"apikey={client.api_key}" in called_url


class TestGetCompanyProfile:
    """Tests for get_company_profile URL construction."""

    @patch("prophitai_data.clients.fmp.requests.get")
    def test_calls_correct_url(self, mock_get):
        """get_company_profile constructs the correct FMP profile URL."""
        mock_get.return_value = _mock_response(json_data=[{"symbol": "MSFT"}])

        client = _make_fmp_client()
        client.get_company_profile("MSFT")

        called_url = mock_get.call_args[0][0]
        assert "https://financialmodelingprep.com/api/v3/profile/MSFT" in called_url
        assert f"apikey={client.api_key}" in called_url
