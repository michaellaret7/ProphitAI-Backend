from backend.src.utils.database import get_connection
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, Union, List, Optional
from uuid import UUID
import json

class PushUserCreatedPortfolioRepository:
    def __init__(self):
        pass
    
    # helper function
    def _ensure_portfolio_exists(self, cursor, portfolio_id: UUID, portfolio_name: str, user_id: str, email: str) -> None:
        """Helper function to ensure the portfolio exists in the parent portfolios table."""
        cursor.execute("""
            INSERT INTO public.portfolios (portfolio_id, portfolio_name, user_id, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (portfolio_id) DO UPDATE SET
                portfolio_name = EXCLUDED.portfolio_name,
                user_id = EXCLUDED.user_id,
                email = EXCLUDED.email
        """, (portfolio_id, portfolio_name, user_id, email))
    
    # helper function
    def _parse_portfolio_json(self, portfolio: Union[Dict, str]) -> Optional[Dict]:
        """Helper function to parse portfolio data from string or dict."""
        if isinstance(portfolio, str):
            try:
                return json.loads(portfolio)
            except json.JSONDecodeError:
                print("Error: portfolio string is not valid JSON")
                return None

        if isinstance(portfolio, dict):
            return portfolio
        
        print("Error: portfolio must be a dictionary or valid JSON string")
        return None
    
    def store_final_portfolio(
        self,
        portfolio: Union[Dict, str],
        portfolio_id: UUID,
        portfolio_name: str,
        user_id: str,
        email: str
    ) -> None:
        conn = get_connection("portfolio_results")
        if not conn:
            return

        # Parse portfolio data
        portfolio = self._parse_portfolio_json(portfolio)
        if portfolio is None:
            return

        data_to_insert = []
        for asset_class, asset_data in portfolio.items():
            # Handle both old format (direct list) and new format (dict with 'recommendations' key)
            if isinstance(asset_data, dict) and 'recommendations' in asset_data:
                # New format: extract recommendations list
                assets = asset_data['recommendations']
            elif isinstance(asset_data, list):
                # Old format: direct list of assets
                assets = asset_data
            else:
                print(f"Warning: Unexpected format for asset class {asset_class}, skipping")
                continue
                
            for asset in assets:
                # Ensure supporting_metrics is a JSON string
                supporting_metrics = asset.get('supporting_metrics')
                if not isinstance(supporting_metrics, str):
                    supporting_metrics = json.dumps(supporting_metrics)

                # Handle both 'reason' and 'reason_for_recommendation' field names
                reason = asset.get('reason') or asset.get('reason_for_recommendation')

                data_to_insert.append((
                    portfolio_id,
                    user_id,
                    email,
                    portfolio_name,
                    asset_class,
                    asset.get('ticker'),
                    asset.get('allocation'),
                    reason,
                    supporting_metrics
                ))

        if not data_to_insert:
            return

        try:
            with conn.cursor() as cursor:
                # Ensure the portfolio exists in the parent 'portfolios' table
                self._ensure_portfolio_exists(cursor, portfolio_id, portfolio_name, user_id, email)

                query = """
                    INSERT INTO public.final_portfolio
                    (portfolio_id, user_id, email, portfolio_name, asset_class, ticker, allocation, reason, supporting_metrics)
                    VALUES %s
                    ON CONFLICT (portfolio_id, asset_class, ticker) DO UPDATE SET
                        allocation = EXCLUDED.allocation,
                        reason = EXCLUDED.reason,
                        supporting_metrics = EXCLUDED.supporting_metrics,
                        user_id = EXCLUDED.user_id,
                        email = EXCLUDED.email,
                        portfolio_name = EXCLUDED.portfolio_name;
                """
                execute_values(
                    cursor,
                    query,
                    data_to_insert,
                    page_size=100
                )
                conn.commit()
        except psycopg2.Error as e:
            print(f"Error storing portfolio: {e}")
            conn.rollback()
        finally:
            conn.close()

    def store_sector_allocations(
        self,
        portfolio: Union[Dict, str],
        portfolio_id: UUID,
        portfolio_name: str,
        user_id: str,
        email: str
    ) -> bool:
        """Store sector-level portfolio allocations in the database.
        
        Returns True if successful, False otherwise.
        """
        conn = get_connection("portfolio_results")
        if not conn:
            return False

        # Parse portfolio data
        portfolio = self._parse_portfolio_json(portfolio)
        if portfolio is None:
            return False

        # Extract portfolio items - expecting structure with 'portfolio' key containing list
        portfolio_items = portfolio.get('portfolio', [])
        if not isinstance(portfolio_items, list) or not portfolio_items:
            print("Error: portfolio must contain a 'portfolio' key with a list of allocations")
            return False

        # Prepare data for insertion
        data_to_insert = []
        for item in portfolio_items:
            if not isinstance(item, dict):
                continue
                
            data_to_insert.append((
                portfolio_id,
                user_id,
                email,
                portfolio_name,
                item.get('asset_class'),
                item.get('allocation'),
                item.get('reason')
            ))

        if not data_to_insert:
            print("Error: No valid sector allocation data to insert")
            return False

        try:
            with conn.cursor() as cursor:
                # Ensure portfolio exists in parent table
                self._ensure_portfolio_exists(cursor, portfolio_id, portfolio_name, user_id, email)

                # Insert sector allocations
                query = """
                    INSERT INTO public.portfolio_sector_allocation
                    (portfolio_id, user_id, email, portfolio_name, asset_class, allocation, reason)
                    VALUES %s
                    ON CONFLICT (portfolio_id, asset_class) DO UPDATE SET
                        allocation = EXCLUDED.allocation,
                        reason = EXCLUDED.reason,
                        user_id = EXCLUDED.user_id,
                        email = EXCLUDED.email,
                        portfolio_name = EXCLUDED.portfolio_name
                """
                execute_values(cursor, query, data_to_insert, page_size=100)
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            print(f"Error storing sector allocations: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def store_portfolio(
        self,
        portfolio_name: str,
        user_id: str,
        email: str
    ) -> Optional[UUID]:
        """Create a new portfolio entry in the portfolios table and return the generated UUID.
        
        Returns the portfolio_id if successful, None otherwise.
        """
        from uuid import uuid4
        
        conn = get_connection("portfolio_results")
        if not conn:
            return None

        # Generate a new UUID for this portfolio
        portfolio_id = uuid4()

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO public.portfolios (portfolio_id, user_id, email, portfolio_name)
                    VALUES (%s, %s, %s, %s)
                    RETURNING portfolio_id
                """, (portfolio_id, user_id, email, portfolio_name))
                
                result = cursor.fetchone()
                conn.commit()
                
                if result and result[0] == portfolio_id:
                    return portfolio_id
                else:
                    print(f"Failed to create portfolio. Expected {portfolio_id}, got {result[0] if result else 'None'}")
                    return None
                    
        except psycopg2.Error as e:
            print(f"Error creating portfolio: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def store_portfolio_thesis(
        self,
        portfolio_id: UUID,
        portfolio_name: str,
        thesis: str,
        user_id: str,
        email: str
    ) -> bool:
        """Store portfolio thesis in the database.
        
        Returns True if successful, False otherwise.
        """
        conn = get_connection("portfolio_results")
        if not conn:
            return False

        if not thesis or not thesis.strip():
            print("Error: thesis cannot be empty")
            return False

        try:
            with conn.cursor() as cursor:
                # Ensure portfolio exists in parent table
                self._ensure_portfolio_exists(cursor, portfolio_id, portfolio_name, user_id, email)

                # Insert portfolio thesis
                cursor.execute("""
                    INSERT INTO public.portfolio_thesis (portfolio_id, user_id, email, portfolio_name, thesis)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        thesis = EXCLUDED.thesis,
                        user_id = EXCLUDED.user_id,
                        email = EXCLUDED.email,
                        portfolio_name = EXCLUDED.portfolio_name,
                        generated_at = DEFAULT
                """, (portfolio_id, user_id, email, portfolio_name, thesis))

                conn.commit()
                return True
                
        except psycopg2.Error as e:
            print(f"Error storing portfolio thesis: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def store_user_information(
        self,
        portfolio_id: UUID,
        portfolio_name: str,
        user_id: str,
        email: str,
        user_profile: Union[Dict, str]
    ) -> bool:
        """Store user information/profile data in the database.
        
        Returns True if successful, False otherwise.
        """
        conn = get_connection("portfolio_results")
        if not conn:
            return False

        # Parse user profile data
        user_profile = self._parse_portfolio_json(user_profile)
        if user_profile is None:
            return False

        try:
            with conn.cursor() as cursor:
                # Ensure portfolio exists in parent table
                self._ensure_portfolio_exists(cursor, portfolio_id, portfolio_name, user_id, email)

                # Insert user information
                cursor.execute("""
                    INSERT INTO public.user_information (portfolio_id, user_id, email, portfolio_name, profile)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        email = EXCLUDED.email,
                        portfolio_name = EXCLUDED.portfolio_name,
                        profile = EXCLUDED.profile,
                        created_at = DEFAULT
                """, (portfolio_id, user_id, email, portfolio_name, json.dumps(user_profile)))

                conn.commit()
                return True
                
        except psycopg2.Error as e:
            print(f"Error storing user information: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

