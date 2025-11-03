# database/config.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

# Reason: Build connection strings from components if full URLs contain placeholders
def get_database_url(env_var: str, db_name: str) -> str:
    """Get database URL, constructing from components if needed."""
    url = os.getenv(env_var)

    # If URL contains unsubstituted variables, build from components
    if url and ('${' in url or '${{' in url):
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return url

# Create engines with connection pooling
market_engine = create_engine(
    get_database_url("MARKET_DATA", "market_data"),
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for debugging
)

user_engine = create_engine(
    get_database_url("USER_DATA", "user_data"),
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

prophit_alts_engine = create_engine(
    get_database_url("PROPHIT_ALTS", "prophit_alts"),
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Create session factories
MarketSession = sessionmaker(bind=market_engine)
UserSession = sessionmaker(bind=user_engine)
ProphitAltsSession = sessionmaker(bind=prophit_alts_engine)

# Create base classes for each database
MarketBase = declarative_base()
UserBase = declarative_base()
ProphitAltsBase = declarative_base()