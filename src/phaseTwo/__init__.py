# src/phaseTwo/__init__.py
# Expose key functions/classes from phaseTwo modules

# Import from the new modules
from .data_retrieval import (
    get_daily_closing_prices,
    get_fundamentals_data,
    get_stock_tickers
)

from .financial_metrics import (
    calculate_stock_metrics,
    generate_fundamental_analysis_report
    # debug_json_encoding is likely internal, not exposed
)

from .sentiment_analysis import (
    get_news_sentiment,
    batch_analyze_news_sentiment
)

from .stock_selection import (
    select_top_performing_stocks,
    analyze_tickers_and_generate_recommendations
)

# Import from portfolio_analysis.py
from .portfolio_analysis import (
    extract_asset_classes,
    process_asset_class,
    analyze_portfolio
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
    
    # financial_metrics exports
    'calculate_stock_metrics',
    'generate_fundamental_analysis_report',

    # sentiment_analysis exports
    'get_news_sentiment',
    'batch_analyze_news_sentiment',

    # stock_selection exports
    'select_top_performing_stocks',
    'analyze_tickers_and_generate_recommendations',

    # phaseTwo exports
    'extract_asset_classes',
    'process_asset_class',
    'analyze_portfolio',
    
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