"""Worker tool setup - available tools registry and schema constants."""

from typing import Any, Dict, List

from app.core.atlas.models.notebook import Notebook
from app.core.atlas.tools.responses import error_response

# --- ticker ---
from app.core.atlas.tools.ticker.performance import ticker_performance
from app.core.atlas.tools.ticker.risk import ticker_risk
from app.core.atlas.tools.ticker.factors import ticker_factors
from app.core.atlas.tools.ticker.technicals import ticker_technicals

# --- news ---
from app.core.atlas.tools.news import general_news, get_ticker_news, get_press_releases

# --- fundamentals ---
from app.core.atlas.tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from app.core.atlas.tools.ticker.fundamentals.estimates import get_analyst_estimates
from app.core.atlas.tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from app.core.atlas.tools.ticker.fundamentals.price_target import get_price_target_data

# --- info ---
from app.core.atlas.tools.ticker.info.description import get_ticker_info, get_etf_info
from app.core.atlas.tools.ticker.info.peers import get_ticker_peers
from app.core.atlas.tools.ticker.info.ratings import get_stock_ratings
from app.core.atlas.tools.ticker.info.institutional_holders import get_institutional_holders
from app.core.atlas.tools.ticker.info.product_segmentation import get_product_segmentation
from app.core.atlas.tools.ticker.info.sectors import get_sector_industries, get_group_tickers
from app.core.atlas.tools.ticker.info.etf_holdings import get_etf_holdings

# --- screener ---
from app.core.atlas.tools.screener.equity_screener import equity_screener
from app.core.atlas.tools.screener.etf_screener import etf_screener

# --- research ---
from app.core.atlas.tools.research.credit_research import credit_research_search
from app.core.atlas.tools.research.earnings_calls import earnings_call_search
from app.core.atlas.tools.research.economics_research import economics_research_search
from app.core.atlas.tools.research.macro_research import macro_research
from app.core.atlas.tools.research.tax_research import tax_research_search
from app.core.atlas.tools.research.theory_research import theory_research
from app.core.atlas.tools.research.user_uploads import user_upload_search

# --- portfolio ---
from app.core.atlas.tools.portfolio.allocator import portfolio_allocator
from app.core.atlas.tools.portfolio.performance import portfolio_performance
from app.core.atlas.tools.portfolio.risk import portfolio_risk
from app.core.atlas.tools.portfolio.stress_test import portfolio_stress_test
from app.core.atlas.tools.portfolio.factor_exposure import portfolio_factor_exposure
from app.core.atlas.tools.portfolio.classification import portfolio_classification
from app.core.atlas.tools.portfolio.user_portfolio import get_user_simulated_portfolio

# --- macro ---
from app.core.atlas.tools.macro.commodity_prices import commodity_prices
from app.core.atlas.tools.macro.us_rates import us_treasury_rates
from app.core.atlas.tools.macro.indicators import macro_indicators

# --- watchlist ---
from app.core.atlas.tools.watchlist.get_watchlist import get_watchlist

# --- broker ---
from app.core.atlas.tools.broker.account import account_info
from app.core.atlas.tools.broker.portfolio import (
    get_positions, close_position,
)
from app.core.atlas.tools.broker.trade import propose_trade
from app.core.atlas.tools.broker.orders import (
    get_order_impact, get_orders, cancel_order, get_quotes,
)
from app.core.atlas.tools.broker.options_trade import (
    propose_options_trade, propose_multi_leg_options_trade,
)

# --- options ---
from app.core.atlas.tools.options.expirations import get_option_expirations
from app.core.atlas.tools.options.contracts import get_option_contracts
from app.core.atlas.tools.options.chain import get_options_chain
from app.core.atlas.tools.options.quote import get_option_quote
from app.core.atlas.tools.options.price_history import get_option_price_history


# ==============================================================================
# AVAILABLE TOOLS — built DRY from @agent_tool-decorated functions
# ==============================================================================

_ALL_TOOL_FUNCTIONS = [
    # ticker (5)
    ticker_performance, ticker_risk, ticker_factors, ticker_technicals,
    get_ticker_news,
    # news (1)
    get_press_releases,
    # fundamentals (4)
    get_ticker_fundamental_data, get_analyst_estimates, get_ratios_ttm, get_price_target_data,
    # info (9)
    get_ticker_info, get_etf_info, get_ticker_peers, get_stock_ratings,
    get_institutional_holders, get_product_segmentation,
    get_sector_industries, get_group_tickers, get_etf_holdings,
    # screener (2)
    equity_screener, etf_screener,
    # research (8)
    credit_research_search, earnings_call_search, economics_research_search,
    general_news, macro_research, tax_research_search, theory_research, user_upload_search,
    # portfolio (7)
    portfolio_allocator, portfolio_performance, portfolio_risk, portfolio_stress_test,
    portfolio_factor_exposure, portfolio_classification, get_user_simulated_portfolio,
    # macro (3)
    commodity_prices, us_treasury_rates, macro_indicators,
    # watchlist (1)
    get_watchlist,
    # broker (11)
    account_info, get_positions, close_position,
    propose_trade, propose_options_trade, propose_multi_leg_options_trade,
    get_orders, cancel_order, get_quotes, get_order_impact,
    # options (5)
    get_option_expirations, get_option_contracts, get_options_chain,
    get_option_quote, get_option_price_history,
]

