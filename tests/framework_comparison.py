"""Framework comparison: Agno vs Atlas on identical prompts, tools, and LLM.

Runs both agent frameworks through 3 prompts of increasing complexity using
the same 6 tools, system prompt, and LLM (gpt-4o at temperature 0.0).
Compares wall-clock time, token usage, tool-calling patterns, and output quality.

NOTE: Atlas token count reflects the LAST iteration only due to assignment
(not accumulation) in ExecutionLoop._track_token_usage (loop.py:186).
"""

import sys
import os
import time
from dataclasses import dataclass
from typing import List, Tuple

# Reason: Windows cp1252 can't encode Unicode chars used by Atlas printer
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Reason: ensure project root is on sys.path for Atlas imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat

from app.core.atlas.agents.chat_agent import ChatAgent
from app.core.atlas.models import PrintMode
from app.core.atlas.tools.base.think import think
from app.core.atlas.tools.base.calculator import calculator
from app.core.atlas.tools.ticker.performance import ticker_performance
from app.core.atlas.tools.ticker.risk import ticker_risk
from app.core.atlas.tools.portfolio.risk import portfolio_risk
from app.core.atlas.tools.ticker.technicals import ticker_technicals


# ================================
# --> Constants
# ================================

MODEL = "gpt-4o"
TEMPERATURE = 0.0
MAX_ITERATIONS = 20

SYSTEM_PROMPT = (
    "You are QuantAnalyst, an expert quantitative financial analyst. "
    "You have access to the following tools:\n\n"
    "1. think - Reason through complex problems step by step before acting.\n"
    "2. calculator - Evaluate mathematical expressions (last resort only).\n"
    "3. ticker_performance - Comprehensive performance metrics for a single stock.\n"
    "4. ticker_risk - Comprehensive risk metrics for a single stock.\n"
    "5. portfolio_risk - Risk metrics for a multi-asset portfolio.\n"
    "6. ticker_technicals - Technical indicator time series for a stock.\n\n"
    "Guidelines:\n"
    "- Use the think tool to plan your approach before starting analysis.\n"
    "- Gather quantitative evidence using the data tools.\n"
    "- Synthesize findings into clear, actionable insights.\n"
    "- Be precise with numbers and cite specific metrics.\n"
    "- Keep your final answer concise but thorough."
)

TOOL_FUNCTIONS = [
    think, calculator, ticker_performance,
    ticker_risk, portfolio_risk, ticker_technicals,
]

TEST_PROMPTS = [
    (
        "Concentrated Tech Hedge",
        "You advise a client holding a concentrated tech portfolio: NVDA (40%), META (30%), AMZN (30%). "
        "They are worried about a tech correction. "
        "1) Analyze the portfolio's overall risk profile. "
        "2) Analyze each holding's individual risk AND momentum technicals. "
        "3) Based on the combined evidence, should the client reduce exposure? "
        "If so, which position should be trimmed first and why? Cite specific metrics.",
    ),
    (
        "Multi-Horizon Regime Shift",
        "Analyze TSLA across three time horizons: 1 year, 3 years, and 5 years. "
        "For EACH horizon get both performance metrics and risk metrics. "
        "Then pull the latest 20-day momentum and volatility technicals. "
        "Identify where the short-term and long-term pictures diverge. "
        "Is TSLA currently in a regime shift? Support your conclusion with numbers.",
    ),
    (
        "Portfolio Construction",
        "A client wants a 5-stock portfolio selected from these 8 candidates: "
        "AAPL, GOOGL, JPM, XOM, UNH, PG, COST, LLY. "
        "Analyze the risk and performance profile of every candidate over 2 years. "
        "Then construct the optimal 5-stock portfolio that minimizes drawdown risk "
        "while maintaining reasonable upside. "
        "Provide specific decimal weight allocations, run portfolio_risk on your proposed portfolio, "
        "and justify each pick and weight with data.",
    ),
]


# ================================
# --> Data model
# ================================

@dataclass
class RunResult:
    """Captured metrics from a single agent run."""

    framework: str
    prompt_label: str
    wall_time_s: float
    tokens_used: int
    iterations: int
    tool_calls: List[str]
    stop_reason: str
    answer: str


