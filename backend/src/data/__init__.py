"""
Data package for ProphitAI.

This package contains modules for managing financial data, including
portfolio data, fundamental data, and database schemas.
"""

# Import modules for easier access
from backend.src.data.PortfolioData import (
    get_portfolio_holdings,
    connect_to_ib,
    calculate_portfolio_metrics,
    calculate_monthly_portfolio_metrics, 
    calculate_monthly_stock_metrics,
    analyze_portfolio_diversification,
    analyze_portfolio_correlations
)

from backend.src.data.FundamentalData import (
    get_financial_data,
    PushFundamentalDataToDB
)

from backend.src.data.database.database_schema_update import (
    recreate_database_schemas
)

from backend.src.data.user_information import (
    get_user_information
) 