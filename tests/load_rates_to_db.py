"""
Fetch government bond rates data from FMP API and load directly into macro_data database.

This script:
1. Fetches rates data from FMP API in 3-month chunks from 1990 to today
2. Processes and validates the data
3. Inserts into the gov_bond_rates table (public schema)
4. Handles duplicates with upsert logic

Note: Each country has a single UUID. This script will look up existing country UUIDs
or create new ones for new countries.
"""
import sys
from pathlib import Path
import pandas as pd
import os
import requests
import time
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.core.db_config import macro_data_engine, MacroDataSession
from app.db.core.models.macro_data_models import GovernmentBondRates
from app.utils.time_utils import get_current_utc_time

load_dotenv()

API_KEY = os.getenv('FMP_API_KEY')
BASE_URL = "https://financialmodelingprep.com/api"


def create_schema_and_tables():
    """Create tables if they don't exist."""
    print("Creating tables...")

    # Create all tables defined in MacroDataBase
    from app.db.core.db_config import MacroDataBase
    MacroDataBase.metadata.create_all(macro_data_engine)

    print("✓ Tables ready")


def get_or_create_country_uuid(country, session):
    """
    Get the UUID for a country, or create a new one if it doesn't exist.

    Args:
        country: Country code (e.g., 'US', 'GB', 'JP')
        session: Database session

    Returns:
        UUID for the country
    """
    # Try to get existing UUID for this country
    result = session.execute(
        text("SELECT DISTINCT id FROM gov_bond_rates WHERE country = :country LIMIT 1"),
        {"country": country}
    )
    row = result.fetchone()

    if row:
        return row[0]  # Return existing UUID
    else:
        # Generate new UUID for new country
        new_uuid = uuid4()
        print(f"  → Generated new UUID for {country}: {new_uuid}")
        return new_uuid


def get_country_rates_from_api(country, start_date, end_date):
    """
    Fetch government bond rates for a specific country from FMP API.

    Args:
        country: Country code (e.g., 'US', 'GB', 'JP')
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        DataFrame with rates data or None
    """
    url = f"{BASE_URL}/v4/treasury"
    params = {
        'apikey': API_KEY
    }

    # For US, don't add country parameter
    if country != 'US':
        params['country'] = country
        params['from'] = start_date
        params['to'] = end_date

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df['country'] = country

                # Filter by date if we got full dataset (US endpoint)
                if 'date' in df.columns and country == 'US':
                    df['date'] = pd.to_datetime(df['date'])
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

                return df
            else:
                return None
        else:
            print(f"  ⚠ HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return None


def map_csv_columns_to_db(df):
    """
    Map CSV column names from FMP API to database column names.

    FMP API returns columns like: 'month1', 'month3', 'year1', 'year10', etc.
    Database expects: '1m', '3m', '1y', '10y', etc.
    """
    column_mapping = {
        'month1': '1m',
        'month2': '2m',
        'month3': '3m',
        'month6': '6m',
        'year1': '1y',
        'year2': '2y',
        'year3': '3y',
        'year5': '5y',
        'year7': '7y',
        'year10': '10y',
        'year20': '20y',
        'year30': '30y',
    }

    # Rename columns that exist in the dataframe
    rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns}
    df = df.rename(columns=rename_dict)

    return df


def load_dataframe_to_database(df, country):
    """
    Load rates data from DataFrame into database.

    Args:
        df: DataFrame with rates data
        country: Country code

    Returns:
        Number of records inserted/updated
    """
    if df is None or df.empty:
        return 0

    # Ensure country column exists
    if 'country' not in df.columns:
        df['country'] = country

    # Map column names
    df = map_csv_columns_to_db(df)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date']).dt.date

    # Add timestamps
    current_time = get_current_utc_time()
    df['created_at'] = current_time
    df['updated_at'] = current_time

    # Use PostgreSQL INSERT ... ON CONFLICT for upsert
    session = MacroDataSession()
    try:
        # Get or create UUID for this country
        country_uuid = get_or_create_country_uuid(country, session)

        # Add country UUID to all records
        df['id'] = str(country_uuid)

        # Select only columns that exist in the database model
        db_columns = [
            'id', 'country', 'date',
            '1m', '2m', '3m', '6m',
            '1y', '2y', '3y', '5y', '7y', '10y', '20y', '30y',
            'created_at', 'updated_at'
        ]

        # Keep only columns that exist in both dataframe and database
        available_columns = [col for col in db_columns if col in df.columns]
        df = df[available_columns]

        # Remove rows with no rate data (all rate columns are null)
        rate_columns = [col for col in available_columns if col not in ['id', 'country', 'date', 'created_at', 'updated_at']]
        df = df.dropna(subset=rate_columns, how='all')

        if df.empty:
            return 0

        # Convert dataframe to list of dicts for SQLAlchemy
        records = df.to_dict('records')

        # Batch insert with ON CONFLICT DO UPDATE
        stmt = insert(GovernmentBondRates).values(records)

        # On conflict, update all rate columns and updated_at
        update_dict = {col: stmt.excluded[col] for col in rate_columns}
        update_dict['updated_at'] = stmt.excluded.updated_at

        stmt = stmt.on_conflict_do_update(
            constraint='uq_country_date',
            set_=update_dict
        )

        session.execute(stmt)
        session.commit()

        return len(records)

    except Exception as e:
        session.rollback()
        print(f"  ✗ Database Error: {e}")
        return 0
    finally:
        session.close()


