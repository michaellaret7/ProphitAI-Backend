"""Worker tool setup - available tools registry and schema constants."""

from typing import Any, Dict, List

from app.core.atlas.models.notebook import Notebook
from app.core.atlas.tools_v2.responses import error_response

# --- ticker ---
from app.core.atlas.tools_v2.ticker.performance import ticker_performance
from app.core.atlas.tools_v2.ticker.risk import ticker_risk
from app.core.atlas.tools_v2.ticker.factors import ticker_factors
from app.core.atlas.tools_v2.ticker.technicals import ticker_technicals

# --- news ---
from app.core.atlas.tools_v2.news import general_news, get_ticker_news, get_press_releases

# --- fundamentals ---
from app.core.atlas.tools_v2.ticker.fundamentals.statements import get_ticker_fundamental_data
from app.core.atlas.tools_v2.ticker.fundamentals.estimates import get_analyst_estimates
from app.core.atlas.tools_v2.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from app.core.atlas.tools_v2.ticker.fundamentals.price_target import get_price_target_data

# --- info ---
from app.core.atlas.tools_v2.ticker.info.description import get_ticker_info, get_etf_info
from app.core.atlas.tools_v2.ticker.info.peers import get_ticker_peers
from app.core.atlas.tools_v2.ticker.info.ratings import get_stock_ratings
from app.core.atlas.tools_v2.ticker.info.institutional_holders import get_institutional_holders
from app.core.atlas.tools_v2.ticker.info.product_segmentation import get_product_segmentation

# --- screener ---
from app.core.atlas.tools_v2.screener.equity_screener import equity_screener
from app.core.atlas.tools_v2.screener.etf_screener import etf_screener

# --- research ---
from app.core.atlas.tools_v2.research.credit_research import credit_research_search
from app.core.atlas.tools_v2.research.earnings_calls import earnings_call_search
from app.core.atlas.tools_v2.research.economics_research import economics_research_search
from app.core.atlas.tools_v2.research.macro_research import macro_research
from app.core.atlas.tools_v2.research.tax_research import tax_research_search
from app.core.atlas.tools_v2.research.user_uploads import user_upload_search

# --- portfolio ---
from app.core.atlas.tools_v2.portfolio.allocator import portfolio_allocator
from app.core.atlas.tools_v2.portfolio.performance import portfolio_performance
from app.core.atlas.tools_v2.portfolio.risk import portfolio_risk
from app.core.atlas.tools_v2.portfolio.stress_test import portfolio_stress_test
from app.core.atlas.tools_v2.portfolio.factor_exposure import portfolio_factor_exposure
from app.core.atlas.tools_v2.portfolio.classification import portfolio_classification

# --- macro ---
from app.core.atlas.tools_v2.macro.commodity_prices import commodity_prices
from app.core.atlas.tools_v2.macro.us_rates import us_treasury_rates
from app.core.atlas.tools_v2.macro.indicators import macro_indicators

# --- alpaca ---
from app.core.atlas.tools_v2.alpaca.account import account_info, account_activities
from app.core.atlas.tools_v2.alpaca.portfolio import (
    get_position, get_positions, close_position, get_portfolio_history,
)
from app.core.atlas.tools_v2.alpaca.trade import (
    submit_trade, get_orders, cancel_order, cancel_all_orders, get_asset,
)


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
    # info (6)
    get_ticker_info, get_etf_info, get_ticker_peers, get_stock_ratings,
    get_institutional_holders, get_product_segmentation,
    # screener (2)
    equity_screener, etf_screener,
    # research (7)
    credit_research_search, earnings_call_search, economics_research_search,
    general_news, macro_research, tax_research_search, user_upload_search,
    # portfolio (6)
    portfolio_allocator, portfolio_performance, portfolio_risk, portfolio_stress_test,
    portfolio_factor_exposure, portfolio_classification,
    # macro (3)
    commodity_prices, us_treasury_rates, macro_indicators,
    # alpaca (11)
    account_info, account_activities, get_position, get_positions,
    close_position, get_portfolio_history, submit_trade, get_orders,
    cancel_order, cancel_all_orders, get_asset,
]

AVAILABLE_TOOLS: Dict[str, Dict[str, Any]] = {
    func.tool["name"]: func.tool for func in _ALL_TOOL_FUNCTIONS
}


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
    from app.core.atlas.tools_v2.worker_agent.worker import deploy_worker_agent

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
