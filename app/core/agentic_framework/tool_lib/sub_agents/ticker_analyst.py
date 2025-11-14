from app.core.agentic_framework.base_agent.sub_agent import SubAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from typing import Optional
from datetime import datetime
import yaml

# Import tool definitions from tool_lib
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_repository import FETCH_TICKER_REPOSITORY_DATA_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.technicals import TECHNICALS_TOOL
from app.utils.decorators.tool_validation import validate_ticker_arg, log_simulation_data_range


def build_ticker_analysis_prompt(ticker: str) -> str:
    """Create a concise, tool-aware user prompt for single-ticker analysis."""
    t = (ticker or "").upper()
    return (
        f"Analyze ticker {t} and deliver a concise, decision-ready view.\n"
        f"\n"
        f"Scope and constraints:\n"
        f"- Use tools only; cite exact figures with dates/periods from tool outputs.\n"
        f"- Prefer the most recent quarter and last 4 quarters for trends; note gaps.\n"
        f"- Keep output tight: answer first, then a compact evidence section.\n"
        f"\n"
        f"Data to gather (use only the available tools):\n"
        f"1) Fundamentals (get_ticker_fundamental_data):\n"
        f"   - statement_type=financial_ratios (last 4q)\n"
        f"   - statement_type=income_statement (last 4q)\n"
        f"   - statement_type=cash_flow (last 4q)\n"
        f"   - statement_type=balance_sheet (last 4q)\n"
        f"2) Repository (fetch_ticker_repository_data):\n"
        f"   - analyst_estimates (limit=4) for revisions/run-rate\n"
        f"   - ratings, analyst_recommendations, price_target_summary\n"
        f"   - stock_news and press_releases (last ~180 days) for catalysts\n"
        f"   - latest_transcript if available; otherwise earnings_transcripts(limit=1)\n"
        f"   - dividends_series for shareholder returns\n"
        f"3) Technicals (run_technicals):\n"
        f"   - indicators=['moving_averages','rsi','macd','adx','bollinger_bands','atr'] (weeks_back=52)\n"
        f"   - Report latest readings with dates; note trend vs MAs and momentum/volatility.\n"
        f"4) Performance & Risk (get_ticker_performance_and_risk):\n"
        f"   - Start with filters=['core']; add 'risk_metrics' or 'performance_metrics' only if needed.\n"
        f"   - Focus: vol, max_drawdown, beta; Sharpe, Sortino, CAGR; trailing total returns (3m/6m/1y/3y).\n"
        f"\n"
        f"What to answer up front (bullet points, max ~8 lines):\n"
        f"- Quality and momentum snapshot: growth (rev/EBIT/FCF), margins, ROE/ROIC if present.\n"
        f"- Balance sheet: leverage and liquidity signals, dividend policy if any.\n"
        f"- Street setup: rating mix, estimate direction, price target context.\n"
        f"- Technicals: trend vs MAs, momentum (RSI/MACD), trend strength (ADX).\n"
        f"- Risk/performance: vol, drawdown, beta; Sharpe/Sortino/CAGR; trailing returns.\n"
        f"- Near-term catalysts/risks from recent news/transcripts.\n"
        f"- Simple valuation context if ratios available (name the metric and period).\n"
        f"\n"
        f"Evidence section (compact):\n"
        f"- Table or bullets with key metrics by quarter (exact periods), estimate trends, ratings counts,\n"
        f"  concise technicals tables (with dates) and risk/performance metrics, transcript headline points,\n"
        f"  and 2-4 notable news items with dates.\n"
        f"\n"
        f"Deliverables:\n"
        f"1) A High level overall analysis of the ticker and a detailed description of your findings"
        f"\n"
        f"Ticker: {t}"
    )


class TickerAnalyst(SubAgent):
    def __init__(self, user_prompt: Optional[str] = None, ticker: Optional[str] = None, simulation_date: Optional[datetime] = None) -> None:
        if (not user_prompt) and ticker:
            user_prompt = build_ticker_analysis_prompt(ticker)

        super().__init__(
            user_prompt=user_prompt,
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            # provider="openai",
            # model="gpt-5.1",
            max_iterations=50,
            print_mode=PrintMode.SUBAGENT,
            temperature=0.7,
            plan_first=True,
            simulation_date=simulation_date
            )
        
        tools = [
            GET_TICKER_FUNDAMENTAL_DATA_TOOL,
            FETCH_TICKER_REPOSITORY_DATA_TOOL,
            GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
            CALCULATE_TICKER_FACTORS_TOOL,
            TECHNICALS_TOOL
        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )


    def run(self) -> str:
        return super().run()


# ============================= Tool Schema ============================= #

