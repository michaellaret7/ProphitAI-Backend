"""
Update Economic Calendar Table

This module updates the economic_calendar table with scheduled economic events
and releases from FMP API. Includes both historical events and future forecasts.
"""
import os
import requests
from datetime import datetime, timedelta, date
from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from dotenv import load_dotenv

from prophitai_data.db.config import MacroDataSession
from prophitai_data.db.models.macro import EconomicCalendar
from prophitai_shared import get_current_utc_time

load_dotenv()


class UpdateEconomicCalendar:
    """Updates economic calendar events from FMP API"""

    # Country UUID mapping (matches gov_bond_rates table)
    COUNTRIES = {
        'US': uuid5(NAMESPACE_DNS, 'country.US'),
        'GB': uuid5(NAMESPACE_DNS, 'country.GB'),
        'DE': uuid5(NAMESPACE_DNS, 'country.DE'),
        'FR': uuid5(NAMESPACE_DNS, 'country.FR'),
        'IT': uuid5(NAMESPACE_DNS, 'country.IT'),
        'JP': uuid5(NAMESPACE_DNS, 'country.JP'),
        'CA': uuid5(NAMESPACE_DNS, 'country.CA'),
        'AU': uuid5(NAMESPACE_DNS, 'country.AU'),
        'CN': uuid5(NAMESPACE_DNS, 'country.CN'),
        'IN': uuid5(NAMESPACE_DNS, 'country.IN'),
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
        Find the last date available in the database.

        Args:
            session: Database session

        Returns:
            Last date in database, or None if no data exists
        """
        try:
            result = session.query(
                func.max(EconomicCalendar.date)
            ).scalar()

            if result:
                return result.date()  # Convert datetime to date
            return None
        except Exception as e:
            print(f"Error getting last date: {e}")
            return None

    def fetch_calendar_data_from_api(
        self,
        from_date: str,
        to_date: str
    ) -> list[dict]:
        """
        Fetch economic calendar events from FMP API.

        Args:
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format

        Returns:
            List of dictionaries containing calendar events
        """
        base_url = "https://financialmodelingprep.com/api/v3"
        url = f"{base_url}/economic_calendar"

        params = {
            'apikey': self.api_key,
            'from': from_date,
            'to': to_date
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data and isinstance(data, list):
                return data
            else:
                print(f"No calendar data returned from {from_date} to {to_date}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching calendar data: {e}")
            return []

    def update_calendar(self) -> int:
        """
        Update economic calendar with latest events.

        Returns:
            Number of records inserted/updated
        """
        session = MacroDataSession()

        try:
            # Get the last date in database
            last_date = self.get_last_date_in_db(session)

            # Determine the date range for fetching
            if last_date:
                # Start from the day after the last date
                start_date = last_date + timedelta(days=1)
            else:
                # No data exists, fetch from 1 year ago
                start_date = get_current_utc_time().date() - timedelta(days=365)

            # End date is 1 year in the future (for upcoming events)
            end_date = get_current_utc_time().date() + timedelta(days=365)

            # Check if we need to fetch data
            if start_date > end_date:
                print(f"Economic Calendar: Already up to date (last date: {last_date})")
                return 0

            print(f"Economic Calendar: Fetching data from {start_date} to {end_date}")

            # Fetch data from API
            calendar_data = self.fetch_calendar_data_from_api(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if not calendar_data:
                print("Economic Calendar: No new data available")
                return 0

            # Prepare records for insertion
            current_time = get_current_utc_time()
            records = []

            for item in calendar_data:
                # Parse date from the API response
                try:
                    item_date = datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, KeyError):
                    # Try alternative format
                    try:
                        item_date = datetime.strptime(item['date'], '%Y-%m-%d')
                    except (ValueError, KeyError):
                        print(f"Skipping item with invalid date: {item.get('date')}")
                        continue

                # Get country code and UUID
                country_code = item.get('country', 'US')
                country_uuid = self.COUNTRIES.get(country_code, self.COUNTRIES['US'])

                # Parse numeric fields safely
                def safe_float(value):
                    if value is None or value == '' or value == 'N/A':
                        return None
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None

                records.append({
                    'id': country_uuid,
                    'event': item.get('event', '')[:500],  # Limit to 500 chars
                    'date': item_date,
                    'country': country_code,
                    'currency': item.get('currency', None),
                    'actual': safe_float(item.get('actual')),
                    'previous': safe_float(item.get('previous')),
                    'estimate': safe_float(item.get('estimate')),
                    'change': safe_float(item.get('change')),
                    'change_percentage': safe_float(item.get('changePercentage')),
                    'impact': item.get('impact', None),
                    'created_at': current_time,
                    'updated_at': current_time
                })

            # Insert with upsert logic (on conflict, update)
            if records:
                stmt = insert(EconomicCalendar).values(records)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_event_date_country',
                    set_={
                        'currency': stmt.excluded.currency,
                        'actual': stmt.excluded.actual,
                        'previous': stmt.excluded.previous,
                        'estimate': stmt.excluded.estimate,
                        'change': stmt.excluded.change,
                        'change_percentage': stmt.excluded.change_percentage,
                        'impact': stmt.excluded.impact,
                        'updated_at': current_time
                    }
                )

                session.execute(stmt)
                session.commit()

                print(f"Economic Calendar: Successfully inserted/updated {len(records)} records")
                return len(records)

            return 0

        except Exception as e:
            session.rollback()
            print(f"Economic Calendar: Error during update - {e}")
            raise
        finally:
            session.close()

    def update_with_summary(self):
        """
        Update economic calendar and print summary.

        Returns:
            Dictionary with summary statistics
        """
        print("Starting economic calendar update...")
        print("=" * 70)

        try:
            records_added = self.update_calendar()
            result = {
                'success': True,
                'records_added': records_added
            }
            self.total_records_added = records_added

        except Exception as e:
            print(f"Economic Calendar: FAILED - {e}")
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
        print("ECONOMIC CALENDAR UPDATE SUMMARY")
        print("=" * 70)
        if result['success']:
            print(f"Status: SUCCESS")
            print(f"Total records inserted/updated: {self.total_records_added:,}")
        else:
            print(f"Status: FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
        print("=" * 70)