# ================================
# --> Agent builders
# ================================

def build_agno_agent() -> AgnoAgent:
    """Create a fresh Agno agent with shared config."""
    return AgnoAgent(
        model=OpenAIChat(id=MODEL, temperature=TEMPERATURE),
        instructions=SYSTEM_PROMPT,
        tools=TOOL_FUNCTIONS,
    )


def build_atlas_agent() -> ChatAgent:
    """Create a fresh Atlas ChatAgent with shared config."""
    agent = ChatAgent(
        provider="openai",
        model=MODEL,
        max_iterations=MAX_ITERATIONS,
        temperature=TEMPERATURE,
        system_prompt=SYSTEM_PROMPT,
        print_mode=PrintMode.PRODUCTION,
    )
    # Reason: think and calculator are auto-registered in AgentBase.__init__
    for tool_fn in [ticker_performance, ticker_risk, portfolio_risk, ticker_technicals]:
        agent.add_tool(**tool_fn.tool)
    return agent


# ================================
# --> Run functions
# ================================

def run_agno(prompt: str, label: str) -> RunResult:
    """Execute a single prompt through Agno and capture metrics."""
    agent = build_agno_agent()
    start = time.perf_counter()

    try:
        response = agent.run(prompt)
    except Exception as e:
        elapsed = time.perf_counter() - start
        return RunResult(
            framework="Agno", prompt_label=label, wall_time_s=elapsed,
            tokens_used=0, iterations=0, tool_calls=[],
            stop_reason=f"ERROR: {e}", answer=str(e),
        )

    elapsed = time.perf_counter() - start

    # Reason: safely extract token metrics from Agno's RunMetrics
    tokens = 0
    iterations = 0
    if response.metrics and response.metrics.details:
        model_metrics = response.metrics.details.get("model", [])
        tokens = sum(getattr(m, "total_tokens", 0) or 0 for m in model_metrics)
        iterations = len(model_metrics)

    tool_calls = [t.tool_name for t in (response.tools or []) if t.tool_name]
    answer = str(response.content) if response.content else ""

    return RunResult(
        framework="Agno",
        prompt_label=label,
        wall_time_s=elapsed,
        tokens_used=tokens,
        iterations=iterations,
        tool_calls=tool_calls,
        stop_reason="completed",
        answer=answer,
    )


def run_atlas(prompt: str, label: str) -> RunResult:
    """Execute a single prompt through Atlas and capture metrics."""
    agent = build_atlas_agent()
    start = time.perf_counter()

    try:
        response = agent.run(user_message=prompt)
    except Exception as e:
        elapsed = time.perf_counter() - start
        return RunResult(
            framework="Atlas", prompt_label=label, wall_time_s=elapsed,
            tokens_used=0, iterations=0, tool_calls=[],
            stop_reason=f"ERROR: {e}", answer=str(e),
        )

    elapsed = time.perf_counter() - start

    return RunResult(
        framework="Atlas",
        prompt_label=label,
        wall_time_s=elapsed,
        tokens_used=response.tokens_used,
        iterations=response.iterations,
        tool_calls=response.tool_calls_made,
        stop_reason=response.stop_reason,
        answer=response.answer,
    )


# ================================
# --> Comparison runner
# ================================

def run_comparison() -> List[Tuple[RunResult, RunResult]]:
    """Run all test prompts through both frameworks and collect results."""
    results: List[Tuple[RunResult, RunResult]] = []

    for label, prompt in TEST_PROMPTS:
        print(f"\n{'-' * 60}")
        print(f"  Running: {label}")
        print(f"{'-' * 60}")

        print("  > Agno  ...", end=" ", flush=True)
        agno_result = run_agno(prompt, label)
        print(f"done ({agno_result.wall_time_s:.1f}s)")

        print("  > Atlas ...", end=" ", flush=True)
        atlas_result = run_atlas(prompt, label)
        print(f"done ({atlas_result.wall_time_s:.1f}s)")

        results.append((agno_result, atlas_result))

    return results


