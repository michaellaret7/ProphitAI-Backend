from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from backend.src.utils.database import get_connection
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class FundamentalDataRepository:
    def __init__(self):
        self.possible_databases = [
            "equity_sector_communication_services_fundamentals",
            "equity_sector_consumer_discretionary_fundamentals",
            "equity_sector_consumer_staples_fundamentals",
            "equity_sector_energy_fundamentals",
            "equity_sector_financials_fundamentals",
            "equity_sector_health_care_fundamentals",
            "equity_sector_industrials_fundamentals",
            "equity_sector_information_technology_fundamentals",
            "equity_sector_materials_fundamentals",
            "equity_sector_real_estate_fundamentals",
            "equity_sector_utilities_fundamentals"
        ]

    def _fetch_data(self, report_type: str, ticker: str) -> List[Dict]:
        """
        Generic method to fetch fundamental data for a ticker.
        It searches for the right table across multiple databases.
        """
        ticker_lower = ticker.lower()
        table_to_find = f"{ticker_lower}_{report_type}"

        for db_name in self.possible_databases:
            conn = get_connection(db_name)
            if not conn:
                continue

            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Find which schema contains the ticker's report table
                    cursor.execute("""
                        SELECT schemaname
                        FROM pg_tables
                        WHERE tablename = %s
                    """, (table_to_find,))

                    table_info = cursor.fetchone()
                    if table_info:
                        schema_name = table_info['schemaname']

                        # Now query the actual data
                        cursor.execute(f'SELECT * FROM "{schema_name}"."{table_to_find}"')

                        rows = cursor.fetchall()

                        if not rows:
                            return []

                        data = []
                        for row in rows:
                            row_dict = dict(row)
                            for key, value in row_dict.items():
                                if isinstance(value, Decimal):
                                    row_dict[key] = float(value)
                                elif isinstance(value, str) and key not in ['ticker', 'currency', 'period']:
                                    # Try to convert string numeric values to float
                                    try:
                                        row_dict[key] = float(value)
                                    except (ValueError, TypeError):
                                        # Keep as string if it's not a numeric value
                                        pass
                            data.append(row_dict)
                        
                        conn.close()
                        return data

            except psycopg2.Error as e:
                print(f"Error searching in {db_name}: {e}")
                continue
            finally:
                if conn:
                    conn.close()
        
        print(f"Data for ticker '{ticker}' with report type '{report_type}' not found in any database.")
        return []

    def fetch_balance_sheet(self, ticker: str) -> List[Dict]:
        """ Fetches balance sheet data for a given ticker. """
        return self._fetch_data("balance_sheets", ticker)

    def fetch_cash_flow_statement(self, ticker: str) -> List[Dict]:
        """ Fetches cash flow statement data for a given ticker. """
        return self._fetch_data("cash_flow_statements", ticker)

    def fetch_income_statement(self, ticker: str) -> List[Dict]:
        """ Fetches income statement data for a given ticker. """
        return self._fetch_data("income_statements", ticker)

    def fetch_financial_metrics(self, ticker: str) -> List[Dict]:
        """ Fetches financial metrics for a given ticker. """
        return self._fetch_data("financial_metrics", ticker)

    def fetch_fundamental_report(self, ticker: str) -> List[Dict]:
        """ Fetches the fundamental report for a given ticker. """
        reports = self._fetch_data("fundamental_report", ticker)
        if reports:
            logger.info("Successfully fetched fundamental report for %s", ticker)
            for report in reports:
                timestamp = report.get("generation_timestamp")
                if timestamp:
                    report["generation_timestamp"] = timestamp.isoformat()
            return reports
        else:
            logger.warning("No fundamental report found for %s", ticker)
            return []

    def fetch_fundamental_estimates(self, ticker: str) -> List[Dict]:
        """ Fetches fundamental estimates for a given ticker. """
        estimates = self._fetch_data("fundamental_estimates", ticker)
        if estimates:
            logger.info("Successfully fetched %d fundamental estimates for %s", len(estimates), ticker)
            for estimate in estimates:
                timestamp = estimate.get("generation_timestamp")
                if timestamp:
                    estimate["generation_timestamp"] = timestamp.isoformat()
            return estimates
        else:
            logger.warning("No fundamental estimates found for %s", ticker)
            return []

