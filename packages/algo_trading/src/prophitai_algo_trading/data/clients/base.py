"""Base client for the FMP (Financial Modeling Prep) API."""

import os
import requests
from dotenv import load_dotenv


class FMPBaseClient:
    """Base client providing authentication and HTTP request handling for FMP API."""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            print("Error: FMP_API_KEY not found in environment variables.")

    def _make_fmp_api_request(self, url: str):
        """Helper function to make requests to the FMP API."""
        if not self.api_key:
            return None

        separator = '&' if '?' in url else '?'
        full_url = f"{url}{separator}apikey={self.api_key}"

        try:
            response = requests.get(full_url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None
