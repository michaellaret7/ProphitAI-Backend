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

from ...backtest.backtest_helpers import (
    get_historical_data_for_all_tickers,
    calculate_portfolio_returns
)

from .phase_two_run import (
    pick_top_tickers_from_asset_classes,
    make_phaseTwo_recommendations,
    run_phase_two,
)

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

    # backtest exports
    'get_historical_data_for_all_tickers',
    'calculate_portfolio_returns',

    # additional exports from phase_two_run
    'pick_top_tickers_from_asset_classes',
    'make_phaseTwo_recommendations',
    'run_phase_two',
] 