# ================================
# --> Report printer
# ================================

def _print_prompt_section(agno: RunResult, atlas: RunResult) -> None:
    """Print comparison for a single prompt."""
    prompt_text = next(p for l, p in TEST_PROMPTS if l == agno.prompt_label)
    truncated = f"{prompt_text[:80]}..." if len(prompt_text) > 80 else prompt_text

    print(f"\n--- Prompt: {agno.prompt_label} {'-' * (48 - len(agno.prompt_label))}")
    print(f'  "{truncated}"')

    # Metrics table
    print(f"\n  {'Metric':<22} {'Agno':>14} {'Atlas':>14}")
    print(f"  {'-' * 50}")
    print(f"  {'Wall Time (s)':<22} {agno.wall_time_s:>14.2f} {atlas.wall_time_s:>14.2f}")
    print(f"  {'Tokens Used':<22} {agno.tokens_used:>14,} {atlas.tokens_used:>14,}*")
    print(f"  {'Iterations':<22} {agno.iterations:>14} {atlas.iterations:>14}")
    print(f"  {'Tool Calls':<22} {len(agno.tool_calls):>14} {len(atlas.tool_calls):>14}")
    print(f"  {'Stop Reason':<22} {agno.stop_reason:>14} {atlas.stop_reason:>14}")

    # Tool call sequences
    print(f"\n  Tool Call Sequence:")
    agno_seq = " -> ".join(agno.tool_calls) if agno.tool_calls else "(none)"
    atlas_seq = " -> ".join(atlas.tool_calls) if atlas.tool_calls else "(none)"
    print(f"    Agno:  {agno_seq}")
    print(f"    Atlas: {atlas_seq}")

    # Answer previews
    print(f"\n  Answer Preview (first 500 chars):")
    for fw, result in [("Agno", agno), ("Atlas", atlas)]:
        print(f"    {fw}:")
        for line in result.answer[:500].split("\n"):
            print(f"      {line}")
        if len(result.answer) > 500:
            print(f"      ...")


def print_report(results: List[Tuple[RunResult, RunResult]]) -> None:
    """Print the full formatted comparison report."""
    sep = "=" * 65

    print(f"\n\n{sep}")
    print("  FRAMEWORK COMPARISON: Agno vs Atlas")
    print(f"  Model: {MODEL} | Temp: {TEMPERATURE} | Max Iters: {MAX_ITERATIONS}")
    print(sep)

    for agno, atlas in results:
        _print_prompt_section(agno, atlas)

    # Aggregate summary
    n = len(results)
    agno_time = sum(a.wall_time_s for a, _ in results)
    atlas_time = sum(b.wall_time_s for _, b in results)
    agno_tokens = sum(a.tokens_used for a, _ in results)
    atlas_tokens = sum(b.tokens_used for _, b in results)
    agno_tools = sum(len(a.tool_calls) for a, _ in results)
    atlas_tools = sum(len(b.tool_calls) for _, b in results)

    print(f"\n{sep}")
    print("  AGGREGATE SUMMARY")
    print(sep)
    print(f"\n  {'Metric':<22} {'Agno':>14} {'Atlas':>14}")
    print(f"  {'-' * 50}")
    print(f"  {'Total Time (s)':<22} {agno_time:>14.2f} {atlas_time:>14.2f}")
    print(f"  {'Total Tokens':<22} {agno_tokens:>14,} {atlas_tokens:>14,}*")
    print(f"  {'Total Tool Calls':<22} {agno_tools:>14} {atlas_tools:>14}")
    print(f"  {'Avg Time/Prompt (s)':<22} {agno_time / n:>14.2f} {atlas_time / n:>14.2f}")
    print(f"  {'Avg Tokens/Prompt':<22} {agno_tokens / n:>14,.0f} {atlas_tokens / n:>14,.0f}*")
    print(f"\n  * Atlas token count reflects LAST iteration only")
    print(f"    (assignment, not accumulation in ExecutionLoop._track_token_usage)")
    print()


# ================================
# --> Entrypoint
# ================================

if __name__ == "__main__":
    results = run_comparison()
    print_report(results)
