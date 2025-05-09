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
from .phase_two_calculations import (
    calculate_stock_metrics,
    calculate_and_filter_metrics,
    calculate_composite_scores
)

from .retrieve_fundamental_report import (
    generate_fundamental_analysis_report
    # debug_json_encoding is likely internal, not exposed
)

from ..backtest import (
    connect_to_ib,
    get_ib_historical_data,
    get_portfolio_value,
    get_historical_data_for_all_tickers,
    get_current_portfolio_holdings,
    calculate_portfolio_returns
)

from .phase_two_run import (
    pick_top_tickers_from_asset_classes,
    make_phaseTwo_recommendations,
)

# Import from backtest when you know which additional functions to expose
# from ..backtest import some_other_function

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
    
    # backtest exports
    'connect_to_ib',
    'get_ib_historical_data',
    'get_portfolio_value',
    'get_historical_data_for_all_tickers',
    'get_current_portfolio_holdings',
    'calculate_portfolio_returns',
    
    # backtest exports - add when implemented
    # 'function1', 'function2'

    # additional exports from phase_two_run
    'pick_top_tickers_from_asset_classes',
    'make_phaseTwo_recommendations',
] 