@validate_ticker_arg()
@log_simulation_data_range()
def ticker_analyst_sub_agent(ticker: str, _simulation_date: Optional[datetime] = None) -> str:
    """Execute comprehensive ticker analysis using the TickerAnalyst subagent.

    Args:
        ticker: Stock ticker symbol to analyze (e.g., 'AAPL', 'MSFT', 'KO')
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents.
                         If provided, analysis uses data available as of this date.

    Returns:
        Comprehensive analysis report including fundamentals, technicals, performance,
        risk metrics, analyst sentiment, and recent news/catalysts.
    """

    try:
        # Normalize ticker after validation for consistency
        tkr = ticker.strip().upper()
        analyst = TickerAnalyst(ticker=tkr, simulation_date=_simulation_date)
        output = analyst.run()

        final_answer = output["final_answer"]

        return yaml.dump({"success": True, "data": final_answer}, default_flow_style=False)
    except Exception as e:
        error_msg = f"Error running ticker analyst sub-agent: {str(e)}"
        print(f"⚠️  {error_msg}")
        return yaml.dump({"success": False, "error": error_msg}, default_flow_style=False)

# Tool Schema Constants
TICKER_ANALYST_DESCRIPTION = (
    "Execute a comprehensive, institutional-grade analysis of a single stock ticker using an autonomous AI analyst. "
    "This tool delegates to a specialized subagent that performs deep fundamental, technical, and sentiment analysis.\n"
    "\n**Analysis Coverage:**"
    "\n  • Fundamentals: Financial ratios, income statement, cash flow, balance sheet (last 4 quarters)"
    "\n  • Technicals: Moving averages, RSI, MACD, ADX, Bollinger Bands, ATR (52 weeks)"
    "\n  • Performance & Risk: Volatility, max drawdown, beta, Sharpe, Sortino, CAGR, trailing returns (3M/6M/1Y/3Y)"
    "\n  • Factor Analysis: Quality, value, momentum, growth, volatility factor exposures"
    "\n  • Analyst Sentiment: Ratings, recommendations, price targets, estimate trends"
    "\n  • News & Catalysts: Recent stock news, press releases, earnings transcripts (last ~180 days)"
    "\n  • Dividend Policy: Dividend history and yield analysis"
    "\n"
    "\n**Output Structure:**"
    "\n  1. Executive Summary (8-10 bullet points):"
    "\n     - Quality & momentum snapshot: revenue/EBIT/FCF growth, margins, ROE/ROIC"
    "\n     - Balance sheet health: leverage, liquidity, dividend policy"
    "\n     - Street sentiment: rating mix, estimate direction, price target context"
    "\n     - Technical setup: trend vs MAs, momentum (RSI/MACD), trend strength (ADX)"
    "\n     - Risk/performance profile: volatility, drawdown, beta, Sharpe/Sortino/CAGR"
    "\n     - Near-term catalysts and risks"
    "\n     - Valuation context (P/E, P/B, etc. with periods)"
    "\n"
    "\n  2. Evidence Section (compact, data-driven):"
    "\n     - Quarterly financial metrics tables (exact periods)"
    "\n     - Analyst estimate trends and rating counts"
    "\n     - Technical indicator tables with dates and latest readings"
    "\n     - Risk/performance metrics summary"
    "\n     - Key transcript highlights"
    "\n     - Notable news items (2-4 most relevant with dates)"
    "\n"
    "\n**When to Use:**"
    "\n  • Deep-dive analysis for portfolio construction decisions"
    "\n  • Pre-investment research requiring comprehensive view"
    "\n  • Risk assessment before position sizing"
    "\n  • Catalyst identification for timing entry/exit"
    "\n  • Competitive analysis within sector"
    "\n"
    "\n**Advantages Over Individual Tools:**"
    "\n  • Automated data gathering across 5+ different data sources"
    "\n  • Intelligent synthesis and cross-referencing of metrics"
    "\n  • Contextual interpretation (e.g., high beta + high volatility → risk flag)"
    "\n  • Time-efficient: single call vs 10+ manual tool calls"
    "\n  • Consistent analysis framework across all tickers"
    "\n"
    "\n**Example Use Cases:**"
    "\n  • CIO Agent: \"Analyze AAPL before adding to portfolio\""
    "\n  • Risk Agent: \"Assess downside risk for TSLA position\""
    "\n  • Sector Agent: \"Compare fundamental quality of XOM vs CVX\""
    "\n"
    "\n**Example:**"
    "\n  ticker_analyst_sub_agent(ticker='AAPL')"
)

TICKER_ANALYST_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "The stock ticker symbol to analyze (e.g., 'AAPL', 'MSFT', 'KO', 'GOOGL'). "
                "Must be a valid US equity ticker. The subagent will automatically gather "
                "all necessary data across fundamentals, technicals, performance, and sentiment."
            ),
            "pattern": "^[A-Z]{1,5}$",
            "minLength": 1,
            "maxLength": 5
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

TICKER_ANALYST_TOOL = {
    "name": "ticker_analyst_sub_agent",
    "description": TICKER_ANALYST_DESCRIPTION,
    "parameters": TICKER_ANALYST_PARAMETERS,
    "function": ticker_analyst_sub_agent,
}


if __name__ == "__main__":
    print(ticker_analyst_sub_agent(ticker="AAPL"))
