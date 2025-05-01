# src/phaseTwo/__init__.py
# Expose key functions/classes from phaseTwo modules

# Import from the new modules
from .data_retrieval import (
    get_daily_closing_prices,
    get_fundamentals_data,
    get_stock_tickers,
    extract_asset_classes,
    get_quarterly_estimates,
    get_asset_description
)

# Import from phaseTwoCalculations.py
from .phaseTwoCalculations import (
    calculate_stock_metrics,
    calculate_and_filter_metrics,
    calculate_composite_scores
)

from .generateFundamentalAnalysis import (
    generate_fundamental_analysis_report
    # debug_json_encoding is likely internal, not exposed
)

from .phaseTwoBacktest import (
    connect_to_ib,
    get_ib_historical_data,
    get_portfolio_value,
    get_historical_data_for_all_tickers,
    get_current_portfolio_holdings,
    calculate_portfolio_returns
)

# Import from phaseTwoBacktest when you know which functions to expose
# from .phaseTwoBacktest import function1, function2

__all__ = [
    # data_retrieval exports
    'get_daily_closing_prices',
    'get_fundamentals_data',
    'get_stock_tickers',
    'extract_asset_classes',
    'get_quarterly_estimates',
    'get_asset_description',
    
    # phaseTwoCalculations exports
    'calculate_stock_metrics',
    'calculate_and_filter_metrics',
    'calculate_composite_scores',

    # financial_metrics exports
    'generate_fundamental_analysis_report',

    # stock_selection exports
    # 'select_top_performing_stocks',
    # 'analyze_tickers_and_generate_recommendations',

    # phaseTwo exports (Note: Original comment said 'phaseTwo', but these came from portfolio_analysis)
    # 'extract_asset_classes', # Moved
    # 'process_asset_class',
    # 'analyze_portfolio',
    
    # phaseTwoBacktest exports
    'connect_to_ib',
    'get_ib_historical_data',
    'get_portfolio_value',
    'get_historical_data_for_all_tickers',
    'get_current_portfolio_holdings',
    'calculate_portfolio_returns',
    
    # phaseTwoBacktest exports - add when implemented
    # 'function1', 'function2'
] 