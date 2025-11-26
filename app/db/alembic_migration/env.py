"""
Multi-database Alembic environment for ProphitAI.

Handles migrations for 4 separate databases:
- market_data (MarketBase)
- user_data (UserBase)
- prophit_alts (ProphitAltsBase)
- macro_data (MacroDataBase)

Usage (from project root):
    alembic -c app/db/alembic_migration/alembic.ini -x db=<database_name> <command>
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

# Reason: Project root is 4 levels up from this file (app/db/alembic_migration/env.py)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Import database configuration
from app.db.core.db_config import (
    MarketBase, UserBase, ProphitAltsBase, MacroDataBase,
    get_database_url
)

# Import all models to register them with their respective Base classes
from app.db.core.models.market_data_models import (
    Ticker, BalanceSheet, CashFlowStatement, IncomeStatement, FinancialRatio,
    AnalystEstimate, ETFHolding, ETFInfo, Dividend, EarningsTranscript, Price,
    PressRelease, StockNews, PriceTargetNews, StockGradeNews, StockGradesIndividual,
    StockGradesSummary, Rating, AnalystRecommendation, PriceTargetSummary
)
from app.db.core.models.user_data_models import User, Company, Portfolio
from app.db.core.models.prophit_alts_models import (
    Fund, FundTrade, FundInitialPosition, FundFinalPosition
)
from app.db.core.models.macro_data_models import (
    GovernmentBondRates, CommodityPrices, EconomicIndicators, EconomicCalendar
)

# Alembic Config object
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Database configurations: name -> (Base, env_var, db_name)
DB_CONFIGS = {
    "market_data": (MarketBase, "MARKET_DATA", "market_data"),
    "user_data": (UserBase, "USER_DATA", "user_data"),
    "prophit_alts": (ProphitAltsBase, "PROPHIT_ALTS", "prophit_alts"),
    "macro_data": (MacroDataBase, "MACRO_DATA", "macro_data"),
}


def get_db_name() -> str:
    """
    Get the database name from -x db=<name> argument.

    Raises:
        ValueError: If database not specified or unknown database name.
    """
    x_args = context.get_x_argument(as_dictionary=True)
    db_name = x_args.get("db")

    if not db_name:
        raise ValueError(
            "Database not specified. Use: alembic -c app/db/alembic_migration/alembic.ini -x db=<database_name> <command>\n"
            f"Available databases: {', '.join(DB_CONFIGS.keys())}"
        )

    if db_name not in DB_CONFIGS:
        raise ValueError(
            f"Unknown database: {db_name}\n"
            f"Available databases: {', '.join(DB_CONFIGS.keys())}"
        )

    return db_name


def get_version_locations(db_name: str) -> str:
    """Get the version locations path for a specific database."""
    alembic_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(alembic_dir, "versions", db_name)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL script without connecting to the database.
    Useful for reviewing migrations or applying them manually.
    """
    db_name = get_db_name()
    base, env_var, db_name_str = DB_CONFIGS[db_name]

    url = get_database_url(env_var, db_name_str)

    context.configure(
        url=url,
        target_metadata=base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=f"alembic_version_{db_name}",
        version_locations=[get_version_locations(db_name)],
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    """
    db_name = get_db_name()
    base, env_var, db_name_str = DB_CONFIGS[db_name]

    url = get_database_url(env_var, db_name_str)

    # Reason: Use NullPool to avoid connection pooling issues during migrations
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=base.metadata,
            version_table=f"alembic_version_{db_name}",
            version_locations=[get_version_locations(db_name)],
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
