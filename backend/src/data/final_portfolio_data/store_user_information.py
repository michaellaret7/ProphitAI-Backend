from __future__ import annotations

"""
Persist the user profile information into the same *portfolio_<n>* schema that
holds the portfolio data.

The module looks for the *latest* portfolio schema (highest number) in the
`portfolio_results` database and writes the payload returned from
`get_user_information()` into a table named ``user_information``.

Table definition
----------------
created_at      TIMESTAMP  DEFAULT now()
profile         JSONB      NOT NULL

The whole object is kept in one JSONB column to avoid migrations when the
profile structure changes.
"""

import json
import re
from typing import Dict, Any
import os
import uuid

from psycopg2 import sql
from psycopg2.extras import Json

from ..user_information import get_user_information
from .store_portfolio_sector_allocations import (
    _pg_connect,
    _ensure_database_exists,
)

__all__ = ["store_user_information"]

# Added: Get USER_NAME from environment
USER_NAME = os.environ.get("USER_NAME")
if not USER_NAME:
    print("Warning: USER_NAME environment variable is not set. It will be required by a calling function.")

def store_user_information(
    portfolio_id: uuid.UUID,
    portfolio_name: str
) -> None:
    """
    Store user profile information linked to a portfolio.
    
    Fetches user information via get_user_information() and persists it
    to the public.user_information table as JSONB data.
    
    Args:
        portfolio_id: The UUID of the portfolio this user information snapshot is associated with.
        portfolio_name: The name of the portfolio.
        
    Returns:
        None
    """

    user_payload: Dict[str, Any] = get_user_information()

    # ------------------------------------------------------------------
    # 1. Prepare DB & determine schema to use (fixed to public)
    # ------------------------------------------------------------------
    target_db = "portfolio_results"
    _ensure_database_exists(target_db)

    schema_to_use = "public"

    # ------------------------------------------------------------------
    # 2. Create table and insert profile into the public schema
    # ------------------------------------------------------------------
    with _pg_connect(target_db) as conn:
        table = "user_information"
        portfolios_table = "portfolios"

        with conn.cursor() as cur:
            # REMOVED: cur.execute(sql.SQL("DROP TABLE IF EXISTS {schema}.{table} CASCADE;").format(...))
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {schema}.{table} (
                        portfolio_id UUID PRIMARY KEY REFERENCES {schema}.{pf_table}(portfolio_id) ON DELETE CASCADE,
                        user_name VARCHAR(255) NOT NULL,
                        portfolio_name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT now(),
                        profile JSONB NOT NULL
                    );
                    """
                ).format(
                    schema=sql.Identifier(schema_to_use), 
                    table=sql.Identifier(table),
                    pf_table=sql.Identifier(portfolios_table)
                )
            )

            insert_sql = sql.SQL(
                """INSERT INTO {schema}.{table} (portfolio_id, user_name, portfolio_name, profile) 
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (portfolio_id) DO UPDATE SET
                       user_name = EXCLUDED.user_name,
                       portfolio_name = EXCLUDED.portfolio_name,
                       profile = EXCLUDED.profile,
                       created_at = EXCLUDED.created_at;
                """
            ).format(schema=sql.Identifier(schema_to_use), table=sql.Identifier(table))
            
            cur.execute(insert_sql, (portfolio_id, USER_NAME, portfolio_name, Json(user_payload)))
            conn.commit()


