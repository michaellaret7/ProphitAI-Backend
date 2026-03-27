"""
Multi-database Alembic environment for ProphitAI.

Handles migrations for 4 separate databases:
- market_data (MarketBase)
- user_data (UserBase)
- prophit_alts (ProphitAltsBase)
- macro_data (MacroDataBase)

Usage (from packages/data/):
    alembic -c migrations/alembic.ini --name <database_name> <command>
"""
import os
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

from dotenv import load_dotenv

load_dotenv()

# Import database configuration
from prophitai_data.db.config import (
    MarketBase, UserBase, ProphitAltsBase, MacroDataBase,
    get_database_url
)

# Import all models to register them with their respective Base classes
from prophitai_data.db.models.market import (
    Ticker, BalanceSheet, CashFlowStatement, IncomeStatement, FinancialRatio,
    AnalystEstimate, ETFHolding, ETFInfo, Dividend, EarningsTranscript, Price,
    DailyPrices, PressRelease, StockNews, PriceTargetNews, StockGradeNews,
    StockGradesIndividual, StockGradesSummary, Rating, AnalystRecommendation,
    PriceTargetSummary, EquityScreener, ETFScreener
)
from prophitai_data.db.models.user import (
    User, Portfolio, PortfolioItem, PortfolioPreference,
    Watchlist, WatchlistItem, Conversation, Message, TradeProposal
)
from prophitai_data.db.models.alts import (
    Fund, FundTrade, FundInitialPosition, FundFinalPosition
)
from prophitai_data.db.models.macro import (
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
    Get the database name from --name argument (config section).

    Raises:
        ValueError: If database not specified or unknown database name.
    """
    # config.config_ini_section is set by --name flag
    db_name = config.config_ini_section

    if db_name == "alembic" or not db_name:
        raise ValueError(
            "Database not specified. Use: alembic -c migrations/alembic.ini --name <database_name> <command>\n"
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
    migrations_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(migrations_dir, "versions", db_name)


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
