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

from psycopg2 import sql
from psycopg2.extras import Json

from ..user_information import get_user_information
from .store_portfolio_sector_allocations import (
    _pg_connect,
    _ensure_database_exists,
    _list_portfolio_schemas,
    _english_word_to_int_map,
    _int_to_english,
)

__all__ = ["store_user_information"]


def store_user_information() -> str:
    """Fetches user information and stores it. Returns the schema name used."""

    user_payload: Dict[str, Any] = get_user_information()

    # ------------------------------------------------------------------
    # 1. Prepare DB & schema
    # ------------------------------------------------------------------
    target_db = "portfolio_results"
    _ensure_database_exists(target_db)

    with _pg_connect(target_db) as conn:
        schemas = _list_portfolio_schemas(conn)

        pattern = re.compile(r"^portfolio_([a-z_]+)$", re.IGNORECASE)
        eng2num = _english_word_to_int_map()
        max_num = 0
        for sch in schemas:
            m = pattern.match(sch)
            if m:
                max_num = max(max_num, eng2num.get(m.group(1).lower(), 0))

        if max_num == 0:
            # Portfolio schema not yet created – start fresh
            schema_name = "portfolio_one"
            with conn.cursor() as cur:
                cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema_name)))
        else:
            schema_name = f"portfolio_{_int_to_english(max_num)}"

        # ------------------------------------------------------------------
        # 2. Create table and insert profile
        # ------------------------------------------------------------------
        table = "user_information"
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {schema}.{table} (
                        created_at TIMESTAMP DEFAULT now(),
                        profile     JSONB NOT NULL
                    );
                    """
                ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(table))
            )

            cur.execute(
                sql.SQL("INSERT INTO {schema}.{table} (profile) VALUES (%s);").format(
                    schema=sql.Identifier(schema_name), table=sql.Identifier(table)
                ),
                (Json(user_payload),),
            )
            conn.commit()

    return schema_name


if __name__ == "__main__":
    print("Stored in schema", store_user_information()) 