def fetch_and_load_historical_rates(country, rate_limit_delay=0.5):
    """
    Fetch historical rates data from FMP API (Jan 1, 1990 to today) and load into database.

    Args:
        country: Country code (e.g., 'US', 'GB', 'JP', 'DE')
        rate_limit_delay: Delay in seconds between API calls (default: 0.5)

    Returns:
        Total number of records inserted/updated
    """
    # Set up date range
    start_date = datetime(1990, 1, 1)
    end_date = get_current_utc_time()

    print(f"\n{'='*80}")
    print(f"Fetching {country} rates from {start_date.date()} to {end_date.date()}")
    print(f"{'='*80}\n")

    all_data = []
    current_start = start_date
    chunk_num = 0
    total_records = 0

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
        df = get_country_rates_from_api(country, start_str, end_str)

        if df is not None and len(df) > 0:
            all_data.append(df)
            print(f"  ✓ Fetched {len(df)} records from API")
        else:
            print(f"  ⚠ No data for this period")

        # Move to next chunk
        current_start = current_end + timedelta(days=1)

        # Rate limiting to avoid API throttling
        if current_start < end_date:
            time.sleep(rate_limit_delay)

    # Combine and load all data
    if all_data:
        # Filter out DataFrames that are empty or have no valid data before concatenating
        valid_data = [df for df in all_data if df is not None and not df.empty]

        if not valid_data:
            print(f"\n{'='*80}")
            print(f"✗ No valid data retrieved for {country}")
            print(f"{'='*80}\n")
            return 0

        combined_df = pd.concat(valid_data, ignore_index=True)

        # Sort by date if date column exists
        if 'date' in combined_df.columns:
            combined_df['date'] = pd.to_datetime(combined_df['date'])
            combined_df = combined_df.sort_values('date')

        # Remove duplicates based on date
        if 'date' in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset='date', keep='first')

        print(f"\nLoading {len(combined_df)} records to database...")
        total_records = load_dataframe_to_database(combined_df, country)

        print(f"\n{'='*80}")
        print(f"✓ Successfully loaded {total_records} records for {country}")
        print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"{'='*80}\n")

        return total_records
    else:
        print(f"\n{'='*80}")
        print(f"✗ No data retrieved for {country}")
        print(f"{'='*80}\n")
        return 0


def fetch_and_load_multiple_countries(countries, rate_limit_delay=0.5):
    """
    Fetch and load rates data for multiple countries.

    Args:
        countries: List of country codes
        rate_limit_delay: Delay between API calls

    Returns:
        Total number of records processed across all countries
    """
    total_records = 0

    for country in countries:
        records = fetch_and_load_historical_rates(country, rate_limit_delay)
        total_records += records

    return total_records


def main():
    """Main execution."""
    print("="*80)
    print("Fetching and Loading Government Bond Rates Data")
    print("="*80)

    # Step 1: Create tables
    create_schema_and_tables()


    # g10 = ['USA', 'GB', 'JP', 'DE', 'FR', 'CA', 'IT', 'ES', 'AU', 'NL']
    # other_developed = ['CH', 'SE', 'NO', 'DK', 'NZ']
    # brics_emerging = ['CN', 'IN', 'BR', 'RU', 'MX', 'SA', 'ZA']
    # asia = ['KR', 'TW', 'SG', 'HK', 'ID', 'TH', 'MY', 'PH']
    europe = ['PL', 'CZ', 'HU', 'TR', 'GR', 'PT', 'IE', 'AT', 'BE', 'FI']

    # Step 3: Fetch and load data
    total = fetch_and_load_multiple_countries(europe, rate_limit_delay=0.5)

    print(f"\n{'='*80}")
    print(f"✓ Complete! Total records processed: {total}")
    print(f"{'='*80}\n")

    # Step 4: Show summary stats
    session = MacroDataSession()
    try:
        result = session.execute(
            text("""
                SELECT
                    country,
                    COUNT(*) as record_count,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM gov_bond_rates
                GROUP BY country
                ORDER BY country
            """)
        )

        print("\nDatabase Summary:")
        print("-" * 80)
        for row in result:
            print(f"  {row.country}: {row.record_count} records "
                  f"({row.earliest_date} to {row.latest_date})")

    finally:
        session.close()


if __name__ == "__main__":
    main()