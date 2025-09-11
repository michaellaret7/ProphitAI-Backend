from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.industry_agents.tools import (
    calc_industry_factor_benchmark_calculations,
    calc_sub_industry_factor_benchmark_calculations,
    calculate_ticker_factors,
    get_fundamental_data,
    fetch_repository_data,
)
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.cio.tools import (
    get_analyst_picks,
    correlation_matrix,
    calculate_portfolio_past_performance,
    exposure_calculator,
    industry_concentration,
    VaR_calculator,
    calculate_portfolio_beta_vs_index,
    factor_tilts_for_portfolio,
    pull_rest_of_ticker_pool,
)
from backend.src.calculations_v2.portfolio.build.builder import CorrelationPortfolioBuilder

def register_cio_tools(agent):
    agent.add_tool(
        name="get_industry_benchmark_calculations",
        description="Get the industry benchmark calculations for a given industry and factor. For example, 'beverages' and 'growth'. Another example is 'food_products' and 'value'.",
        parameters={
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "The industry to get the benchmark calculations for. For example, 'beverages', 'food_products', etc.",
                },
                "factor": {
                    "type": "string",
                    "description": "The factor to get the benchmark calculations for. The options are 'growth', 'value', 'momentum', 'quality', and 'volatility'.",
                    "enum": ["growth", "value", "momentum", "quality", "volatility"]
                },
            },
            "required": ["industry", "factor"],
        },
        function=lambda industry, factor: calc_industry_factor_benchmark_calculations(industry, factor).to_dict(),
    )
    
    agent.add_tool(
        name="get_sub_industry_benchmark_calculations",
        description="Get the sub-industry benchmark calculations for a given sub-industry and factor. For example, 'soft_drinks' and 'growth'. Another example is 'packaged_foods' and 'value'.",
        parameters={
            "type": "object",
            "properties": {
                "sub_industry": {
                    "type": "string",
                    "description": "The sub-industry to get the benchmark calculations for. For example, 'soft_drinks', 'packaged_foods', etc.",
                },
                "factor": {
                    "type": "string",
                    "description": "The factor to get the benchmark calculations for. The options are 'growth', 'value', 'momentum', 'quality', and 'volatility'.",
                    "enum": ["growth", "value", "momentum", "quality", "volatility"]
                },
            },
            "required": ["sub_industry", "factor"],
        },
        function=lambda sub_industry, factor: calc_sub_industry_factor_benchmark_calculations(sub_industry, factor).to_dict(),
    )
        
    agent.add_tool(
        name="calculate_ticker_factors",
        description="Calculate all factor metrics for a given ticker and factor type. Can calculate growth, value, momentum, quality, or volatility factors.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol to calculate factors for. For example, 'AAPL', 'MSFT', 'KO', etc.",
                },
                "factor": {
                    "type": "string",
                    "description": "The factor type to calculate. Options are 'growth', 'value', 'momentum', 'quality', or 'volatility'. 'all' DOES NOT EXIST FOR THIS TOOL",
                    "enum": ["growth", "value", "momentum", "quality", "volatility"]
                },
            },
            "required": ["ticker", "factor"],
        },
        function=calculate_ticker_factors,
    )
       
    agent.add_tool(
        name="get_ticker_fundamental_data",
        description="Get fundamental financial data for a ticker including income statements, balance sheets, cash flow statements, financial ratios, or analyst estimates.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol to get fundamental data for. For example, 'AAPL', 'MSFT', 'KO', etc.",
                },
                "statement_type": {
                    "type": "string",
                    "description": "Type of fundamental data to retrieve. Must be one of: 'income_statement', 'balance_sheet', 'cash_flow', 'financial_ratios', 'analyst_estimates'.",
                    "enum": ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"]
                },
                "quarters_back": {
                    "type": "integer",
                    "description": "Number of quarters of historical data to retrieve. Default is 1 (most recent quarter only).",
                    "default": 1
                },
            },
            "required": ["ticker", "statement_type"],
        },
        function=get_fundamental_data,
    )

    agent.add_tool(
        name="fetch_ticker_repository_data",
        description=(
            "Fetch auxiliary data for a ticker. Supported data_type: "
            "'press_releases','stock_news','price_target_news','grades_individual','grades_summary',"
            "'ratings','analyst_recommendations','price_target_summary','etf_info','etf_holdings',"
            "'earnings_transcripts','latest_transcript','dividends_series'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., 'AAPL').",
                },
                "data_type": {
                    "type": "string",
                    "description": "Type of data to fetch.",
                    "enum": [
                        "press_releases",
                        "stock_news",
                        "price_target_news",
                        "grades_individual",
                        "grades_summary",
                        "ratings",
                        "analyst_recommendations",
                        "price_target_summary",
                        "etf_info",
                        "etf_holdings",
                        "earnings_transcripts",
                        "latest_transcript",
                        "dividends_series"
                    ]
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional max number of items (applies to earnings_transcripts).",
                    "minimum": 1,
                    "maximum": 4
                }
            },
            "required": ["ticker", "data_type"],
        },
        function=fetch_repository_data,
    )

    # Tool 1: Get Analyst Picks
    agent.add_tool(
        name="get_analyst_picks",
        description=(
            "Retrieve analyst picks and initial positions for the Consumer Staples Fund. "
            "Returns a dictionary with tickers as keys and position details including position type "
            "(long/short), industry, conviction level, and reasoning."
        ),
        parameters={
            "type": "object",
            "properties": {}
        },
        function=get_analyst_picks,
    )

    # Tool 2: Correlation Matrix
    agent.add_tool(
        name="correlation_matrix",
        description="Calculate the correlation matrix for portfolio holdings using 252 trading days of historical data. Returns a correlation matrix showing relationships between all portfolio holdings.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: correlation_matrix(portfolio_dict, lookback_days=252),
    )

    # Tool 3: Calculate Portfolio Past Performance
    agent.add_tool(
        name="calculate_portfolio_past_performance",
        description="Compute comprehensive performance metrics for a portfolio using 3 years of historical data. Returns metrics including CAGR, Sharpe ratio, Sortino ratio, Beta, Alpha, Information ratio, Treynor ratio, tracking error, Omega ratio, Burke ratio, Sterling ratio, Martin ratio, max drawdown, win rate, profit factor, tail ratio, ulcer index, Calmar ratios, and annualized returns. All values are rounded to 5 decimal places. Uses SPY as benchmark and 2% risk-free rate.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: calculate_portfolio_past_performance(
            portfolio_dict, rf_annual=0.02, lookback_years=3, benchmark="SPY"
        ),
    )

    # Tool 4: Exposure Calculator
    agent.add_tool(
        name="exposure_calculator",
        description="Calculate portfolio exposure metrics. Net exposure is long minus short exposure. Gross exposure is the sum of absolute values of all positions. Long exposure is the sum of all long positions. Short exposure is the absolute value sum of all short positions. You must provide a portfolio_dict as an argument.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
                "exposure_type": {
                    "type": "string",
                    "description": "Type of exposure to calculate. Must be one of: 'net' (long minus short), 'gross' (sum of absolute values), 'long' (sum of long positions), or 'short' (sum of short positions).",
                    "enum": ["net", "gross", "long", "short"],
                },
            },
            "required": ["portfolio_dict", "exposure_type"],
            "additionalProperties": False
        },
        function=exposure_calculator,
    )

    # Tool 5: Industry Concentration
    agent.add_tool(
        name="industry_concentration",
        description="Calculate portfolio concentration by industry or sub-industry. Returns a dictionary showing the allocation percentage to each industry or sub-industry category, rounded to 5 decimal places.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
                "industry_level": {
                    "type": "string",
                    "description": "Level of industry aggregation. 'industry' provides broader categories (e.g., 'Food Products'), while 'sub_industry' provides more granular categories (e.g., 'Packaged Foods').",
                    "enum": ["industry", "sub_industry"],
                },
            },
            "required": ["portfolio_dict", "industry_level"],
            "additionalProperties": False
        },
        function=industry_concentration,
    )

    # Tool 6: VaR Calculator
    agent.add_tool(
        name="VaR_calculator",
        description="Calculate Value at Risk (VaR) at portfolio, industry, or sub-industry level. Portfolio level returns a single float value. Industry and sub-industry levels return dictionaries with VaR for each category. All values are rounded to 5 decimal places.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
                "level": {
                    "type": "string",
                    "description": "Level at which to calculate VaR. 'portfolio' calculates overall portfolio VaR, 'industry' calculates VaR by industry groups, 'sub_industry' calculates VaR by sub-industry groups.",
                    "enum": ["portfolio", "industry", "sub_industry"],
                },
            },
            "required": ["portfolio_dict", "level"],
            "additionalProperties": False
        },
        function=VaR_calculator,
    )

    # Tool 7: Calculate Portfolio Beta vs Index
    agent.add_tool(
        name="calculate_portfolio_beta_vs_index",
        description="Calculate CAPM beta for a long/short portfolio versus a specified market index using 252 trading days of historical data. Beta measures the portfolio's systematic risk relative to the index. A beta of 1.0 means the portfolio moves with the market, >1.0 means more volatile than market, <1.0 means less volatile.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
                "index_ticker": {
                    "type": "string",
                    "description": "Market index ticker to calculate beta against. Common indices: 'SPY' (S&P 500), 'QQQ' (NASDAQ 100), 'IWM' (Russell 2000), 'DIA' (Dow Jones), 'VTI' (Total Market).",
                },
            },
            "required": ["portfolio_dict", "index_ticker"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict, index_ticker: calculate_portfolio_beta_vs_index(
            portfolio_dict, lookback_days=252, index_ticker=index_ticker
        ),
    )

    # Tool 8: Factor Tilts for Portfolio
    agent.add_tool(
        name="factor_tilts_for_portfolio",
        description=(
            "Compute style factor tilts for a long/short portfolio using calculations_v2. "
            "Supports 'value', 'growth', 'momentum', 'quality', 'volatility', or 'all'.\n\n"
            "Input: 'portfolio_dict' must map each ticker to an object with 'allocation' (decimal, e.g., 0.1 for 10%) "
            "and 'position' ('long' or 'short'). Shorts are treated as negative weights automatically.\n\n"
            "Output: If a single factor is requested, returns a detailed object including 'factor', 'net_tilt', 'long_tilt', 'short_tilt', "
            "and 'per_ticker_exposure' (exposure per ticker). If 'all' is requested, returns a compact object keyed by factor name, "
            "each containing only the summary fields: 'factor', 'net_tilt', 'long_tilt', 'short_tilt'.\n\n"
            "All numeric results are rounded to 4 decimals. In cases where exposures cannot be computed (e.g., data unavailable), "
            "an object with an 'error' message is returned."
        ),
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                },
                "factors": {
                    "type": "string",
                    "description": (
                        "Factor to compute. Use 'all' for a summary across all factors; otherwise choose one of: "
                        "'value', 'growth', 'momentum', 'quality', 'volatility'."
                    ),
                    "enum": ["all", "value", "growth", "momentum", "quality", "volatility"],
                },
            },
            "required": ["portfolio_dict", "factors"],
            "additionalProperties": False
        },
        function=factor_tilts_for_portfolio,
    )

    # Tool 9: Build Correlation-Aware Portfolio
    agent.add_tool(
        name="build_portfolio",
        description=(
            "Build a correlation-aware long/short portfolio using historical data, optimization, and risk controls. "
            "This orchestrates data fetching, returns calculation, long/short optimization with group normalization, "
            "volatility scaling to a target annual volatility, and position sizing with leverage.\n\n"
            "Input 'portfolio_dict' maps tickers to {'allocation', 'position'} where: \n"
            "- 'allocation' is a decimal risk allocation (e.g., 0.10 = 10% of risk budget). Allocations are normalized within long and short groups.\n"
            "- 'position' is 'long' or 'short'. Shorts are treated as negative weights automatically.\n\n"
            "Key parameters: \n"
            "- The following parameters are LOCKED and cannot be overridden: target_annual_vol=0.15, portfolio_value=1_000_000, leverage=2.0, target_net_exposure=0.30, lookback_days=252.\n"
            "- Optional: 'max_position_weight' (number, default 0.10) caps absolute weight per position prior to renormalization.\n\n"
            "Output includes: \n"
            "- 'status' ('success' or 'error').\n"
            "- 'weights': signed optimized weights (negative for shorts).\n"
            "- 'position_sizes': dollar sizes after applying 'portfolio_value' and 'leverage'.\n"
            "- 'risk_metrics': volatility, max drawdown, VaR, expected shortfall, Sharpe, and concentration metrics.\n"
            "- 'target_vol', 'portfolio_value', 'leverage', 'target_net_exposure'.\n"
            "- 'actual_net_exposure', 'gross_exposure', 'long_exposure', 'short_exposure'.\n"
            "- 'final_portfolio': allocation/position format for execution (allocations rounded to 5 decimals).\n\n"
            "Returns an 'error' field with a message if any step fails (e.g., data unavailable)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: CorrelationPortfolioBuilder().build_portfolio(
            portfolio_dict=portfolio_dict,
            target_annual_vol=0.15,
            portfolio_value=1_000_000,
            leverage=2.0,
            target_net_exposure=0.30,
            lookback_days=252,
            max_position_weight=0.10,
        ),
    )

    # Tool 10: Pull Rest of Ticker Pool
    agent.add_tool(
        name="pull_rest_of_ticker_pool",
        description=(
            "Return remaining consumer staples tickers not already in fund initial positions, "
            "filtered by sector and minimum market cap."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        function=pull_rest_of_ticker_pool,
    )


