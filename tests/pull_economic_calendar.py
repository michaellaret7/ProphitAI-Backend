"""
Fetch Economic Calendar data from FMP API.

The Economic Calendar provides:
- Scheduled release dates for economic reports
- Expected vs actual values for announcements
- Central bank meetings and interest rate decisions
- PMI releases, employment reports, GDP announcements
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_economic_calendar(from_date: str = None, to_date: str = None):
    """
    Fetch economic calendar events from FMP API.

    Args:
        from_date: Start date in YYYY-MM-DD format (optional)
        to_date: End date in YYYY-MM-DD format (optional, max 90 days from start)

    Returns:
        DataFrame with economic calendar events
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("Set FMP_API_KEY environment variable")

    # Default to next 90 days if no dates provided
    if not from_date:
        from_date = datetime.now().strftime("%Y-%m-%d")
    if not to_date:
        # Max 90 days range
        to_datetime = datetime.strptime(from_date, "%Y-%m-%d") + timedelta(days=90)
        to_date = to_datetime.strftime("%Y-%m-%d")

    url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={from_date}&to={to_date}&apikey={api_key}"

    print(f"Fetching economic calendar from {from_date} to {to_date}...")

    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")

    data = response.json()

    if not data or not isinstance(data, list):
        print("No data found or unexpected format")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} economic calendar events")

    return df


if __name__ == "__main__":
    # Fetch economic calendar for next 90 days
    df = get_economic_calendar()

    if not df.empty:
        print("\nEconomic Calendar Data:")
        print("=" * 100)
        print(f"Total events: {len(df)}")
        print(f"\nColumns: {', '.join(df.columns)}")
        print(f"\nSample events:")
        print(df.head(20).to_string())

        # Show some statistics
        if 'country' in df.columns:
            print(f"\n\nCountries: {df['country'].nunique()} unique")
            print(df['country'].value_counts().head(10))

        if 'event' in df.columns:
            print(f"\n\nTop events:")
            print(df['event'].value_counts().head(10))
    else:
        print("No data retrieved")
