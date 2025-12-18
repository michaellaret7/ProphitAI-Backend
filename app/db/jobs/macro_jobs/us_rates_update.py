"""
Update US Treasury Rates Table

This module updates the gov_bond_rates table with the latest US treasury yield data
from FMP API. Fetches the full yield curve (1m through 30y maturities).
"""
import os
import requests
from datetime import timedelta, date
from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from dotenv import load_dotenv

from app.db.core.db_config import MacroDataSession
from app.db.core.models.macro_data_models import GovernmentBondRates
from app.utils.time_utils import get_current_utc_time

load_dotenv()


class UpdateUSRates:
    """Updates US treasury rates from FMP API"""

    # Deterministic UUID for USA (matches other macro data tables)
    US_UUID = uuid5(NAMESPACE_DNS, 'country.USA')

    # Column mapping from FMP API to database
    COLUMN_MAPPING = {
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

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable not found")

        # Progress tracking
        self.total_records_added = 0
        self.errors = 0

    def get_last_date_in_db(self, session) -> date | None:
        """
        Find the last date available in the database for US rates.

        Args:
            session: Database session

        Returns:
            Last date in database, or None if no data exists
        """
        try:
            result = session.query(
                func.max(GovernmentBondRates.date)
            ).filter(
                GovernmentBondRates.country == 'USA'
            ).scalar()

            return result
        except Exception as e:
            print(f"Error getting last date: {e}")
            return None

    def fetch_rates_from_api(self) -> list[dict]:
        """
        Fetch US treasury rates from FMP API.

        Note: US treasury endpoint returns all historical data without date params.

        Returns:
            List of dictionaries containing treasury rate data
        """
        base_url = "https://financialmodelingprep.com/api/v4"
        url = f"{base_url}/treasury"

        params = {
            'apikey': self.api_key
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            if data and isinstance(data, list):
                return data
            else:
                print("US Rates: No data returned from API")
                return []

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching US rates: {e}")
            return []

    def _map_api_columns(self, item: dict) -> dict:
        """
        Map FMP API column names to database column names.

        Args:
            item: Dictionary from API response

        Returns:
            Dictionary with mapped column names
        """
        mapped = {}
        for api_col, db_col in self.COLUMN_MAPPING.items():
            if api_col in item and item[api_col] is not None:
                try:
                    mapped[db_col] = float(item[api_col])
                except (ValueError, TypeError):
                    mapped[db_col] = None
            else:
                mapped[db_col] = None
        return mapped

    def update_rates(self) -> int:
        """
        Update US treasury rates with latest data.

        Returns:
            Number of records inserted/updated
        """
        session = MacroDataSession()

        try:
            # Get the last date in database
            last_date = self.get_last_date_in_db(session)

            # Fetch all data from API
            print("US Rates: Fetching data from FMP API...")
            rates_data = self.fetch_rates_from_api()

            if not rates_data:
                print("US Rates: No data available from API")
                return 0

            # Filter to only new data if we have existing data
            if last_date:
                print(f"US Rates: Last date in DB is {last_date}, filtering new records...")

            # Prepare records for insertion
            current_time = get_current_utc_time()
            records = []

            for item in rates_data:
                # Parse date from API response
                try:
                    from datetime import datetime
                    item_date = datetime.strptime(item['date'], '%Y-%m-%d').date()
                except (ValueError, KeyError) as e:
                    print(f"Skipping item with invalid date: {item.get('date')}")
                    continue

                # Skip records we already have
                if last_date and item_date <= last_date:
                    continue

                # Map API columns to DB columns
                rate_values = self._map_api_columns(item)

                # Skip if all rate values are None
                if all(v is None for v in rate_values.values()):
                    continue

                record = {
                    'id': self.US_UUID,
                    'country': 'USA',
                    'date': item_date,
                    'created_at': current_time,
                    'updated_at': current_time,
                    **rate_values
                }
                records.append(record)

            if not records:
                if last_date:
                    print(f"US Rates: Already up to date (last date: {last_date})")
                else:
                    print("US Rates: No valid records to insert")
                return 0

            print(f"US Rates: Inserting {len(records)} new records...")

            # Insert with upsert logic (on conflict, update)
            stmt = insert(GovernmentBondRates).values(records)

            # Build update dict for rate columns
            rate_columns = list(self.COLUMN_MAPPING.values())
            update_dict = {col: stmt.excluded[col] for col in rate_columns}
            update_dict['updated_at'] = current_time

            stmt = stmt.on_conflict_do_update(
                constraint='uq_country_date',
                set_=update_dict
            )

            session.execute(stmt)
            session.commit()

            print(f"US Rates: Successfully inserted/updated {len(records)} records")
            return len(records)

        except Exception as e:
            session.rollback()
            print(f"US Rates: Error during update - {e}")
            raise
        finally:
            session.close()

    def update_with_summary(self):
        """
        Update US rates and print summary.

        Returns:
            Dictionary with summary statistics
        """
        print("Starting US treasury rates update...")
        print("=" * 70)

        try:
            records_added = self.update_rates()
            result = {
                'success': True,
                'records_added': records_added
            }
            self.total_records_added = records_added

        except Exception as e:
            print(f"US Rates: FAILED - {e}")
            result = {
                'success': False,
                'error': str(e)
            }
            self.errors = 1

        # Print summary
        self._print_summary(result)

        return result

    def _print_summary(self, result: dict):
        """Print summary of the update process"""
        print("\n" + "=" * 70)
        print("US TREASURY RATES UPDATE SUMMARY")
        print("=" * 70)
        if result['success']:
            print(f"Status: SUCCESS")
            print(f"Total records inserted/updated: {self.total_records_added:,}")
        else:
            print(f"Status: FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
        print("=" * 70)


