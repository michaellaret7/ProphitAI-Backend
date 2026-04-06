"""Test the past_ideas tool through a live agent.

Creates a bare Agent with only past_ideas registered, then runs three
sequential tasks that exercise read, write, and update_verdict operations.
Verifies the past_ideas.md file state after each operation.
"""

from functools import partial
from pathlib import Path

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_fund.tools import past_ideas


IDEAS_FILE = Path(__file__).parent.parent / "src" / "prophitai_fund" / "past_ideas.md"

SYSTEM_PROMPT = (
    "You are a test agent. You have one tool: past_ideas. "
    "Follow the user's instructions exactly — call the tool with the "
    "specified operation and parameters, then respond with 'done'."
)


# ================================
# --> Helper funcs
# ================================

def _build_agent() -> Agent:
    """Create an agent with only the past_ideas tool registered."""

    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        print_mode=PrintMode.VERBOSE,
    )

    agent.add_tool(**{**past_ideas.tool, "function": partial(past_ideas, IDEAS_FILE)})

    return agent


def _print_file_state(label: str) -> None:
    """Print the current contents of the ideas file."""

    content = IDEAS_FILE.read_text(encoding="utf-8").strip() if IDEAS_FILE.exists() else "(file does not exist)"

    print(f"\n--- {label} ---")
    print(content)


# ================================
# --> Test operations
# ================================

def test_read_empty() -> None:
    """Test 1: Read from an empty/nonexistent file."""

    print("\n========== TEST 1: READ (empty) ==========")

    agent = _build_agent()

    response = agent.run(
        "Call past_ideas with operation='read'. Report what you get back."
    )

    print("\n--- Agent Response ---")
    print(response.answer)

    _print_file_state("File After Read")


def test_write() -> None:
    """Test 2: Write a new idea."""

    print("\n========== TEST 2: WRITE ==========")

    agent = _build_agent()

    response = agent.run(
        "Call past_ideas with operation='write' and the following fields:\n"
        "- title: 'Volatility Risk Premium Harvest'\n"
        "- category: 'volatility'\n"
        "- description: 'Systematically sell short-dated index options to capture "
        "the persistent gap between implied and realized volatility. The strategy "
        "exploits the well-documented variance risk premium — option buyers consistently "
        "overpay for downside protection, creating a harvestable spread between implied "
        "and realized vol. Best expressed through 30-45 DTE put spreads on broad indices. "
        "Works across market regimes but requires careful tail-risk management during "
        "sudden vol spikes like Feb 2018 Volmageddon.'\n"
        "- edge: 'The variance risk premium — implied volatility consistently exceeds "
        "realized volatility by 2-4%% annualized. Option sellers earn this spread as "
        "compensation for bearing tail risk.'\n"
        "- universe: 'Broad equity indices (S&P 500, Nasdaq 100). High liquidity, tight "
        "bid-ask spreads, deep options markets. No single-name exposure.'\n"
        "- entry_exit: 'Sell 30-45 DTE put spreads when VIX/RV ratio exceeds 1.2. "
        "Exit at 21 DTE or 50%% profit target. Close immediately if VIX spikes above "
        "35 intraday.'\n"
        "- risk_management: 'Max 2-3%% portfolio notional per trade. Strict delta "
        "hedging when portfolio delta exceeds +/- 0.15. Long OTM puts at 10-delta as "
        "permanent tail hedge. Hard stop at -8%% monthly drawdown.'\n"
        "- research_backing: 'Carr & Wu (2009) document persistent VRP across asset "
        "classes. Coval & Shumway (2001) show put sellers earn excess returns. "
        "Israelov & Nielsen (2015) demonstrate VRP harvesting with Sharpe ~1.0 after "
        "transaction costs.'"
    )

    print("\n--- Agent Response ---")
    print(response.answer)

    _print_file_state("File After Write")

    content = IDEAS_FILE.read_text(encoding="utf-8")
    assert "name: Volatility Risk Premium Harvest" in content, "Idea name not found in frontmatter"
    assert "category: volatility" in content, "Category not found in frontmatter"
    assert "verdict: pending" in content, "Pending verdict not found in frontmatter"
    assert "### Description" in content, "Description section header missing"
    assert "### Edge" in content, "Edge section header missing"
    assert "### Universe" in content, "Universe section header missing"
    assert "### Entry & Exit" in content, "Entry & Exit section header missing"
    assert "### Risk Management" in content, "Risk Management section header missing"
    assert "### Research Backing" in content, "Research Backing section header missing"

    print("\nWrite test passed.")


def test_update_verdict() -> None:
    """Test 3: Update the verdict on the idea written in test 2."""

    print("\n========== TEST 3: UPDATE VERDICT ==========")

    agent = _build_agent()

    response = agent.run(
        "Call past_ideas with operation='update_verdict' and:\n"
        "- title: 'Volatility Risk Premium Harvest'\n"
        "- verdict: 'passed'\n"
        "- research_summary: 'Backtested 2010-2024 across 4 ticker combinations:\n"
        "1. SPY put spreads (30 DTE): Sharpe 1.4, max DD -12%%, Calmar 1.2\n"
        "2. QQQ put spreads (30 DTE): Sharpe 1.1, max DD -18%%, Calmar 0.6\n"
        "3. IWM put spreads (45 DTE): Sharpe 0.8, max DD -22%%, Calmar 0.4\n"
        "4. SPY+QQQ blended (30 DTE): Sharpe 1.3, max DD -14%%, Calmar 0.9\n\n"
        "SPY-only and blended approaches both viable. VRP signal positive in 85%% of months. "
        "Strategy failed during Feb 2018 Volmageddon (-15%% in 3 days) and Mar 2020 COVID "
        "(-22%% peak drawdown on QQQ leg). Adding 10-delta OTM put tail hedge reduced max "
        "DD to -8%% with Sharpe degradation of only 0.15. Recommended: SPY-only with "
        "permanent tail hedge.'"
    )

    print("\n--- Agent Response ---")
    print(response.answer)

    _print_file_state("File After Verdict Update")

    content = IDEAS_FILE.read_text(encoding="utf-8")
    assert "verdict: passed" in content, "Verdict not found in frontmatter"
    assert "verdict: pending" not in content, "Pending placeholder was not replaced"
    assert "### Research Results" in content, "Research Results section missing"

    print("\nUpdate verdict test passed.")


def run_all() -> None:
    """Run all three tests sequentially."""

    # Reason: start clean so test_read_empty sees an empty file
    if IDEAS_FILE.exists():
        IDEAS_FILE.unlink()

    test_read_empty()
    test_write()
    test_update_verdict()

    print("\n========== ALL TESTS PASSED ==========")


if __name__ == "__main__":
    run_all()
