"""Test all agent prompt configurations after restructure.

Tests:
1. Agent with no system_prompt (generic base prompt fallback)
2. Agent with custom chat system_prompt (as chat_executor would)
3. WatchlistAgent with orchestrator system_prompt
4. PortfolioBuilderAgent with orchestrator system_prompt
"""

import traceback
from typing import Optional

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode
from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_atlas.prompts.base import build_base_system_prompt
from prophitai_atlas.prompts.plan_injection import inject_plan_tasks


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
def get_stock_history(ticker: str, days: int = 30) -> str:
    """Get historical daily closing prices for a stock.

    Args:
        ticker: The stock ticker symbol.
        days: Number of days of history to return.
    """
    return success_response({
        "ticker": ticker.upper(),
        "days": days,
        "prices": [100.0 + i * 0.5 for i in range(days)],
    })


@agent_tool(category="fundamentals")
def get_financials(ticker: str, period: Optional[str] = "annual") -> str:
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
    })


@agent_tool(category="screener")
def equity_screener(sector: Optional[str] = None) -> str:
    """Screen equities by sector and criteria.

    Args:
        sector: Optional sector filter (e.g. 'Technology', 'Healthcare').
    """
    return success_response({
        "results": [
            {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market_cap": 2900000000000},
            {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "market_cap": 3100000000000},
            {"ticker": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "market_cap": 2200000000000},
        ]
    })


@agent_tool(category="ticker_analytics")
def ticker_performance(tickers: str) -> str:
    """Get performance metrics for one or more tickers.

    Args:
        tickers: Comma-separated ticker symbols.
    """
    return success_response({
        "results": [
            {"ticker": "AAPL", "ytd_return": 0.12, "1y_return": 0.25, "volatility": 0.22},
            {"ticker": "MSFT", "ytd_return": 0.08, "1y_return": 0.18, "volatility": 0.19},
        ]
    })


@agent_tool(category="risk")
def portfolio_risk(tickers: str, weights: str) -> str:
    """Calculate portfolio risk metrics.

    Args:
        tickers: Comma-separated ticker symbols.
        weights: Comma-separated portfolio weights (decimal).
    """
    return success_response({
        "portfolio_volatility": 0.18,
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.15,
        "var_95": -0.025,
    })


FAKE_TOOLS = [
    get_stock_quote, get_stock_history, get_financials,
    equity_screener, ticker_performance, portfolio_risk,
]


# ================================
# --> Helper
# ================================

def print_result(label: str, result):
    """Print agent result summary."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Answer: {result.answer[:300]}{'...' if len(result.answer) > 300 else ''}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Tokens: {result.tokens_used}")
    print(f"  Tool calls: {result.tool_calls_made}")
    print(f"  Stop reason: {result.stop_reason}")
    if result.plan:
        print(f"  Plan tasks: {[t.description for t in result.plan.tasks]}")
    print()


def run_test(name: str, fn):
    """Run a test function and report pass/fail."""
    print(f"\n>>> Running: {name}")
    try:
        fn()
        print(f"<<< PASSED: {name}")
        return (name, True, None)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"<<< FAILED: {name}\n{tb}")
        return (name, False, str(e))


# ================================
# --> Test 1: Agent with generic base prompt (no system_prompt)
# ================================

def test_agent_base_prompt():
    """Agent with no system_prompt should use generic base prompt and work for simple queries."""
    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
        deferred_tools=FAKE_TOOLS,
        # no system_prompt — should use build_base_system_prompt
    )

    # Verify the system_prompt contains base prompt markers
    assert "Dynamic Tool Registration" in agent.system_prompt, "Base prompt missing tool registration section"
    assert "expert financial" not in agent.system_prompt, "Base prompt should NOT contain domain-specific language"

    result = agent.run(
        user_message=(
            "Use register_tools to load the market_data category, "
            "then get a quote for AAPL. Report the price."
        ),
        max_iterations=15,
    )

    assert result.stop_reason == "answer_ready", f"Expected answer_ready, got {result.stop_reason}"
    assert result.answer, "Answer should not be empty"
    assert len(result.tool_calls_made) > 0, "Should have made tool calls"
    print_result("Test 1: Agent with generic base prompt", result)


# ================================
# --> Test 2: Agent with custom chat system_prompt
# ================================

def test_agent_custom_chat_prompt():
    """Agent with chat system_prompt (as chat_executor does) should use it as-is."""
    from prophitai_api.agents.prompts import build_chat_system_prompt

    chat_prompt = build_chat_system_prompt()

    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
        deferred_tools=FAKE_TOOLS,
        system_prompt=chat_prompt,
    )

    # Verify the agent uses the chat prompt, not the base prompt
    assert "expert financial research analyst" in agent.system_prompt, "Should use the chat prompt"
    assert "3-Tier Decision Framework" in agent.system_prompt, "Chat prompt should have decision framework"
    assert "<deferred_tools>" in agent.system_prompt, "Deferred tools should be appended"

    result = agent.run(
        user_message="What's AAPL trading at?",
        max_iterations=15,
    )

    assert result.stop_reason == "answer_ready", f"Expected answer_ready, got {result.stop_reason}"
    assert result.answer, "Answer should not be empty"
    print_result("Test 2: Agent with chat system_prompt", result)


# ================================
# --> Test 3: Agent with orchestrator prompt + plan_first
# ================================

def test_agent_orchestrator_prompt_plan_first():
    """Agent with orchestrator system_prompt in plan_first mode should inject plan tasks."""
    from prophitai_api.agents.prompts import build_orchestrator_system_prompt

    orchestrator_prompt = build_orchestrator_system_prompt()

    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
        deferred_tools=FAKE_TOOLS,
        system_prompt=orchestrator_prompt,
    )

    # Verify the agent uses the orchestrator prompt
    assert "orchestrator agent" in agent.system_prompt, "Should use the orchestrator prompt"
    assert "Deploy Multiple Workers" in agent.system_prompt, "Orchestrator prompt should have worker rules"
    assert "<deferred_tools>" in agent.system_prompt, "Deferred tools should be appended"

    result = agent.run(
        user_message=(
            "Screen for technology stocks, then analyze the top candidates' "
            "fundamentals and performance. Build a summary of the best picks."
        ),
        plan_first=True,
        max_iterations=50,
    )

    assert result.stop_reason == "answer_ready", f"Expected answer_ready, got {result.stop_reason}"
    assert result.answer, "Answer should not be empty"
    assert result.plan is not None, "Plan should exist in plan_first mode"
    assert len(result.plan.tasks) > 0, "Plan should have tasks"
    print_result("Test 3: Agent with orchestrator prompt + plan_first", result)


# ================================
# --> Test 4: WatchlistAgent end-to-end
# ================================

def test_watchlist_agent():
    """WatchlistAgent should initialize with orchestrator prompt and run plan_first."""
    from prophitai_api.agents.watchlist import WatchlistAgent

    agent = WatchlistAgent(
        user_preferences="Find 5 AI infrastructure stocks with strong revenue growth",
    )

    # Verify the internal agent uses orchestrator prompt
    assert "orchestrator agent" in agent._agent.system_prompt, "Should use orchestrator prompt"

    result = agent.run()

    assert result.stop_reason == "answer_ready", f"Expected answer_ready, got {result.stop_reason}"
    assert result.answer, "Answer should not be empty"
    assert result.plan is not None, "Should have a plan"
    print_result("Test 4: WatchlistAgent end-to-end", result)


# ================================
# --> Test 5: PortfolioBuilderAgent end-to-end
# ================================

def test_portfolio_builder_agent():
    """PortfolioBuilderAgent should initialize with orchestrator prompt and run plan_first."""
    from prophitai_api.agents.portfolio_builder import PortfolioBuilderAgent

    agent = PortfolioBuilderAgent(
        user_preferences="Build a 5-stock technology portfolio focused on AI with equal weights",
    )

    # Verify the internal agent uses orchestrator prompt
    assert "orchestrator agent" in agent._agent.system_prompt, "Should use orchestrator prompt"

    result = agent.run()

    assert result.stop_reason == "answer_ready", f"Expected answer_ready, got {result.stop_reason}"
    assert result.answer, "Answer should not be empty"
    assert result.plan is not None, "Should have a plan"
    print_result("Test 5: PortfolioBuilderAgent end-to-end", result)


# ================================
# --> Test 6: inject_plan_tasks utility
# ================================

def test_inject_plan_tasks_utility():
    """inject_plan_tasks should append plan tasks to any base prompt string."""
    from prophitai_atlas.models.new_plan import Plan, PlanTask

    plan = Plan(tasks=[
        PlanTask(id="task_1", step=1, description="Screen for candidates"),
        PlanTask(id="task_2", step=1, description="Research macro environment"),
        PlanTask(id="task_3", step=2, description="Analyze top candidates deeply"),
    ])

    base = "You are a test agent."
    result = inject_plan_tasks(base, plan)

    assert "You are a test agent." in result, "Should preserve base prompt"
    assert "## Your Plan" in result, "Should have plan section"
    assert "Step 1 (parallel):" in result, "Should group parallel tasks"
    assert "task_1. Screen for candidates" in result, "Should include task 1"
    assert "task_2. Research macro environment" in result, "Should include task 2"
    assert "Step 2: task_3. Analyze top candidates deeply" in result, "Should include task 3"
    assert "update_plan" in result, "Should reference update_plan tool"

    print("\n" + "="*60)
    print("  Test 6: inject_plan_tasks utility")
    print("="*60)
    print("  All assertions passed")
    print(f"  Result length: {len(result)} chars")
    print(f"  Preview: ...{result[-200:]}")
    print()


# ================================
# --> Main
# ================================

if __name__ == "__main__":
    results = []

    # Unit test first (fast, no LLM calls)
    results.append(run_test("inject_plan_tasks utility", test_inject_plan_tasks_utility))

    # Agent tests (LLM calls)
    results.append(run_test("Agent with generic base prompt", test_agent_base_prompt))
    results.append(run_test("Agent with chat system_prompt", test_agent_custom_chat_prompt))
    results.append(run_test("Agent with orchestrator + plan_first", test_agent_orchestrator_prompt_plan_first))

    # Domain agent tests (real tools, LLM calls)
    results.append(run_test("WatchlistAgent e2e", test_watchlist_agent))
    results.append(run_test("PortfolioBuilderAgent e2e", test_portfolio_builder_agent))

    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" — {err}" if err else ""))
    print(f"\n  {passed}/{len(results)} passed, {failed} failed")
    print("="*60)
