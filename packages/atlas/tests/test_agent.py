"""Smoke test — actually runs the Agent against the real LLM."""

from typing import Optional

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode
from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response


# ================================
# --> Fake data tools for testing
# ================================

@agent_tool(category="market_data")
def get_stock_quote(ticker: str) -> str:
    """Get the current price quote for a stock ticker.

    Args:
        ticker: The stock ticker symbol (e.g. AAPL, MSFT).
    """
    fake_prices = {
        "AAPL": 187.50, "MSFT": 415.20, "GOOGL": 172.80,
        "NVDA": 880.00, "TSLA": 245.30, "AMZN": 185.60,
    }
    price = fake_prices.get(ticker.upper())
    if price is None:
        return error_response(f"Unknown ticker: {ticker}")
    return success_response({
        "ticker": ticker.upper(),
        "price": price,
        "currency": "USD",
    })


@agent_tool(category="market_data")
def get_stock_history(
    ticker: str,
    days: int = 30,
) -> str:
    """Get historical daily closing prices for a stock.

    Args:
        ticker: The stock ticker symbol.
        days: Number of days of history to return.
    """
    return success_response({
        "ticker": ticker.upper(),
        "days": days,
        "prices": [100.0 + i * 0.5 for i in range(days)],
        "note": "Fake linear data for testing",
    })


@agent_tool(category="fundamentals")
def get_financials(
    ticker: str,
    period: Optional[str] = "annual",
) -> str:
    """Fetch income statement and balance sheet summary for a ticker.

    Args:
        ticker: The stock ticker symbol.
        period: Reporting period — 'annual' or 'quarterly'.
    """
    return success_response({
        "ticker": ticker.upper(),
        "period": period,
        "revenue": 394_328_000_000,
        "net_income": 96_995_000_000,
        "total_assets": 352_583_000_000,
        "note": "Fake AAPL-like data for testing",
    })


FAKE_TOOLS = [get_stock_quote, get_stock_history, get_financials]


def test_agent_chat_mode():
    """Smoke test: Agent.run() in chat mode with tool catalogue and fake data tools."""
    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
        deferred_tools=FAKE_TOOLS,
    )

    result = agent.run(
        user_message=(
            "Use register_tools to load the market_data category, "
            "then get a quote for AAPL. Report the price."
        ),
        max_iterations=15,
    )

    print(f"\n--- Chat mode results ---")
    print(f"Answer: {result.answer}")
    print(f"Iterations: {result.iterations}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Tool calls: {result.tool_calls_made}")
    print(f"Stop reason: {result.stop_reason}")
    print(f"Plan: {result.plan}")


def test_agent_plan_first_mode():
    """Smoke test: Agent.run() with plan_first=True using fake data tools."""
    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
        deferred_tools=FAKE_TOOLS,
    )

    result = agent.run(
        user_message=(
            "Use register_tools to load the market_data category, "
            "then get a quote for AAPL. After that, deploy a worker agent to fetch "
            "AAPL's financials using the get_financials tool — the worker should "
            "write a note with its findings. Finally, retrieve the notes and "
            "summarize everything."
        ),
        plan_first=True,
        max_iterations=50,
    )

    print(f"\n--- Plan-first mode results ---")
    print(f"Answer: {result.answer}")
    print(f"Iterations: {result.iterations}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Tool calls: {result.tool_calls_made}")
    print(f"Stop reason: {result.stop_reason}")
    print(f"Plan tasks: {[t.description for t in result.plan.tasks]}")


if __name__ == "__main__":
    test_agent_chat_mode()
    test_agent_plan_first_mode()
