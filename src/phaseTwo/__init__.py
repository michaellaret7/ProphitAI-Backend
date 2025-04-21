# src/phaseTwo/__init__.py
# Expose key functions/classes from phaseTwo modules

from .phaseTwo import (
    get_daily_closing_prices, 
    calculate_stock_metrics, 
    get_fundamentals_data, 
    generate_fundamental_analysis_report,
    get_news_sentiment,
    extract_asset_classes,
    get_stock_tickers,
    select_top_performing_stocks,
    analyze_ticker,
    batch_analyze_news_sentiment,
    analyze_tickers_and_generate_recommendations,
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
    # phaseTwo exports
    'get_daily_closing_prices', 
    'calculate_stock_metrics', 
    'get_fundamentals_data', 
    'generate_fundamental_analysis_report',
    'get_news_sentiment',
    'extract_asset_classes',
    'get_stock_tickers',
    'select_top_performing_stocks',
    'analyze_ticker',
    'batch_analyze_news_sentiment',
    'analyze_tickers_and_generate_recommendations',
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