"""
Data package for ProphitAI.

This package contains modules for managing financial data, including
portfolio data, fundamental data, and database schemas.
"""

# Import modules for easier access
# Note: portfolio_analysis.py has been removed and its functionality
# has been replaced by the calculations folder

from backend.src.utils.ib_utils import (
    connect_to_ib
)


from backend.src.data.user_information import (
    get_user_information
) 