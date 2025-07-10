"""
Script to create all database tables from SQLAlchemy models
"""
from sqlalchemy import text
from backend.src.db.core.db_config import market_engine, user_engine, MarketBase, UserBase

# Import all models to register them with their respective Base classes
from backend.src.db.core.user_data_models import (
    User, Company, CompanyUser, Portfolio
)
from backend.src.db.core.market_data_models import (
    Ticker, BalanceSheet, CashFlowStatement, IncomeStatement, FinancialRatio,
    AnalystEstimate, ETFHolding, ETFInfo, Dividend,
    EarningsTranscript, Price, PressRelease, StockNews, PriceTargetNews,
    StockGradeNews, GeneralNews, StockGradesIndividual, StockGradesSummary,
    Rating, AnalystRecommendation, PriceTargetSummary
)

def create_schemas():
    """Create all required schemas in the market database"""
    schemas = [
        'ticker_universe',
        'fundamental_data',
        'price_data',
        'news_data',
        'grades_and_ratings_data'
    ]
    
    with market_engine.connect() as conn:
        for schema in schemas:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            print(f"Schema '{schema}' created or already exists")
        conn.commit()

def create_all_tables():
    """Create all tables in both databases"""
    print("Creating schemas in Market database...")
    create_schemas()
    
    print("\nCreating User Data tables...")
    UserBase.metadata.create_all(bind=user_engine)
    print("User Data tables created successfully!")
    
    print("\nCreating Market Data tables...")
    MarketBase.metadata.create_all(bind=market_engine)
    print("Market Data tables created successfully!")

if __name__ == "__main__":
    create_all_tables()
    print("\nAll tables created successfully!") 