"""
Fetch and store US Economic Indicators from FMP API to database.

Retrieves macroeconomic time series data back to 1990 and stores in
the economic_indicators table with one UUID per indicator.
"""
import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys
from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.core.db_config import MacroDataSession
from app.db.core.models.macro_data_models import EconomicIndicators
from app.utils.time_utils import get_current_utc_time

load_dotenv()


# All available economic indicators from FMP (only indicators that return data)
ECONOMIC_INDICATORS = {
    # Labor Market
    "unemploymentRate": "Unemployment Rate",
    "totalNonfarmPayroll": "Total Nonfarm Payroll",
    "initialClaims": "Initial Jobless Claims",

    # Growth & Output
    "GDP": "Gross Domestic Product",
    "realGDP": "Real GDP",
    "nominalPotentialGDP": "Nominal Potential GDP",
    "realGDPPerCapita": "Real GDP Per Capita",
    "industrialProductionTotalIndex": "Industrial Production Total Index",
    "retailSales": "Retail Sales",
    "durableGoods": "Durable Goods Orders",

    # Inflation & Prices
    "CPI": "Consumer Price Index",
    "inflationRate": "Inflation Rate",
    "retailMoneyFunds": "Retail Money Funds",

    # Credit & Rates
    "federalFunds": "Federal Funds Rate",

    # Consumer Metrics
    "consumerSentiment": "Consumer Sentiment (University of Michigan)",

    # Business
    "totalVehicleSales": "Total Vehicle Sales",
}


def get_indicator_uuid(indicator_name: str):
    """
    Generate a deterministic UUID for an economic indicator.
    Same indicator always gets the same UUID.

    Args:
        indicator_name: Indicator name (e.g., 'GDP', 'unemploymentRate')

    Returns:
        UUID for the indicator
    """
    return uuid5(NAMESPACE_DNS, f"economic_indicator.{indicator_name}")


def get_economic_indicator(indicator_name: str, from_date: str = None, to_date: str = None):
    """
    Fetch a specific economic indicator from FMP API.

    Args:
        indicator_name: The indicator name (e.g., 'GDP', 'CPI', 'unemploymentRate')
        from_date: Start date in YYYY-MM-DD format (optional)
        to_date: End date in YYYY-MM-DD format (optional)

    Returns:
        DataFrame with date and value columns
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("Set FMP_API_KEY environment variable")

    url = f"https://financialmodelingprep.com/api/v4/economic?name={indicator_name}&apikey={api_key}"

    if from_date:
        url += f"&from={from_date}"
    if to_date:
        url += f"&to={to_date}"

    response = requests.get(url)

    if response.status_code != 200:
        print(f"  Error: API returned status {response.status_code}")
        return pd.DataFrame()

    data = response.json()

    if not data or not isinstance(data, list):
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Convert date strings to date objects for database insertion
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date

    # Remove duplicate dates (keep last occurrence for most recent value)
    if not df.empty and 'date' in df.columns:
        df = df.drop_duplicates(subset=['date'], keep='last')

    return df


def push_indicator_data_to_db(indicator_name: str, df: pd.DataFrame) -> int:
    """
    Push economic indicator data to the database.

    Uses upsert logic - updates existing records and inserts new ones
    based on unique constraint (indicator, date).

    Args:
        indicator_name: Indicator name (e.g., 'GDP', 'unemploymentRate')
        df: DataFrame with columns [date, value]

    Returns:
        Number of records inserted/updated
    """
    if df.empty:
        print(f"No data to insert for {indicator_name}")
        return 0

    session = MacroDataSession()
    try:
        current_time = get_current_utc_time()
        indicator_uuid = get_indicator_uuid(indicator_name)

        # Prepare records for insertion
        records = []
        for _, row in df.iterrows():
            records.append({
                'id': indicator_uuid,
                'indicator': indicator_name,
                'date': row['date'],
                'value': float(row['value']) if pd.notna(row['value']) else None,
                'created_at': current_time,
                'updated_at': current_time
            })

        # Use PostgreSQL INSERT ... ON CONFLICT for upsert
        stmt = insert(EconomicIndicators).values(records)

        # On conflict, update value and updated_at
        stmt = stmt.on_conflict_do_update(
            constraint='uq_indicator_date',
            set_={
                'value': stmt.excluded.value,
                'updated_at': current_time
            }
        )

        session.execute(stmt)
        session.commit()

        print(f"Inserted/updated {len(records)} records for {indicator_name}")
        return len(records)

    except Exception as e:
        session.rollback()
        print(f"Error inserting data for {indicator_name}: {e}")
        raise
    finally:
        session.close()


def fetch_and_store_indicator(indicator_name: str, from_date: str = "1990-01-01", to_date: str = None) -> int:
    """
    Fetch economic indicator data from FMP API and store in database.

    Args:
        indicator_name: Indicator name (e.g., 'GDP', 'unemploymentRate')
        from_date: Start date in YYYY-MM-DD format (default: 1990-01-01)
        to_date: End date in YYYY-MM-DD format (default: today)

    Returns:
        Number of records inserted/updated
    """
    # Fetch data from API
    df = get_economic_indicator(indicator_name, from_date, to_date)

    if df.empty:
        return 0

    # Push to database
    count = push_indicator_data_to_db(indicator_name, df)

    return count


def fetch_and_store_all_indicators(from_date: str = "1990-01-01", to_date: str = None):
    """
    Fetch all economic indicators from FMP API and store in database.

    Args:
        from_date: Start date in YYYY-MM-DD format (default: 1990-01-01)
        to_date: End date in YYYY-MM-DD format (default: today)

    Returns:
        Dictionary with indicator names as keys and record counts as values
    """
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching {len(ECONOMIC_INDICATORS)} economic indicators...")
    print(f"Date range: {from_date} to {to_date}")
    print("=" * 80)

    results = {}
    success_count = 0
    failed_indicators = []
    total_records = 0

    for indicator_key, indicator_label in ECONOMIC_INDICATORS.items():
        print(f"\n{indicator_label} ({indicator_key})...")

        try:
            count = fetch_and_store_indicator(indicator_key, from_date, to_date)

            if count > 0:
                results[indicator_key] = count
                success_count += 1
                total_records += count
            else:
                failed_indicators.append(indicator_key)

        except Exception as e:
            print(f"Failed: {e}")
            failed_indicators.append(indicator_key)

    print("\n" + "=" * 80)
    print(f"Summary: {success_count}/{len(ECONOMIC_INDICATORS)} indicators loaded successfully")
    print(f"Total records inserted/updated: {total_records:,}")

    if failed_indicators:
        print(f"\nFailed indicators: {', '.join(failed_indicators)}")

    return results


if __name__ == "__main__":
    # Fetch and store only consumer sentiment
    print("Fetching Consumer Sentiment data from 1990...")
    print("=" * 80)

    try:
        count = fetch_and_store_indicator("consumerSentiment", from_date="1990-01-01")
        print("\n" + "=" * 80)
        print(f"Success! Loaded {count:,} records for consumerSentiment")
    except Exception as e:
        print(f"\nFailed to load consumerSentiment: {e}")
        import traceback
        traceback.print_exc()
