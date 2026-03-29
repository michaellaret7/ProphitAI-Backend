"""
Update Economic Indicators Table

This module updates the economic_indicators table with the latest data from FMP API.
Tracks key US economic indicators like GDP, unemployment, CPI, etc.
"""
import os
import requests
from datetime import datetime, timedelta, date
from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from dotenv import load_dotenv

from prophitai_data.db.config import MacroDataSession
from prophitai_data.db.models.macro import EconomicIndicators
from prophitai_shared import get_current_utc_time

load_dotenv()


class UpdateEconomicIndicators:
    """Updates economic indicator data from FMP API"""

    # Economic indicators to track
    INDICATORS = [
        'GDP',
        'realGDP',
        'nominalPotentialGDP',
        'realGDPPerCapita',
        'federalFunds',
        'CPI',
        'inflationRate',
        'inflation',
        'retailSales',
        'consumerSentiment',
        'durableGoods',
        'unemploymentRate',
        'totalNonfarmPayroll',
        'initialClaims',
        'industrialProductionTotalIndex',
        'newPrivatelyOwnedHousingUnitsStartedTotalUnits',
        'totalVehicleSales',
        'retailMoneyFunds',
        'smoothedUSRecessionProbabilities',
        'nonFarmPayrollEmployment',
    ]

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable not found")

        # Progress tracking
        self.total_indicators = 0
        self.processed = 0
        self.errors = 0
        self.total_records_added = 0

    @staticmethod
    def get_indicator_uuid(indicator: str):
        """
        Generate a deterministic UUID for an economic indicator.
        Same indicator always gets the same UUID.

        Args:
            indicator: Economic indicator name (e.g., 'GDP')

        Returns:
            UUID for the indicator
        """
        return uuid5(NAMESPACE_DNS, f"economic_indicator.{indicator}")

    def get_last_date_in_db(self, session, indicator: str) -> date | None:
        """
        Find the last date available in the database for a given indicator.

        Args:
            session: Database session
            indicator: Economic indicator name

        Returns:
            Last date in database, or None if no data exists
        """
        try:
            result = session.query(
                func.max(EconomicIndicators.date)
            ).filter(
                EconomicIndicators.indicator == indicator
            ).scalar()

            return result
        except Exception as e:
            print(f"Error getting last date for {indicator}: {e}")
            return None

    def fetch_indicator_data_from_api(
        self,
        indicator: str,
        from_date: str,
        to_date: str
    ) -> list[dict]:
        """
        Fetch economic indicator data from FMP API.

        Args:
            indicator: Economic indicator name
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format

        Returns:
            List of dictionaries containing indicator data
        """
        base_url = "https://financialmodelingprep.com/api/v4"
        url = f"{base_url}/economic"

        params = {
            'apikey': self.api_key,
            'name': indicator,
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
                print(f"No data returned for {indicator} from {from_date} to {to_date}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"API request failed for {indicator}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching {indicator}: {e}")
            return []

    def update_indicator(self, indicator: str) -> int:
        """
        Update a single economic indicator with latest data.

        Args:
            indicator: Economic indicator name to update

        Returns:
            Number of records inserted/updated
        """
        session = MacroDataSession()

        try:
            # Get the last date in database
            last_date = self.get_last_date_in_db(session, indicator)

            # Determine the date range for fetching
            if last_date:
                # Start from the day after the last date
                start_date = last_date + timedelta(days=1)
            else:
                # No data exists, fetch from a reasonable historical date
                # Fetch last 30 years of data for new indicators
                start_date = get_current_utc_time().date() - timedelta(days=365 * 30)

            # End date is current UTC date
            end_date = get_current_utc_time().date()

            # Check if we need to fetch data
            if start_date > end_date:
                print(f"{indicator}: Already up to date (last date: {last_date})")
                return 0

            print(f"{indicator}: Fetching data from {start_date} to {end_date}")

            # Fetch data from API
            historical_data = self.fetch_indicator_data_from_api(
                indicator,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if not historical_data:
                print(f"{indicator}: No new data available")
                return 0

            # Prepare records for insertion
            indicator_uuid = self.get_indicator_uuid(indicator)
            current_time = get_current_utc_time()

            records = []
            for item in historical_data:
                # Parse date from the API response
                item_date = datetime.strptime(item['date'], '%Y-%m-%d').date()

                records.append({
                    'id': indicator_uuid,
                    'indicator': indicator,
                    'date': item_date,
                    'value': float(item['value']) if item.get('value') is not None else None,
                    'created_at': current_time,
                    'updated_at': current_time
                })

            # Insert with upsert logic (on conflict, update)
            if records:
                stmt = insert(EconomicIndicators).values(records)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_indicator_date',
                    set_={
                        'value': stmt.excluded.value,
                        'updated_at': current_time
                    }
                )

                session.execute(stmt)
                session.commit()

                print(f"{indicator}: Successfully inserted/updated {len(records)} records")
                return len(records)

            return 0

        except Exception as e:
            session.rollback()
            print(f"{indicator}: Error during update - {e}")
            raise
        finally:
            session.close()

    def update_all_indicators(self):
        """
        Update all economic indicators in the INDICATORS list.

        Returns:
            Dictionary with summary statistics
        """
        self.total_indicators = len(self.INDICATORS)
        self.processed = 0
        self.errors = 0
        self.total_records_added = 0

        print(f"Starting economic indicators update for {self.total_indicators} indicators...")
        print("=" * 70)

        results = {}

        for indicator in self.INDICATORS:
            try:
                records_added = self.update_indicator(indicator)
                results[indicator] = {
                    'success': True,
                    'records_added': records_added
                }
                self.total_records_added += records_added
                self.processed += 1

            except Exception as e:
                print(f"{indicator}: FAILED - {e}")
                results[indicator] = {
                    'success': False,
                    'error': str(e)
                }
                self.errors += 1
                self.processed += 1

        # Print summary
        self._print_summary(results)

        return results

    def _print_summary(self, results: dict):
        """Print summary of the update process"""
        successful = sum(1 for r in results.values() if r['success'])

        print("\n" + "=" * 70)
        print("ECONOMIC INDICATORS UPDATE SUMMARY")
        print("=" * 70)
        print(f"Total indicators: {self.total_indicators}")
        print(f"Successfully updated: {successful}")
        print(f"Failed: {self.errors}")
        print(f"Total records inserted/updated: {self.total_records_added:,}")
        print("=" * 70)

        # Show details for failed indicators
        if self.errors > 0:
            print("\nFailed indicators:")
            for indicator, result in results.items():
                if not result['success']:
                    print(f"  {indicator}: {result.get('error', 'Unknown error')}")
            print("=" * 70)
