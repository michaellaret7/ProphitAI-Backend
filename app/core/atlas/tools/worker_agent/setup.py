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
from app.core.atlas.tools.portfolio.covariance import portfolio_covariance
from app.core.atlas.tools.portfolio.correlation import portfolio_correlation
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
from app.core.atlas.tools.broker.orders import (
    get_order_impact, get_orders, cancel_order, get_quotes,
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
    # portfolio (9)
    portfolio_allocator, portfolio_performance, portfolio_risk, portfolio_stress_test,
    portfolio_factor_exposure, portfolio_classification, portfolio_covariance,
    portfolio_correlation, get_user_simulated_portfolio,
    # macro (3)
    commodity_prices, us_treasury_rates, macro_indicators,
    # watchlist (1)
    get_watchlist,
    # broker (8)
    account_info, get_positions, close_position,
    get_orders, cancel_order, get_quotes, get_order_impact,
    # options (5)
    get_option_expirations, get_option_contracts, get_options_chain,
    get_option_quote, get_option_price_history,
]

AVAILABLE_TOOLS: Dict[str, Dict[str, Any]] = {
    func.tool["name"]: func.tool for func in _ALL_TOOL_FUNCTIONS
}


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

DEPLOY_WORKER_DESCRIPTION = """
  Deploy a focused worker agent to autonomously execute a specific sub-task.
  The worker runs its own tool-calling loop with the tools you select and returns
  a structured result.

  **WHEN TO USE:**
  - Research tasks: earnings call analysis, news summarization, sector deep-dives
  - Data-heavy analysis that requires multiple sequential tool calls
  - Any focused sub-task that benefits from isolated execution

  **IMPORTANT:** Always pass the plan_task_id of the plan task you are working on.

  **MANDATORY PROMPT STRUCTURE:**
  The `task` string MUST contain ALL 5 of the following labeled sections.
  Do NOT omit any section. Do NOT reorder them.

  ── ROLE ──
  The worker's persona and expertise for this task.
  Specificity matters — "senior equity analyst covering consumer staples" beats
  "analyst". The more targeted the persona, the better the worker's output quality
  because it anchors the LLM's domain knowledge and tone.

  ── TASK ──
  What specifically the worker must accomplish.
  Include concrete inputs: tickers, dates, metrics, thresholds. If you already have
  data from prior steps or other workers, paste it directly here so the worker does
  not waste iterations re-fetching information you already possess.

  ── SUCCESS CRITERIA ──
  How the worker knows it is done. The worker continues until every criterion is met.
  Use measurable, checkable conditions (e.g., "at least 5 tickers analyzed",
  "all risk metrics computed", "output contains a table with columns X, Y, Z").
  Avoid vague criteria like "do a thorough job" — the worker cannot self-evaluate
  against ambiguity.

  ── RULES ──
  Constraints and guardrails the worker must follow.
  Scope limits, data source constraints, things to explicitly avoid, and any
  domain-specific guardrails (e.g., "only use TTM data", "exclude ETFs",
  "do not make forward-looking projections").

  ── OUTPUT FORMAT ──
  The exact structure and format of the final response.
  Be explicit about structure — specify sections, bullet lists, tables, JSON schema,
  or prose. The more precise the format specification, the more directly usable the
  worker's output will be in your next step without manual reformatting.

  **CONTEXT-PASSING:**
  Use the `context` parameter to pass results from prior workers or earlier tool
  calls. This data is automatically prepended to the worker's prompt under a
  CONTEXT label, keeping the 5-section task structure clean. For example, if a
  previous worker returned a list of tickers with scores, pass that as `context`
  instead of embedding it in the TASK section.

  **TOOL SELECTION:**
  Only equip tools the worker actually needs for this specific task. Over-provisioning
  dilutes the worker's focus and wastes its iteration budget on irrelevant options.
  A worker with 3 targeted tools outperforms one with 15 broad tools.

  **WRITE_NOTE BEHAVIOR:**
  When a worker calls `write_note`, those notes are saved to the orchestrator's
  shared notebook. You can read these notes to inform subsequent workers or your
  own final synthesis.

  **DO NOT:**
  - Send vague one-liner tasks with no structure — the worker will underperform.
  - Omit OUTPUT FORMAT — the worker will guess, and its output will be unusable.
  - Dump every available tool into the tools list — select only what is needed.
  - Repeat data-fetching work a prior worker already completed — use `context` to pass it.

  **EXAMPLE:**
  deploy_worker_agent(
    task=(
      "ROLE: You are a senior equity research analyst specializing in mega-cap tech.\\n\\n"
      "TASK: Research the latest AAPL earnings call. Extract key financial metrics, "
      "management forward guidance, and notable analyst Q&A exchanges.\\n\\n"
      "SUCCESS CRITERIA:\\n"
      "- Revenue, EPS, and gross margin figures for the reported quarter are included\\n"
      "- Management guidance for next quarter is summarized\\n"
      "- At least 3 notable analyst Q&A exchanges are captured\\n\\n"
      "RULES:\\n"
      "- Only use data from the most recent earnings call\\n"
      "- Do not speculate beyond what management explicitly stated\\n"
      "- Cite specific numbers, not vague qualitative language\\n\\n"
      "OUTPUT FORMAT:\\n"
      "Return a structured summary with sections: Financial Highlights, "
      "Forward Guidance, and Analyst Q&A (each Q&A as Question / Answer pairs)."
    ),
    context="Prior screening worker identified AAPL as a top pick with score 92/100. Current price: $187.50, P/E: 29.3x.",
    tools=['earnings_call_search', 'get_ticker_news'],
    plan_task_id='1'
  )
"""

DEPLOY_WORKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": (
                "The worker's full prompt. MUST include all 5 labeled sections: "
                "ROLE, TASK, SUCCESS CRITERIA, RULES, and OUTPUT FORMAT. "
                "If you have data from prior steps or other workers, embed it "
                "directly in the TASK section to avoid redundant fetching. "
                "See the tool description for the required structure and example."
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
        },
        "context": {
            "type": "string",
            "description": (
                "Optional data from prior steps or other workers to provide as background. "
                "This is prepended to the task prompt so the worker has it without re-fetching. "
                "Use this for passing raw data (ticker lists, scores, tables) instead of "
                "stuffing it into the TASK section."
            )
        }
    },
    "required": ["task", "tools", "plan_task_id"],
    "additionalProperties": False
}

# Reason: WorkerAgent auto-registers these via AgentBase and its own __init__,
# so the orchestrator may redundantly request them. Skip silently.
_WORKER_DEFAULT_TOOLS = {"think", "calculator", "llm_web_search", "write_note"}


def _resolve_and_deploy(
    notebook: Notebook, 
    chat_callback: Any,
    task: str, 
    tools: List[str], 
    plan_task_id: str = "", 
    context: str = "",
) -> str:
    """Resolve tool name strings to tool dicts, then deploy the worker agent.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via partial).
        task: Task description from the orchestrator LLM.
        tools: List of tool name strings from the orchestrator LLM.
        plan_task_id: The plan task ID this worker is deployed for.
        context: Optional data from prior steps to prepend to the task.
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

    # Reason: Prepend context with a label so the worker LLM can distinguish
    # background data from the structured 5-section task prompt.
    full_task = f"CONTEXT:\n{context}\n\n{task}" if context else task

    return deploy_worker_agent(
        notebook=notebook,
        chat_callback=chat_callback,
        task=full_task,
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
