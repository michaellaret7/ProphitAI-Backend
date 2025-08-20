from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.cio.cio_tools import *
from backend.src.stress_test.runner import run_stress_test_workflow
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import get_upside_downside_ratios
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *

def register_cio_tools(agent):
    agent.add_tool(
        name="get_larger_ticker_pool",
        description="Get the larger pool of tickers from the CIO agent's original selection stored in ProphitAlts database. Returns a dictionary format: ticker_name: {position: 'long'|'short', industry: str, risk_allocation: float, reasoning: str}. Data source: Consumer Staples Fund initial analysis. ✅ NO PARAMETERS REQUIRED: This tool correctly takes no arguments - call with empty '{}' parameters. WHEN TO USE: (1) Portfolio modification - finding replacement tickers when removing positions, (2) Diversification expansion - adding new positions within same investment theme, (3) Sector allocation - understanding available options by industry, (4) CIO reasoning review - understanding original investment thesis. WORKFLOW: Use when current portfolio needs modification → Review available alternatives → Run factor/performance analysis on candidates → Test modified portfolio with analyze_portfolio_performance.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        function=lambda: get_larger_ticker_pool()
    )

    agent.add_tool(
        name="get_upside_downside_ratios",
        description="Calculate upside capture ratio (how much the portfolio captures during market up periods) and downside capture ratio (how much the portfolio loses during market down periods) versus SPY benchmark using historical price data. Values above 100% indicate outperformance/underperformance in respective market conditions. Returns dictionary format: {'upside_capture': float, 'downside_capture': float} as percentages. Data source: Daily price data from market database. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: get_upside_downside_ratios({'portfolio_dict': {'CELH': {'conviction': 0.10, 'position': 'long'}, 'PEP': {'conviction': 0.05, 'position': 'short'}}}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Asymmetric return analysis - understanding portfolio behavior in bull vs bear markets, (2) Long/short strategy validation - confirming shorts provide downside protection, (3) Risk-adjusted return evaluation - beyond simple Sharpe ratios, (4) Strategy style analysis - growth vs defensive characteristics. WORKFLOW: Use AFTER analyze_portfolio_performance to understand market-conditional behavior. Ideal for long/short portfolios to validate that shorts actually hedge during market downturns.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'CELH': {'conviction': 0.10, 'position': 'long'}, 'PEP': {'conviction': 0.05, 'position': 'short'}}"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: get_upside_downside_ratios(portfolio_dict)
    )

    agent.add_tool(
        name="get_all_factor_calculations",
        description="Calculate comprehensive factor scores for a ticker using the last year of daily price data and latest fundamental data from market database. Returns nested dictionary format: {'growth_factors': {...}, 'quality_factors': {...}, 'value_factors': {...}, 'momentum_factors': {...}, 'volatility_factors': {...}} with specific metrics like Sharpe ratio, beta vs SPY, P/E ratios, ROE, debt-to-equity. Data sources: Daily price feeds and FMP fundamental database. WHEN TO USE: (1) Stock selection - evaluating WHY a stock might outperform, (2) Factor exposure analysis - understanding growth/value/quality tilts, (3) Fundamental screening - finding stocks with specific characteristics, (4) Style analysis - ensuring portfolio factor balance. FACTOR ANALYSIS vs PERFORMANCE METRICS: Use FACTORS for forward-looking investment decisions based on fundamental characteristics; use get_ticker_performance_metrics for backward-looking performance evaluation. WORKFLOW: Screen with factors → Validate with performance metrics → Confirm with fundamentals.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string", 
                    "description": "Stock ticker symbol (required). Must be 1-10 alphabetic characters, case-insensitive (will be converted to uppercase). Examples: 'AAPL', 'msft', 'TSLA'. No spaces, numbers, or special characters allowed."
                }
            },
            "required": ["ticker"]
        },
        function=lambda ticker: get_all_factor_calculations(ticker)
    )

    agent.add_tool(
        name="get_ticker_performance_metrics",
        description="Calculate comprehensive performance metrics for a ticker using historical daily price data. Returns structured dictionary with metrics like total returns (%), annualized returns (%), volatility (%), Sharpe ratio (float), Sortino ratio (float), maximum drawdown (%), beta vs SPY (float), alpha generation, and various risk-adjusted return measures. Covers multiple time periods (1M, 3M, 6M, 1Y, 2Y) for trend analysis. Data source: Market database daily price feeds with 2% risk-free rate assumption. WHEN TO USE: (1) Performance attribution - understanding HOW a stock has performed, (2) Risk assessment - measuring actual volatility and drawdowns, (3) Peer comparison - ranking stocks by risk-adjusted returns, (4) Position sizing - using volatility for risk budgeting. PERFORMANCE METRICS vs FACTOR ANALYSIS: Use PERFORMANCE for backward-looking validation of what has happened; use get_all_factor_calculations for forward-looking prediction of what might happen. WORKFLOW: Factor screening → Performance validation → Portfolio construction with analyze_portfolio_performance.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string", 
                    "description": "Stock ticker symbol (required). Must be 1-10 alphabetic characters, case-insensitive (will be converted to uppercase). Examples: 'PEP', 'ko', 'CELH'. No spaces, numbers, or special characters allowed."
                }
            },
            "required": ["ticker"]
        },
        function=lambda ticker: get_ticker_performance_metrics(ticker)
    )

    agent.add_tool(
        name="get_most_recent_fundamentals",
        description="Retrieve the most recent fundamental data for a ticker from FMP (Financial Modeling Prep) database, typically updated within 1-3 months of earnings releases. Returns list of dictionaries with financial metrics (values in USD millions unless specified). Access balance sheet (assets, liabilities, equity), income statement (revenue, earnings, margins), cash flow statement (operating/investing/financing flows), financial ratios (ROE %, debt ratios, efficiency metrics), or analyst estimates (EPS forecasts $, price targets $). Data source: FMP API with quarterly/annual reporting periods. WHEN TO USE: (1) Deep-dive validation after factor analysis identifies interesting stocks, (2) Quarterly earnings analysis for existing positions, (3) Specific metric lookups for valuation models, (4) Fundamental data for custom calculations. FUNDAMENTALS vs FACTORS: Use FUNDAMENTALS for raw accounting data and detailed analysis; factors provide processed/normalized scores. WORKFLOW: Factor screening → Fundamental validation → Performance confirmation → Portfolio allocation decision.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string", 
                    "description": "Stock ticker symbol (required). Must be 1-10 alphabetic characters, case-insensitive (will be converted to uppercase). Examples: 'WMT', 'cl', 'DOLE'. No spaces, numbers, or special characters allowed."
                },
                "fundamentals_type": {
                    "type": "string", 
                    "description": "Type of fundamental data to retrieve (required). Must be exactly one of: 'balance_sheet', 'income_statement', 'cash_flow_statement', 'financial_ratios', 'analyst_estimates', or 'all'. Case-sensitive. Use 'all' to get all fundamental types in a single call. Example: 'financial_ratios'"
                }
            },
            "required": ["ticker", "fundamentals_type"]
        },
        function=lambda ticker, fundamentals_type: get_most_recent_fundamentals(ticker, fundamentals_type)
    )

    agent.add_tool(
        name="analyze_portfolio_performance",
        description="Comprehensive portfolio performance analysis over approximately 2 years (504 trading days) of historical data. Calculates total returns (%), annualized returns (%), volatility (%), Sharpe ratio (float), Sortino ratio (float), Calmar ratio (float), maximum drawdown (%), alpha/beta vs SPY (2% risk-free rate), upside potential ratio (float), VaR 95% (%), and information ratio (float). Returns nested dictionary: {'per_ticker_total_returns': {ticker: 'xx.xx%'}, 'portfolio_metrics': {metric_name: value}}. Data source: Daily price data from market database. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: analyze_portfolio_performance({'portfolio_dict': {'PM': {'conviction': 0.05, 'position': 'long'}, 'STZ': {'conviction': 0.03, 'position': 'short'}}}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Complete portfolio evaluation - overall risk/return profile, (2) Performance attribution - which holdings drove returns, (3) Risk budgeting - understanding portfolio-level risk metrics, (4) Benchmark comparison - alpha/beta analysis vs SPY. ANALYSIS SEQUENCE: Individual stock analysis (factors/performance) → Portfolio construction → analyze_portfolio_performance → stress_test validation → correlation analysis for refinement. This is the CORE evaluation tool for portfolio-level decisions.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Supports JSON string format or dictionary object. Example: {'PM': {'conviction': 0.05, 'position': 'long'}, 'STZ': {'conviction': 0.03, 'position': 'short'}}"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: analyze_portfolio_performance(portfolio_dict)
    )
