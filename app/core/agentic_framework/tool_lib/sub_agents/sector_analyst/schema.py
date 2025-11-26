from app.core.agentic_framework.tool_lib.sub_agents.sector_analyst.sub_agent import run_sector_analyst

SECTOR_ANALYST_DESCRIPTION = (
    "Autonomous sub-agent specialized in comprehensive sector-level analysis and stock research within a specific market sector. "
    "This tool spawns an independent AI agent with 50 iterations to perform deep sector analysis. The agent autonomously plans and executes "
    "a multi-step research workflow to analyze sector performance, identify industry trends, screen for stocks, and evaluate individual tickers."
    "\n\n**CAPABILITIES:**"
    "\n\n1. SECTOR-LEVEL ANALYSIS"
    "\n  - Sector performance metrics across multiple time periods"
    "\n  - Sector valuation metrics (P/E ratios, multiples)"
    "\n  - Industry and sub-industry breakdown within the sector"
    "\n  - Sector composition and constituent tickers"
    "\n\n2. INDUSTRY BENCHMARKING"
    "\n  - Factor exposure analysis at industry level (growth, value, momentum, quality, volatility)"
    "\n  - Sub-industry factor benchmarking"
    "\n  - Comparative industry positioning and trends"
    "\n\n3. STOCK SCREENING AND DISCOVERY"
    "\n  - Advanced stock screener with custom criteria"
    "\n  - Group ticker retrieval by sector/industry/sub-industry"
    "\n  - Multi-criteria filtering for stock selection"
    "\n\n4. TICKER-LEVEL ANALYSIS"
    "\n  - Individual stock factor calculations (growth, value, momentum, quality, volatility)"
    "\n  - Performance and risk metrics (returns, volatility, Sharpe ratio, max drawdown)"
    "\n  - Fundamental data analysis (income statement, balance sheet, cash flow, ratios)"
    "\n  - Analyst estimates and consensus forecasts"
    "\n  - Stock ratings and recommendations"
    "\n  - Price target data and analyst coverage"
    "\n\n**USE CASES:**"
    "\n  - Comprehensive sector deep-dive research"
    "\n  - Top-down sector rotation analysis"
    "\n  - Stock screening and idea generation within a sector"
    "\n  - Industry trend identification and positioning"
    "\n  - Comparative analysis of stocks within a sector"
    "\n  - Factor-based sector analysis"
    "\n  - Thematic research within specific sectors"
    "\n\n**EXECUTION:**"
    "\nThe agent operates autonomously using a planning-first approach. It will create a structured research plan, execute tools iteratively, "
    "synthesize findings, and return a comprehensive analysis. The agent runs for up to 50 iterations with temperature 0.7 for balanced analytical reasoning."
    "\n\n**OUTPUT:**"
    "\nReturns a detailed analytical report with sector insights, industry trends, stock recommendations, and supporting data from the agent's research process."
)

SECTOR_ANALYST_PARAMETERS = {
    "type": "object",
    "properties": {
        "sector": {
            "type": "string",
            "description": (
                "The market sector to analyze. Must be one of the following valid sector identifiers: "
                "'equity_sector_information_technology', 'equity_sector_health_care', 'equity_sector_financials', "
                "'equity_sector_consumer_discretionary', 'equity_sector_consumer_staples', 'equity_sector_industrials', "
                "'equity_sector_communication_services', 'equity_sector_energy', 'equity_sector_materials', "
                "'equity_sector_utilities', 'equity_sector_real_estate'"
            ),
            "enum": [
                "equity_sector_information_technology",
                "equity_sector_health_care",
                "equity_sector_financials",
                "equity_sector_consumer_discretionary",
                "equity_sector_consumer_staples",
                "equity_sector_industrials",
                "equity_sector_communication_services",
                "equity_sector_energy",
                "equity_sector_materials",
                "equity_sector_utilities",
                "equity_sector_real_estate"
            ]
        }
    },
    "required": ["sector"],
    "additionalProperties": False
}

SECTOR_ANALYST_TOOL = {
    "name": "sector_analyst",
    "description": SECTOR_ANALYST_DESCRIPTION,
    "parameters": SECTOR_ANALYST_PARAMETERS,
    "function": run_sector_analyst,
}
