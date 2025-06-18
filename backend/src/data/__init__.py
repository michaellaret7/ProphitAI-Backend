"""
Data package for ProphitAI.

This package contains modules for managing financial data, including
portfolio data, fundamental data, and database schemas.
"""

# Import modules for easier access
from backend.src.utils.portfolio_analysis import (
    get_portfolio_holdings,
    calculate_portfolio_metrics,
    calculate_monthly_portfolio_metrics, 
    calculate_monthly_stock_metrics,
    analyze_portfolio_correlations
)

from backend.src.utils.ib_utils import (
    connect_to_ib
)

from backend.jobs.update_database_schema import (
    recreate_database_schemas
)

from backend.src.data.user_information import (
    get_user_information
) 