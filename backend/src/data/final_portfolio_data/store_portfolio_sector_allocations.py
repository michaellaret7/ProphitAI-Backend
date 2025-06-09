from __future__ import annotations

"""
Utility to persist the sector-level allocation that comes back from phase-one optimisation into
our Postgres database.

Workflow implemented:
1. Accept the output of phaseOneRun.optimize (either a dict or its JSON string) as the first
   positional argument.
2. Ensure the target database - ``portfolio_results`` - exists.
3. Calculate the next schema name following the convention ``portfolio_<number in words>``.
   If no schema exists yet we start with ``portfolio_one``.
4. Within that schema create (if required) the table ``portfolio_sector_allocation`` and dump the
   allocation rows into it.

The heavy-lifting around database connections / schema+table creation already lives inside the
IBKRDatabase helper (see testing/buildDB.py).  Here we simply orchestrate these calls and keep
this module laser-focused and easy to test.

NOTE: Only the columns that are guaranteed to appear in the optimiser output are pushed
      (``asset_class``, ``allocation``, ``reason``).  Additional keys are ignored.
"""

import json
from typing import Dict, Any, List
import pandas as pd
import os
import uuid # Added for UUID generation
from psycopg2 import connect, sql, extensions
from psycopg2.extras import execute_values, RealDictCursor
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment & DB helpers
# ---------------------------------------------------------------------------

# Load variables from .env if not already available (safe-no-op when called multiple times)
load_dotenv()

DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
USER_NAME = os.environ.get("USER_NAME")

if not all([DB_USER, DB_PASSWORD, DB_HOST, USER_NAME]):
    raise RuntimeError(
        "Database credentials (DB_USER, DB_PASSWORD, DB_HOST) and USER_NAME "
        "must be set in .env or environment"
    )


