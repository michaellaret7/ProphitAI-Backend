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
import re
import os
from psycopg2 import connect, sql, extensions
from psycopg2.extras import execute_values
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

if not all([DB_USER, DB_PASSWORD, DB_HOST]):
    raise RuntimeError("Database credentials (DB_USER, DB_PASSWORD, DB_HOST) must be set in .env or environment")


def _pg_connect(db: str, autocommit: bool = True):
    """Return a fresh psycopg2 connection to *db*."""
    conn = connect(
        dbname=db,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.set_session(autocommit=autocommit)
    return conn


def _ensure_database_exists(db_name: str) -> None:
    """Create *db_name* if it does not yet exist."""
    with _pg_connect("postgres") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone():
                return  # already there
            cur.execute(sql.SQL("CREATE DATABASE {}".format(sql.Identifier(db_name).string)))


def _list_portfolio_schemas(conn) -> list[str]:
    """Return schemas that match the 'portfolio_%' pattern (lower-cased)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name LIKE 'portfolio_%';
            """
        )
        return [row[0] for row in cur.fetchall()]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store_portfolio_sector_allocations(portfolio: dict | str) -> str:
    """Persist *portfolio* to Postgres and return the schema name that was created.

    Parameters
    ----------
    portfolio
        Either the dictionary produced by ``optimize`` or its JSON-encoded string.

    Returns
    -------
    str
        The schema name inside *portfolio_results* that now contains the data
        (e.g. ``'portfolio_one'``).
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

    with _pg_connect(target_db) as conn:
        # -----------------------------------------------------------------
        # 4. Calculate next schema name
        # -----------------------------------------------------------------
        existing_schemas = _list_portfolio_schemas(conn)

        # Extract numbers from schemas like 'portfolio_one', 'portfolio_two', ...
        pattern = re.compile(r"^portfolio_([a-z]+)$", re.IGNORECASE)
        english_to_num = _english_word_to_int_map()

        max_num = 0
        for sch in existing_schemas:
            match = pattern.match(sch)
            if match:
                word = match.group(1).lower()
                num = english_to_num.get(word, 0)
                max_num = max(max_num, num)

        next_num = max_num + 1  # start at 1 when none exists
        next_word = _int_to_english(next_num)
        schema_name = f"portfolio_{next_word}"

        # -----------------------------------------------------------------
        # 5. Create schema & table
        # -----------------------------------------------------------------
        table_name = "portfolio_sector_allocation"

        with conn.cursor() as cur:
            # Create schema
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema_name)))

            # Define table
            create_table_sql = sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    id SERIAL PRIMARY KEY,
                    asset_class VARCHAR(255),
                    allocation NUMERIC(10,3),
                    reason TEXT
                );
                """
            ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(table_name))
            cur.execute(create_table_sql)

            # ----------------------------------------------------------------
            # 6. Insert data - removed ON CONFLICT to allow duplicates
            # ----------------------------------------------------------------
            rows = [tuple(x) for x in df.itertuples(index=False, name=None)]

            insert_sql = sql.SQL(
                """
                INSERT INTO {schema}.{table} (asset_class, allocation, reason)
                VALUES %s;
                """
            ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(table_name))

            execute_values(cur, insert_sql.as_string(conn), rows)

            # ----------------------------------------------------------------
            # 6.b (New) Store the high-level thesis, if provided
            # ----------------------------------------------------------------
            thesis = portfolio_dict.get("portfolio_thesis")
            if thesis:
                # Ensure meta table exists
                create_meta_sql = sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {schema}.portfolio_thesis (
                        id SERIAL PRIMARY KEY,
                        generated_at TIMESTAMP DEFAULT now(),
                        thesis        TEXT      NOT NULL,
                        extra         JSONB     DEFAULT '{{}}'::jsonb
                    );
                    """
                ).format(schema=sql.Identifier(schema_name))
                cur.execute(create_meta_sql)

                # Insert thesis (one row per portfolio snapshot)
                cur.execute(
                    sql.SQL("INSERT INTO {schema}.portfolio_thesis (thesis) VALUES (%s);").format(
                        schema=sql.Identifier(schema_name)
                    ),
                    (thesis,)
                )

        # Commit is automatic because autocommit true, but call for clarity
        conn.commit()

    return schema_name

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_num_to_words_mapping = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety"
}


def _int_to_english(n: int) -> str:
    """Convert *n* (1-99) to its English word representation.

    For numbers outside that range a ``ValueError`` is raised – our use-case
    will realistically never exceed that.
    """
    if n <= 0 or n >= 100:
        raise ValueError("Only numbers between 1 and 99 supported")

    if n in _num_to_words_mapping:
        return _num_to_words_mapping[n]

    # handle 21-99 (excluding exact tens which are covered above)
    tens, ones = divmod(n, 10)
    return f"{_num_to_words_mapping[tens * 10]}_{_num_to_words_mapping[ones]}"


def _english_word_to_int_map() -> Dict[str, int]:
    """Return inverse mapping used for schema introspection."""
    mapping: Dict[str, int] = {word: num for num, word in _num_to_words_mapping.items()}
    # Add values for 21-99 (hyphen/underscore handled)
    for n in range(21, 100):
        if n in _num_to_words_mapping:
            continue
        tens, ones = divmod(n, 10)
        word = f"{_num_to_words_mapping[tens * 10]}_{_num_to_words_mapping[ones]}"
        mapping[word] = n
    return mapping

if __name__ == "__main__":
    portfolio = {
    "portfolio": [
        {
        "asset_class": "semiconductors",
        "allocation": 10,
        "reason": "Secular AI and cloud growth, U.S./Taiwan leadership, and double-digit YoY sales increases drive this segment. Premium valuations are justified by structural demand; risks are countered by industry dominance and capital discipline."
        },
        {
        "asset_class": "application_software",
        "allocation": 7,
        "reason": "AI adoption, enterprise cloud migration, and vertical-specific platforms make this segment a consistent outperformer. Strong retention, high margins, and broad applicability underpin growth."
        },
        {
        "asset_class": "biotechnology",
        "allocation": 6,
        "reason": "Innovation in GLP-1, gene therapy, and biologics drives top-line growth and long-term defensiveness. Biotech offers both alpha and protection in volatile markets."
        },
        {
        "asset_class": "health_care_equipment",
        "allocation": 5,
        "reason": "MedTech, diagnostics, and minimally invasive surgery (robotics, AI-driven devices) are high-growth, high-margin segments that combine defensiveness with innovation-driven upside."
        },
        {
        "asset_class": "multi_family_residential_reits",
        "allocation": 5,
        "reason": "Housing undersupply, demographic tailwinds, and rising rents support strong income and inflation hedging for the next 3–5 years."
        },
        {
        "asset_class": "data_center_reits",
        "allocation": 5,
        "reason": "Digital transformation and AI infrastructure demand are driving exponential data growth, making this REIT segment a structural outperformer with long-term leases and pricing power."
        },
        {
        "asset_class": "diversified_banks",
        "allocation": 5,
        "reason": "Large banks offer resilience, digital innovation, and benefit from loan growth, M&A, and strong capital ratios. They also provide some yield and cyclical upside."
        },
        {
        "asset_class": "investment_grade_corporate_bond_etfs",
        "allocation": 7,
        "reason": "Yields above 5%, robust credit fundamentals, and tight spreads create income ballast and portfolio stability, especially in a late-cycle environment."
        },
        {
        "asset_class": "high_yield_junk_bond_etfs",
        "allocation": 5,
        "reason": "Attractive 7%+ yields, low default risk, and solid corporate fundamentals provide tactical income and risk-on exposure, complementing investment grade bonds."
        },
        {
        "asset_class": "treasury_and_inflation_bond_etfs",
        "allocation": 8,
        "reason": "Treasuries and TIPS provide diversification, inflation protection, and a critical risk-off hedge—especially important amid policy, inflation, and geopolitical volatility."
        },
        {
        "asset_class": "single_country_and_regional_etfs_in_emerging_marke",
        "allocation": 8,
        "reason": "Targeting India, Taiwan, and Southeast Asia leverages strong GDP and earnings growth, currency stability, and EM tech/consumer expansion, diversifying away from U.S. cyclicality."
        },
        {
        "asset_class": "electric_utilities",
        "allocation": 4,
        "reason": "Secular growth from electrification, AI/data center power demand, and grid modernization. Utilities offer stable dividends, inflation protection, and defensive attributes."
        },
        {
        "asset_class": "oil_and_gas_exploration",
        "allocation": 4,
        "reason": "Natural gas and upstream oil are well-positioned for energy transition volatility, with strong cash flows, capital discipline, and upside from both traditional and transition markets."
        },
        {
        "asset_class": "precious_metals_etfs",
        "allocation": 4,
        "reason": "Gold provides a robust hedge against inflation, currency devaluation, and geopolitical uncertainty, especially as central banks accumulate reserves."
        },
        {
        "asset_class": "specialty_chemicals",
        "allocation": 3,
        "reason": "Specialty chemicals benefit from energy transition, battery/EV demand, and innovation-driven margin expansion. Defensive and growth attributes are well-balanced here."
        },
        {
        "asset_class": "consumer_staples_merchandise_retail",
        "allocation": 4,
        "reason": "Essentials-focused retail offers defensive ballast, cash flow resilience, and dividend support. Volume growth and stable demand make this a core holding for market uncertainty."
        },
        {
        "asset_class": "Cash",
        "allocation": 5,
        "reason": "Maintains strategic liquidity for tactical rebalancing, supports risk management, and ensures portfolio flexibility for new opportunities or defensive moves."
        }
    ],
    "portfolio_thesis": "This portfolio is optimized for a medium-risk, growth-focused investor with a 5-year horizon, balancing secular growth (AI, healthcare, EM tech/consumer) with defensive income and inflation hedges. Overweights in AI/tech, healthcare, and digital real estate are paired with quality bonds, EM equity, and real asset exposures to capture upside and manage risk. This structure aligns with 2025 market themes—AI acceleration, EM outperformance, late-cycle volatility, and policy uncertainty—ensuring strong return potential while minimizing drawdowns and maintaining flexibility."
    }

    store_portfolio_sector_allocations(portfolio)