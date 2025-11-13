from app.core.agentic_framework.base_agent.sub_agent import SubAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from typing import Optional

# Import tool definitions from tool_lib
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_repository import FETCH_TICKER_REPOSITORY_DATA_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.technicals import TECHNICALS_TOOL


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
    def __init__(self, user_prompt: Optional[str] = None, ticker: Optional[str] = None) -> None:
        if (not user_prompt) and ticker:
            user_prompt = build_ticker_analysis_prompt(ticker)

        super().__init__(
            user_prompt=user_prompt,
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            max_iterations=50,
            print_mode=PrintMode.VERBOSE,
            temperature=0.7,
            plan_first=True
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


if __name__ == "__main__":
    agent = TickerAnalyst(ticker="AAPL")
    agent.run()