def _pg_connect(db: str, autocommit: bool = True):
    """
    Create a PostgreSQL database connection.
    
    Args:
        db: The database name to connect to.
        autocommit: Whether to enable autocommit mode (default: True)
        
    Returns:
        psycopg2.connection: Active database connection object.
    """
    conn = connect(
        dbname=db,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    # Register UUID adapter globally for psycopg2
    # extensions.register_adapter(uuid.UUID, AsIs) # Not strictly needed as psycopg2 >2.8 handles UUIDs well
    conn.set_session(autocommit=autocommit)
    return conn


def _ensure_database_exists(db_name: str) -> None:
    """
    Create database if it doesn't exist.
    
    Connects to postgres database and creates the specified database
    if it doesn't already exist.
    
    Args:
        db_name: The name of the database to create.
        
    Returns:
        None
    """
    with _pg_connect("postgres") as conn:
        with conn.cursor() as cur:
            # Ensure pgcrypto extension is available for gen_random_uuid() if used,
            # but we will generate UUID in Python. UUID type itself doesn't need it.
            # cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone():
                return  # already there
            cur.execute(sql.SQL("CREATE DATABASE {}".format(sql.Identifier(db_name).string)))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store_portfolio_sector_allocations(portfolio: dict | str, portfolio_name: str) -> uuid.UUID:
    """
    Store Phase One optimization results to the database.
    
    Persists sector-level portfolio allocations, thesis, and metadata to the
    portfolio_results database using a newly generated UUID as portfolio identifier.
    
    Args:
        portfolio: Dictionary or JSON string containing portfolio allocation data.
        portfolio_name: User-chosen name for this portfolio.
        
    Returns:
        uuid.UUID: The generated portfolio_id from the portfolios table.
        
    Raises:
        ValueError: If portfolio data is invalid or empty.
        TypeError: If portfolio is not dict or string type.
    """
    # ---------------------------------------------------------------------
    # 1. Normalise input
    # ---------------------------------------------------------------------
    if isinstance(portfolio, str):
        try:
            portfolio_dict: Dict[str, Any] = json.loads(portfolio)
        except json.JSONDecodeError as err:
            raise ValueError("`portfolio` parameter is a string but not valid JSON") from err
    elif isinstance(portfolio, dict):
        portfolio_dict = portfolio
    else:
        raise TypeError("`portfolio` must be a dict or JSON string, got %s" % type(portfolio).__name__)

    if "portfolio" not in portfolio_dict or not isinstance(portfolio_dict["portfolio"], list):
        raise ValueError("Input JSON does not contain a 'portfolio' key with a list value")

    portfolio_items: List[Dict[str, Any]] = portfolio_dict["portfolio"]

    if not portfolio_items:
        raise ValueError("Portfolio list is empty – nothing to store")

    # ---------------------------------------------------------------------
    # 2. Convert to DataFrame (clean, simple)
    # ---------------------------------------------------------------------
    df = pd.DataFrame(portfolio_items)

    # We keep only the expected columns to guarantee predictable table structure.
    expected_cols = ["asset_class", "allocation", "reason"]
    df = df[[c for c in expected_cols if c in df.columns]]

    # ---------------------------------------------------------------------
    # 3. Ensure the target database exists & open connection
    # ---------------------------------------------------------------------
    target_db = "portfolio_results"
    _ensure_database_exists(target_db)

    # Use public schema by default
    schema_name = "public"

    with _pg_connect(target_db) as conn:
        # -----------------------------------------------------------------
        # 4. Calculate next schema name - REMOVED, using public schema now
        # -----------------------------------------------------------------
        
        # -----------------------------------------------------------------
        # 5. Create tables (if they don't exist) in the public schema
        # -----------------------------------------------------------------
        portfolios_table = "portfolios"
        portfolio_sector_allocation_table = "portfolio_sector_allocation"
        portfolio_thesis_table = "portfolio_thesis"

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Drop the portfolios table to ensure it's created with the correct UUID type for portfolio_id
            # cur.execute(sql.SQL("DROP TABLE IF EXISTS {schema}.{table} CASCADE;").format(
            #     schema=sql.Identifier(schema_name), table=sql.Identifier(portfolios_table)))
            
            # Create portfolios table with UUID as portfolio_id
            create_portfolios_table_sql = sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    portfolio_id UUID PRIMARY KEY,
                    user_name VARCHAR(255) NOT NULL,
                    portfolio_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT now()
                );
                """
            ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(portfolios_table))
            cur.execute(create_portfolios_table_sql)

            # Always generate a new UUID for each call to this function for a new portfolio instance
            current_portfolio_id = uuid.uuid4()

            # Insert into portfolios table - REMOVED ON CONFLICT clause
            insert_portfolio_sql = sql.SQL(
                """
                INSERT INTO {schema}.{table} (portfolio_id, user_name, portfolio_name)
                VALUES (%s, %s, %s)
                RETURNING portfolio_id; 
                """
            ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(portfolios_table))
            
            cur.execute(
                insert_portfolio_sql, 
                (current_portfolio_id, USER_NAME, portfolio_name)
            )
            result = cur.fetchone()
            # The returned portfolio_id should now always be the newly generated current_portfolio_id
            if result and result['portfolio_id'] == current_portfolio_id:
                pass # Successfully inserted the new UUID
            else:
                # This case should ideally not be reached if INSERT RETURNING works correctly
                # and no other mechanism alters current_portfolio_id.
                # If it does, it indicates a problem with the insert or logic.
                raise Exception(f"Failed to insert/retrieve the new portfolio_id. Expected {current_portfolio_id}, got {result['portfolio_id'] if result else 'None'}")

            # Recreate portfolio_sector_allocation table
            # Dropping for safety during schema change, normally migrations are better
            # cur.execute(sql.SQL("DROP TABLE IF EXISTS {schema}.{table} CASCADE;").format(
            #     schema=sql.Identifier(schema_name), table=sql.Identifier(portfolio_sector_allocation_table)))
            create_psa_table_sql_revised = sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    portfolio_id UUID NOT NULL REFERENCES {schema}.{pf_table}(portfolio_id) ON DELETE CASCADE,
                    user_name VARCHAR(255) NOT NULL,
                    portfolio_name VARCHAR(255) NOT NULL,
                    asset_class VARCHAR(255) NOT NULL,
                    allocation NUMERIC(10,3),
                    reason TEXT,
                    PRIMARY KEY (portfolio_id, asset_class) 
                );
                """
            ).format(
                schema=sql.Identifier(schema_name), 
                table=sql.Identifier(portfolio_sector_allocation_table),
                pf_table=sql.Identifier(portfolios_table)
            )
            cur.execute(create_psa_table_sql_revised)
            
            psa_rows = []
            for item_tuple in df.itertuples(index=False, name=None):
                psa_rows.append((current_portfolio_id, USER_NAME, portfolio_name) + item_tuple)
            
            insert_psa_sql = sql.SQL(
                """
                INSERT INTO {schema}.{table} (portfolio_id, user_name, portfolio_name, asset_class, allocation, reason)
                VALUES %s
                ON CONFLICT (portfolio_id, asset_class) DO UPDATE SET
                    allocation = EXCLUDED.allocation,
                    reason = EXCLUDED.reason,
                    user_name = EXCLUDED.user_name, 
                    portfolio_name = EXCLUDED.portfolio_name;
                """
            ).format(
                schema=sql.Identifier(schema_name), 
                table=sql.Identifier(portfolio_sector_allocation_table)
            )
            execute_values(cur, insert_psa_sql.as_string(conn), psa_rows)

            # Recreate portfolio_thesis table
            # cur.execute(sql.SQL("DROP TABLE IF EXISTS {schema}.{table} CASCADE;").format(
            #     schema=sql.Identifier(schema_name), table=sql.Identifier(portfolio_thesis_table)))
            create_thesis_table_sql_revised = sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    portfolio_id UUID PRIMARY KEY REFERENCES {schema}.{pf_table}(portfolio_id) ON DELETE CASCADE,
                    user_name VARCHAR(255) NOT NULL, 
                    portfolio_name VARCHAR(255) NOT NULL, 
                    generated_at TIMESTAMP DEFAULT now(),
                    thesis TEXT NOT NULL,
                    extra JSONB DEFAULT '{{}}'::jsonb
                );
                """
            ).format(
                schema=sql.Identifier(schema_name), 
                table=sql.Identifier(portfolio_thesis_table),
                pf_table=sql.Identifier(portfolios_table)
            )
            cur.execute(create_thesis_table_sql_revised)

            thesis_text = portfolio_dict.get("portfolio_thesis")
            if thesis_text:
                insert_thesis_sql = sql.SQL(
                    """
                    INSERT INTO {schema}.{table} (portfolio_id, user_name, portfolio_name, thesis) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        thesis = EXCLUDED.thesis,
                        user_name = EXCLUDED.user_name,
                        portfolio_name = EXCLUDED.portfolio_name,
                        generated_at = EXCLUDED.generated_at;
                    """
                ).format(
                    schema=sql.Identifier(schema_name), 
                    table=sql.Identifier(portfolio_thesis_table)
                )
                cur.execute(insert_thesis_sql, (current_portfolio_id, USER_NAME, portfolio_name, thesis_text))

        conn.commit()

    return current_portfolio_id

# ---------------------------------------------------------------------------
# Helper utilities - REMOVED _num_to_words_mapping, _int_to_english, _english_word_to_int_map
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: Ensure USER_NAME is in your .env or environment for this test
    if not USER_NAME:
        print("Please set USER_NAME in your environment for the test to run.")
    else:
        # The f-string with uuid.uuid4().hex[:8] ensures unique portfolio name for each test run
        test_portfolio_name = f"MyTestPortfolio_{uuid.uuid4().hex[:8]}" 
        
        # Sample data for store_portfolio_sector_allocations
        sector_portfolio_data = {
            "portfolio": [
                {
                    "asset_class": "semiconductors",
                    "allocation": 10.5,
                    "reason": "Strong growth in AI sector."
                },
                {
                    "asset_class": "renewable_energy",
                    "allocation": 15.0,
                    "reason": "Government incentives and increasing demand."
                },
                {
                    "asset_class": "Cash",
                    "allocation": 5.0,
                    "reason": "Strategic liquidity."
                }
            ],
            "portfolio_thesis": "This is a test thesis for the comprehensive portfolio."
        }

        # Sample data for store_final_portfolio 
        # (structure this like the output of make_phaseTwo_recommendations)
        final_portfolio_data = {
            "semiconductors": {
                "total_stocks_analyzed": 2,
                "recommendations": [
                    {
                        "ticker": "NVDA",
                        "reason_for_recommendation": "Leading AI chip manufacturer.",
                        "supporting_metrics": {"sharpe_ratio": 2.1, "operating_margin_avg": "60%"},
                        "allocation": 7.5
                    },
                    {
                        "ticker": "AMD",
                        "reason_for_recommendation": "Competitive CPU and GPU offerings.",
                        "supporting_metrics": {"beta": 1.2, "revenue_growth": "20%"},
                        "allocation": 3.0
                    }
                ]
            },
            "renewable_energy": {
                "total_stocks_analyzed": 1,
                "recommendations": [
                    {
                        "ticker": "NEE",
                        "reason_for_recommendation": "Largest renewable energy producer.",
                        "supporting_metrics": {"dividend_yield": "3%", "payout_ratio": "60%"},
                        "allocation": 15.0
                    }
                ]
            }
            # "Cash" asset class usually doesn't have ticker recommendations in this structure
        }

        try:
            print(f"--- Running Test for User: {USER_NAME}, Portfolio: {test_portfolio_name} ---")
            
            # 1. Store sector allocations and thesis, get portfolio_id
            print("1. Storing sector allocations and thesis...")
            created_portfolio_id = store_portfolio_sector_allocations(sector_portfolio_data, test_portfolio_name)
            print(f"   Successfully stored. Portfolio UUID: {created_portfolio_id}")

            # 2. Store final portfolio (ticker details)
            # Need to import store_final_portfolio at the top of the file if not already done for __main__
            from .store_final_portfolio import store_final_portfolio
            print("\n2. Storing final portfolio (ticker details)...")
            store_final_portfolio(final_portfolio_data, created_portfolio_id, test_portfolio_name)
            print(f"   Successfully stored final portfolio details for Portfolio UUID: {created_portfolio_id}")

            # 3. Store user information
            # Need to import store_user_information at the top of the file if not already done for __main__
            from .store_user_information import store_user_information
            # (Assuming get_user_information() in store_user_information.py fetches/returns some mock data for testing)
            print("\n3. Storing user information...")
            store_user_information(created_portfolio_id, test_portfolio_name)
            print(f"   Successfully stored user information for Portfolio UUID: {created_portfolio_id}")

            print("\n--- Test Completed Successfully ---")
            print(f"Check your 'portfolio_results' database, public schema, for portfolio_id = {created_portfolio_id}.")

        except Exception as e:
            print(f"--- Test Failed --- ")
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()