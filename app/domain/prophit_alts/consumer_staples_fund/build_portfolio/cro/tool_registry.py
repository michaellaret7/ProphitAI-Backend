from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cro.tools import *
from app.domain.stress_test.runner import run_stress_test_workflow
from app.db.core.db_config import ProphitAltsSession
from app.db.core.prophit_alts_models import *

def register_cro_tools(agent):
    """
    Register all CRO agent tools with the provided agent instance.
    
    ⚠️ GPT-5 COMPATIBILITY NOTE:
    All portfolio analysis tools require the 'portfolio_dict' parameter with actual portfolio data.
    Common GPT-5 mistake: Calling tools with empty arguments '{}' instead of passing portfolio data.
    ALWAYS pass the portfolio you want to analyze - never call with empty parameters.
    
    Args:
        agent: The CROAgent instance to register tools with
    """
    
    # Stress test tool
    agent.add_tool(
        name="stress_test",
        description="Run comprehensive stress tests on a portfolio including market crash scenarios (-20%, -30%, -40%), sector rotation stress, interest rate shock, inflation spike, and correlation breakdown scenarios. Returns detailed dictionary with risk metrics, VaR calculations (%), scenario-specific performance impacts (%), maximum drawdowns (%), and stress test results by scenario type. Data source: Historical price data from market database with Monte Carlo simulation engine. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to stress test. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: stress_test({'portfolio_dict': {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to stress test. WHEN TO USE: (1) Final validation after portfolio construction - worst-case scenario analysis, (2) Position sizing decisions - ensuring survivability, (3) Risk management - understanding tail risk exposure, (4) Client reporting - demonstrating downside protection. CRITICAL WORKFLOW: analyze_portfolio_performance (understand baseline) → stress_test (validate resilience) → correlation analysis (check concentration) → final allocation decisions. Use stress testing as the FINAL CHECK before committing capital.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to stress test. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: run_stress_test_workflow(portfolio_dict)
    )

    # Initial portfolio dictionary tool
    agent.add_tool(
        name="get_initial_portfolio_dict",
        description="Get the Consumer Staples Fund's initial portfolio dictionary with 34 tickers and their conviction levels (17 long positions including CASY, CELH at 10% conviction, plus 17 short positions including WBA, PEP). Returns dictionary format: {ticker: {'conviction': float, 'position': 'long'|'short'}}. Data source: INITIAL_PORTFOLIO_DICT constant from CIO analysis. ✅ NO PARAMETERS REQUIRED: This tool correctly takes no arguments - call with empty '{}' parameters. WHEN TO USE: (1) ALWAYS START HERE - get the baseline portfolio before any analysis, (2) Portfolio construction - use as template for modifications, (3) Allocation reference - understand CIO's conviction levels, (4) Comparison base - measure changes against original structure. ESSENTIAL WORKFLOW: get_initial_portfolio_dict (start) → analyze_portfolio_performance (baseline) → individual stock analysis → portfolio modifications → re-analysis. This is the REQUIRED FIRST STEP for any CRO analysis.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        function=lambda: get_initial_portfolio_dict()
    )

    agent.add_tool(
        name="calculate_correlation_matrix",
        description="Calculate correlation matrix showing linear relationships between portfolio tickers using the last year (252 trading days) of daily returns data. Correlation values range from -1 (perfect negative correlation) to +1 (perfect positive correlation), rounded to 3 decimal places. Returns dictionary format: {'tickers': [list], 'correlation_matrix': {ticker: {ticker: correlation_value}}}. Data source: Daily price feeds from market database. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: calculate_correlation_matrix({'portfolio_dict': {'MNST': {'conviction': 0.05, 'position': 'long'}, 'COTY': {'conviction': 0.05, 'position': 'short'}}}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Identifying over-concentrated positions with >0.8 correlation, (2) Finding diversification pairs with <0.3 correlation, (3) Pre-allocation analysis to avoid clustering, (4) Stress testing correlation assumptions. WORKFLOW: Use BEFORE major allocation changes → Run analyze_portfolio_performance → Compare with stress_test results for complete risk picture. Choose CORRELATION (not covariance) for: diversification analysis, risk concentration assessment, intuitive relationship interpretation.",
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
        function=lambda portfolio_dict: calculate_correlation_matrix(portfolio_dict)
    )

    agent.add_tool(
        name="calculate_covariance_matrix",
        description="Calculate covariance matrix measuring how portfolio tickers move together in absolute terms using the last year (252 trading days) of daily returns data. Unlike correlation, covariance is not normalized and reflects both the strength and direction of relationships, rounded to 6 decimal places. Returns dictionary format: {'tickers': [list], 'covariance_matrix': {ticker: {ticker: covariance_value}}}. Data source: Daily price feeds from market database. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: calculate_covariance_matrix({'portfolio_dict': {'VITL': {'conviction': 0.05, 'position': 'long'}, 'KVUE': {'conviction': 0.05, 'position': 'short'}}}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Portfolio optimization/mean-variance analysis requiring actual variance values, (2) Risk budgeting with volatility-weighted positions, (3) Hedge ratio calculations, (4) Advanced quantitative models needing non-normalized relationships. WORKFLOW: Use AFTER correlation analysis → Combine with get_ticker_performance_metrics for volatility → Feed into portfolio optimization algorithms. Choose COVARIANCE (not correlation) for: mathematical optimization, volatility-adjusted analysis, hedge construction, quantitative modeling.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'VITL': {'conviction': 0.05, 'position': 'long'}, 'KVUE': {'conviction': 0.05, 'position': 'short'}}"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: calculate_covariance_matrix(portfolio_dict)
    )

    # VaR/Expected Shortfall tool
    agent.add_tool(
        name="vol_es",
        description="Calculate portfolio Volatility, Value at Risk (VaR), and Expected Shortfall (ES) using parametric, historical, or EWMA methods. Returns comprehensive risk metrics including daily/annual VaR, Expected Shortfall (conditional VaR), and portfolio volatility with customizable time horizons and confidence levels. Data source: Historical price data from market database with internal returns calculation. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze for risk metrics. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: vol_es({'portfolio_dict': {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}, 'horizon_days': 10, 'conf': 0.95, 'method': 'hist'}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Risk assessment before position sizing - understand worst-case scenarios, (2) Regulatory capital calculations requiring VaR metrics, (3) Client risk reporting with confidence intervals, (4) Comparing risk across different portfolio configurations, (5) Setting stop-loss and risk limits. CRITICAL WORKFLOW: get_initial_portfolio_dict → vol_es (baseline risk) → risk_contribution (identify concentrations) → portfolio modifications → vol_es (validate improvements). Use as PRIMARY RISK METRIC for portfolio evaluation.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}"
                },
                "horizon_days": {
                    "type": "integer", 
                    "description": "Time horizon for risk calculation in days. Default: 1 for daily risk. Common values: 1 (daily), 10 (bi-weekly), 21 (monthly), 252 (annual). VaR scales with √days.",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 252
                },
                "conf": {
                    "type": "number",
                    "description": "Confidence level for VaR/ES calculation as decimal. Default: 0.99 (99% confidence). Common values: 0.95 (95%), 0.99 (99%), 0.999 (99.9%). Higher confidence = more conservative risk estimate.",
                    "default": 0.99,
                    "minimum": 0.90,
                    "maximum": 0.999
                },
                "method": {
                    "type": "string",
                    "description": "Calculation method. 'param' (parametric/normal): assumes normal distribution, fastest. 'hist' (historical): uses actual return distribution, most realistic. 'ewma' (exponentially weighted): recent data weighted more heavily, most responsive. Default: 'param'",
                    "enum": ["param", "hist", "ewma"],
                    "default": "param"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict, horizon_days=1, conf=0.99, method='param': vol_es(portfolio_dict, horizon_days, conf, method)
    )

    # Risk contribution tool
    agent.add_tool(
        name="risk_contribution",
        description="Calculate Total Risk and decompose risk contributions by individual assets using volatility or VaR-based metrics. Returns Total Risk (TR), Marginal Contribution to Total Risk (MCTR) per asset, and Component Total Risk percentages (CTR%) showing which positions contribute most to portfolio risk. Essential for risk budgeting and concentration analysis. Data source: Historical price data with internal covariance matrix calculations. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze for risk decomposition. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: risk_contribution({'portfolio_dict': {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}, 'metric': 'vol'}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Risk budgeting - ensure no single position dominates risk, (2) Position sizing decisions - identify over-concentrated positions, (3) Portfolio rebalancing - understand which assets to reduce/increase, (4) Risk attribution reporting for clients, (5) Regulatory compliance for concentration limits. CRITICAL WORKFLOW: vol_es (understand total risk) → risk_contribution (identify concentrations) → analyze high-contribution assets → rebalance → re-run risk_contribution (validate improvements). Use AFTER vol_es to understand WHERE portfolio risk comes from.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}"
                },
                "metric": {
                    "type": "string",
                    "description": "Risk metric to decompose. 'vol' (volatility): decompose portfolio volatility - easier to interpret, good for general risk analysis. 'var' (Value at Risk): decompose VaR metric - useful for tail risk analysis and regulatory reporting. Default: 'vol'",
                    "enum": ["vol", "var"],
                    "default": "vol"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict, metric='vol': risk_contribution(portfolio_dict, metric)
    )

    # Drawdown profile tool
    agent.add_tool(
        name="drawdown_profile",
        description="Analyze portfolio drawdown characteristics including maximum drawdown, average drawdowns, Ulcer Index (drawdown severity measure), and detailed episode analysis with recovery times. Provides comprehensive downside risk assessment using 2-year historical portfolio NAV analysis with peak-to-trough decline detection. Critical for understanding portfolio resilience and downside protection. Data source: 2-year historical price data with weighted portfolio returns calculation. 🚨 CRITICAL PARAMETER REQUIRED: You MUST provide 'portfolio_dict' containing the specific portfolio you want to analyze for drawdown characteristics. This should be the current portfolio you're analyzing, a modified portfolio you've constructed, or a new iteration you want to test in the format: {'TICKER': {'conviction': 0.xx, 'position': 'long'/'short'}}. EXAMPLE: drawdown_profile({'portfolio_dict': {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}}) DO NOT call with empty arguments '{}' - this will cause 'Portfolio dictionary is required' error. Pass the actual portfolio data you want to analyze. WHEN TO USE: (1) Downside risk assessment - understand worst historical declines, (2) Client suitability analysis - match drawdown tolerance to investor profile, (3) Risk management - set appropriate stop-loss levels, (4) Performance evaluation - assess risk-adjusted returns considering drawdowns, (5) Stress testing complement - historical vs hypothetical stress scenarios. CRITICAL WORKFLOW: vol_es (statistical risk) → drawdown_profile (historical reality) → stress_test (hypothetical scenarios) → comprehensive risk assessment. Use to understand ACTUAL HISTORICAL EXPERIENCE of portfolio performance during market stress.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "🚨 REQUIRED: Portfolio dictionary containing the portfolio you want to analyze. Keys are ticker symbols (uppercase strings, 1-10 characters) and values are objects with 'conviction' and 'position' fields. Conviction must be float between 0.0-1.0 representing position size. Position must be exactly 'long' or 'short' (lowercase). MUST provide actual portfolio data - cannot be empty! Example: {'CASY': {'conviction': 0.10, 'position': 'long'}, 'WBA': {'conviction': 0.05, 'position': 'short'}}"
                }
            },
            "required": ["portfolio_dict"],
            "additionalProperties": False
        },
        function=lambda portfolio_dict: drawdown_profile(portfolio_dict)
    )


