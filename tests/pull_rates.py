"""
Pull government bond rates for multiple countries from FMP.

Supports 60+ countries. Most common ones have 3-month and 10-year rates.
US has full yield curve (12 maturities).
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.utils.time_utils import get_current_utc_time

load_dotenv()

API_KEY = os.getenv('FMP_API_KEY')
BASE_URL = "https://financialmodelingprep.com/api"


def get_country_rates(country, start_date=None, end_date=None):
    """
    Pull government bond rates for a specific country.

    Args:
        country: Country code (e.g., 'US', 'GB', 'JP')
        start_date: Start date (default: 10 years ago)
        end_date: End date (default: today)

    Returns:
        DataFrame with rates data
    """
    if not start_date:
        start_date = (get_current_utc_time() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = get_current_utc_time().strftime('%Y-%m-%d')

    print(f"Fetching {country} rates from {start_date} to {end_date}...")

    url = f"{BASE_URL}/v4/treasury"
    params = {
        'apikey': API_KEY
    }

    # For US, don't add country parameter
    if country != 'US':
        params['country'] = country

    # Add date range if not US (US endpoint may not support date filtering)
    if country != 'US':
        params['from'] = start_date
        params['to'] = end_date

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df['country'] = country

                # Filter by date if we got full dataset
                if 'date' in df.columns and country == 'US':
                    df['date'] = pd.to_datetime(df['date'])
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

                print(f"  {country}: {len(df)} records")
                return df
            else:
                print(f"  {country}: No data returned")
                return None
        else:
            print(f"  {country}: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"  {country}: Error - {e}")
        return None


def fetch_historical_rates(country, output_filename=None, rate_limit_delay=0.5):
    """
    Fetch historical rates data from Jan 1, 1990 to today in 3-month chunks.
    Saves data to CSV file in tests directory.

    Args:
        country: Country code (e.g., 'US', 'GB', 'JP', 'DE')
        output_filename: Custom CSV filename (default: '{country}_rates_1990_to_today.csv')
        rate_limit_delay: Delay in seconds between API calls (default: 0.5)

    Returns:
        DataFrame with all historical rates data
    """
    # Set up date range
    start_date = datetime(1990, 1, 1)
    end_date = get_current_utc_time()

    # Set up output file
    if output_filename is None:
        output_filename = f"{country}_rates_1990_to_today.csv"

    output_path = Path(__file__).parent / output_filename

    print(f"\n{'='*80}")
    print(f"Fetching {country} rates from {start_date.date()} to {end_date.date()}")
    print(f"Output file: {output_path}")
    print(f"{'='*80}\n")

    all_data = []
    current_start = start_date
    chunk_num = 0

    # Iterate through 3-month chunks
    while current_start < end_date:
        chunk_num += 1

        # Calculate end of this chunk (3 months = ~90 days)
        current_end = current_start + timedelta(days=90)
        if current_end > end_date:
            current_end = end_date

        # Format dates for API
        start_str = current_start.strftime('%Y-%m-%d')
        end_str = current_end.strftime('%Y-%m-%d')

        print(f"Chunk {chunk_num}: {start_str} to {end_str}")

        # Fetch data for this chunk
        df = get_country_rates(country, start_str, end_str)

        if df is not None and len(df) > 0:
            all_data.append(df)
            print(f"  ✓ Fetched {len(df)} records")
        else:
            print(f"  ⚠ No data for this period")

        # Move to next chunk
        current_start = current_end + timedelta(days=1)

        # Rate limiting to avoid API throttling
        if current_start < end_date:
            time.sleep(rate_limit_delay)

    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)

        # Sort by date if date column exists
        if 'date' in combined_df.columns:
            combined_df['date'] = pd.to_datetime(combined_df['date'])
            combined_df = combined_df.sort_values('date')

        # Remove duplicates based on date
        if 'date' in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset='date', keep='first')

        # Save to CSV
        combined_df.to_csv(output_path, index=False)

        print(f"\n{'='*80}")
        print(f"✓ Successfully saved {len(combined_df)} records to {output_path}")
        print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"{'='*80}\n")

        return combined_df
    else:
        print(f"\n{'='*80}")
        print(f"✗ No data retrieved for {country}")
        print(f"{'='*80}\n")
        return None




# Predefined country sets
COUNTRIES = [
    'USA', 'GB', 'JP', 'DE', 'FR', 'CA', 'IT', 'ES', 'AU', 'NL',  # G10
    'CH', 'SE', 'NO', 'DK', 'NZ',                                 # Other developed
    'CN', 'IN', 'BR', 'RU', 'MX', 'SA', 'ZA',                     # BRICS + emerging
    'KR', 'TW', 'SG', 'HK', 'ID', 'TH', 'MY', 'PH',              # Asia
    'PL', 'CZ', 'HU', 'TR', 'GR', 'PT', 'IE', 'AT', 'BE', 'FI',  # Europe
]

def main():
    """Main execution - customize as needed."""

    # Example: Fetch all historical data for US
    # This will make ~140 API calls (35 years / 3 months each)
    # df = fetch_historical_rates(COUNTRIES[3])
    # print(df.head())

    from app.db.core.db_config import MacroDataSession
    from app.db.core.models.macro_data_models import GovernmentBondRates
    session = MacroDataSession()
    rates = session.query(GovernmentBondRates).filter(GovernmentBondRates.country == 'ES').all()
    for bond in rates:
        print(bond.date, bond.y1)
    session.close()

if __name__ == "__main__":
    main()