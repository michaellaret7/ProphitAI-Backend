from __future__ import annotations

"""
Persist ticker-level allocation recommendations (Phase Two output) into our Postgres
`portfolio_results` database.

Behaviour
---------
1. Accept a dict or JSON string that follows the structure produced by
   `make_phaseTwo_recommendations` – see *testing/recentOutput.txt*.
2. Detect the most recent `portfolio_<n>` schema (created earlier by
   `store_portfolio_sector_allocations`) and create/use that schema.  If none
   exists, start with ``portfolio_one``.
3. In that schema create a table ``final_portfolio`` (if it does not already
   exist) with columns:
   • asset_class          VARCHAR
   • ticker               VARCHAR
   • allocation           NUMERIC
   • reason               TEXT
   • supporting_metrics   JSONB
   The composite (asset_class, ticker) acts as primary key to allow idempotent
   re-runs.
4. Bulk-insert / upsert the rows.
"""

import json
from typing import Dict, Any, List, Tuple
import re
from psycopg2 import sql
from psycopg2.extras import execute_values
import os
import uuid # Added for UUID type hint

# Re-use the connection helpers from the sibling module to avoid duplication
from .store_portfolio_sector_allocations import (
    _pg_connect,
    _ensure_database_exists,
)

__all__ = ["store_final_portfolio"]

# Added: Get USER_NAME from environment
USER_NAME = os.environ.get("USER_NAME")
if not USER_NAME:
    # This module relies on USER_NAME being set.
    # It's also checked in store_portfolio_sector_allocations, but good to have a local check/awareness.
    print("Warning: USER_NAME environment variable is not set. It will be required by a calling function.")

def store_final_portfolio(
    portfolio: dict | str, 
    portfolio_id: uuid.UUID, # Changed type to uuid.UUID
    portfolio_name: str
) -> None:
    """Store *portfolio* ticker details into the public.final_portfolio table.

    Parameters
    ----------
    portfolio
        The portfolio data to store (ticker-level recommendations).
    portfolio_id
        The UUID of the portfolio this data belongs to.
    portfolio_name
        The name of the portfolio this data belongs to.
    """

    # ------------------------------------------------------------------
    # 1. Normalise / validate input
    # ------------------------------------------------------------------
    if isinstance(portfolio, str):
        try:
            portfolio_dict: Dict[str, Any] = json.loads(portfolio)
        except json.JSONDecodeError as err:
            raise ValueError("`portfolio` string is not valid JSON") from err
    elif isinstance(portfolio, dict):
        portfolio_dict = portfolio
    else:
        raise TypeError("`portfolio` must be dict or JSON str, got %s" % type(portfolio).__name__)

    if not portfolio_dict:
        raise ValueError("Portfolio payload is empty – nothing to persist")

    # ------------------------------------------------------------------
    # 2. Flatten the nested structure into rows
    # ------------------------------------------------------------------
    rows: List[Tuple[uuid.UUID, str, str, str, str, float, str, str]] = [] # Changed portfolio_id type

    for asset_class, info in portfolio_dict.items():
        # Skip entries that are not dicts or contain error message only
        if not isinstance(info, dict):
            continue

        recs = info.get("recommendations", [])
        if not recs:
            # skip asset_class with no recommendations (maybe contains 'error')
            continue

        for rec in recs:
            ticker = rec.get("ticker")
            if not ticker:
                continue  # malformed entry

            allocation = rec.get("allocation")
            # Convert allocation to float if possible
            try:
                allocation_float = float(allocation) if allocation is not None else None
            except (ValueError, TypeError):
                allocation_float = None

            reason = rec.get("reason_for_recommendation") or rec.get("reason") or ""
            metrics_json = json.dumps(rec.get("supporting_metrics", {}))

            rows.append((portfolio_id, USER_NAME, portfolio_name, asset_class, ticker, allocation_float, reason, metrics_json))

    if not rows:
        raise ValueError("No recommendation rows found in portfolio payload")

    # ------------------------------------------------------------------
    # 3. DB prep – determine schema to use (now fixed to public)
    # ------------------------------------------------------------------
    target_db = "portfolio_results"
    _ensure_database_exists(target_db)

    schema_to_use = "public" # Fixed schema

    # ------------------------------------------------------------------
    # 4. Create table & insert data into the public schema
    # ------------------------------------------------------------------
    with _pg_connect(target_db) as conn:
        table = "final_portfolio"
        # Need to reference the `portfolios` table from store_portfolio_sector_allocations
        portfolios_table = "portfolios"

        with conn.cursor() as cur:
            # Recreate final_portfolio table
            create_sql = sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    portfolio_id UUID NOT NULL REFERENCES {schema}.{pf_table}(portfolio_id) ON DELETE CASCADE,
                    user_name VARCHAR(255) NOT NULL,
                    portfolio_name VARCHAR(255) NOT NULL,
                    asset_class VARCHAR(255) NOT NULL,
                    ticker VARCHAR(32) NOT NULL,
                    allocation NUMERIC(10,3),
                    reason TEXT,
                    supporting_metrics JSONB,
                    PRIMARY KEY (portfolio_id, asset_class, ticker)
                );
                """
            ).format(
                schema=sql.Identifier(schema_to_use), 
                table=sql.Identifier(table),
                pf_table=sql.Identifier(portfolios_table)
            )
            cur.execute(create_sql)

            insert_sql = sql.SQL(
                """
                INSERT INTO {schema}.{table}
                (portfolio_id, user_name, portfolio_name, asset_class, ticker, allocation, reason, supporting_metrics)
                VALUES %s
                ON CONFLICT (portfolio_id, asset_class, ticker) DO UPDATE SET
                    allocation = EXCLUDED.allocation,
                    reason = EXCLUDED.reason,
                    supporting_metrics = EXCLUDED.supporting_metrics,
                    user_name = EXCLUDED.user_name,      -- ensure these are updated too
                    portfolio_name = EXCLUDED.portfolio_name;
                """
            ).format(schema=sql.Identifier(schema_to_use), table=sql.Identifier(table))

            execute_values(cur, insert_sql.as_string(conn), rows)
            conn.commit()

    # return schema_to_use # No longer returning schema_name as it's fixed