AVAILABLE_TOOLS: Dict[str, Dict[str, Any]] = {
    func.tool["name"]: func.tool for func in _ALL_TOOL_FUNCTIONS
}


def build_tool_catalog() -> str:
    """One-line description per tool for the orchestrator's system prompt."""
    lines = []
    for name in sorted(AVAILABLE_TOOLS):
        desc = AVAILABLE_TOOLS[name].get("description", "")
        short = desc.split(".")[0].strip()
        lines.append(f"- **{name}**: {short}")
    return "\n".join(lines)


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

DEPLOY_WORKER_DESCRIPTION = (
    "Deploy a focused worker agent to autonomously execute a specific sub-task. "
    "The worker runs its own tool-calling loop with the tools you select and returns "
    "a structured result.\n\n"
    "**WHEN TO USE:**\n"
    "- Research tasks: earnings call analysis, news summarization, sector deep-dives\n"
    "- Data-heavy analysis that requires multiple sequential tool calls\n"
    "- Any focused sub-task that benefits from isolated execution\n\n"
    "**HOW IT WORKS:**\n"
    "1. Provide a clear, detailed task description\n"
    "2. Select the tools the worker needs from the available set\n"
    "3. The worker agent executes autonomously and returns results\n"
    "4. Worker write_note calls are saved in orchestrator memory for later review\n\n"
    "**TIPS FOR GOOD TASK DESCRIPTIONS:**\n"
    "- Be specific about what data to gather and what output format you expect\n"
    "- Include relevant context (tickers, time periods, metrics of interest)\n"
    "- State the end goal clearly so the worker knows when it's done\n\n"
    "**IMPORTANT:** Always pass the plan_task_id of the plan task you are working on.\n\n"
    "Example: deploy_worker_agent(\n"
    "  task='Research the latest earnings call for AAPL. Summarize key metrics, "
    "management guidance, and notable analyst Q&A.',\n"
    "  tools=['earnings_call_search', 'get_ticker_news'],\n"
    "  plan_task_id='1'\n"
    ")"
)

DEPLOY_WORKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": (
                "A clear, detailed description of the task for the worker agent. "
                "Include all relevant context: tickers, time periods, metrics, "
                "and desired output format."
            )
        },
        "tools": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": sorted(AVAILABLE_TOOLS.keys()),
            },
            "description": "List of tool names to equip the worker agent with.",
            "minItems": 1
        },
        "plan_task_id": {
            "type": "string",
            "description": "The plan task ID this worker is being deployed for (e.g., '1', '2')."
        }
    },
    "required": ["task", "tools", "plan_task_id"],
    "additionalProperties": False
}

# Reason: WorkerAgent auto-registers these via AgentBase and its own __init__,
# so the orchestrator may redundantly request them. Skip silently.
_WORKER_DEFAULT_TOOLS = {"think", "calculator", "llm_web_search", "write_note"}


def _resolve_and_deploy(
    notebook: Notebook, chat_callback: Any,
    task: str, tools: List[str], plan_task_id: str = "",
) -> str:
    """Resolve tool name strings to tool dicts, then deploy the worker agent.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via partial).
        task: Task description from the orchestrator LLM.
        tools: List of tool name strings from the orchestrator LLM.
        plan_task_id: The plan task ID this worker is deployed for.
    """
    from app.core.atlas.tools.worker_agent.worker import deploy_worker_agent

    tool_defs = []
    for name in tools:
        if name in _WORKER_DEFAULT_TOOLS:
            continue
        tool = AVAILABLE_TOOLS.get(name)
        if tool is None:
            return error_response(
                f"Unknown tool '{name}'. Available: {sorted(AVAILABLE_TOOLS.keys())}"
            )
        tool_defs.append(tool)

    return deploy_worker_agent(
        notebook=notebook,
        chat_callback=chat_callback,
        task=task,
        tools=tool_defs,
        plan_task_id=plan_task_id,
    )


# Reason: `function` is intentionally omitted — it must be bound via
# functools.partial(_resolve_and_deploy, notebook) at registration time.
DEPLOY_WORKER_TOOL = {
    "name": "deploy_worker_agent",
    "description": DEPLOY_WORKER_DESCRIPTION,
    "parameters": DEPLOY_WORKER_PARAMETERS,
}
