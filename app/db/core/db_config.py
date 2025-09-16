# database/config.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

# Create engines with connection pooling
market_engine = create_engine(
    os.getenv("MARKET_DATA"),
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for debugging
)

user_engine = create_engine(
    os.getenv("USER_DATA"),
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False
)

prophit_alts_engine = create_engine(
    os.getenv("PROPHIT_ALTS"),
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
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