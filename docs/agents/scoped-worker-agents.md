# Scoped Worker Agents — Phase 1 Complete, Phase 2 Handoff

## What Was Done (Phase 1)

We replaced the old worker deployment system where every worker received ALL_TOOL_FUNCTIONS (70+ tools) as deferred tools with a new scoped system. Research (LongFuncEval, Anthropic's own benchmarks) shows LLM tool selection accuracy degrades significantly with large tool sets — Opus 4 dropped from 74% to 49% accuracy.

### Old System (removed)
- One deploy tool: `deploy_worker_agent`
- Every worker got ALL_TOOL_FUNCTIONS as deferred tools
- Workers had `register_tools` meta-tool to lazy-load what they needed
- Full tool catalogue description (~70+ tools) appended to every worker's system prompt
- Workers wasted iterations calling `register_tools` before doing real work

### New System (Phase 1)
- Two deploy tools: `deploy_scoped_worker` and `deploy_general_worker`
- Workers get ONLY the tools they need, registered directly at init
- No deferred tools, no `register_tools`, no tool catalogue in the system prompt
- `WorkerSpec` dataclass defines scoped worker configurations (name, system_prompt, tools, max_iterations)
- No global registry — each workflow defines its own `dict[str, WorkerSpec]` and binds it via lambda

---

## Architecture

### File Structure

```
packages/atlas/src/prophitai_atlas/
  models/
    worker_spec.py          # WorkerSpec frozen dataclass
  agents/
    worker_agent.py         # WorkerAgent class (accepts direct tools + optional system_prompt)
  tools/base/worker_agent/
    deploy_scoped.py        # deploy_scoped_worker tool (schema + full execution)
    deploy_general.py       # deploy_general_worker tool (schema + full execution)
    resolve.py              # resolve_tools_by_name shared helper
    write_note.py           # write_note tool (unchanged)
```

### Two Deploy Tools

**`deploy_scoped_worker`** — for pre-defined specialist workers
- LLM passes: `worker_type`, `task`, `plan_task_id`, `context` (optional)
- Deploy function looks up `registry[worker_type]` → gets `WorkerSpec` (registry is pre-bound per workflow via lambda)
- Resolves `spec.tools` (frozenset of tool name strings) → actual callables via `resolve_tools_by_name`
- Creates WorkerAgent with `spec.system_prompt` and `spec.max_iterations`
- The parent agent has NO control over which tools the worker gets — it's locked in the spec

**`deploy_general_worker`** — for ad-hoc workers with explicit tools
- LLM passes: `task`, `tools` (array of tool name strings), `plan_task_id` (optional), `context` (optional)
- Deploy function resolves tool names → actual callables via `resolve_tools_by_name`
- Creates WorkerAgent with the default worker system prompt
- `GENERAL_WORKER_MAX_ITERATIONS = 100` (higher than scoped default of 30)

### Why Two Tools (Not One)

Structural enforcement. Scoped parent agents (architecture workflow, fund workflow) only get `deploy_scoped_worker` registered — they literally cannot deploy a general worker. The chat agent gets both. This prevents scoped agents from bypassing the preset tool/prompt configuration. We considered a single tool with `worker_type="general"` but rejected it because:
1. It's prompt enforcement dressed as structural enforcement
2. Nothing prevents a scoped agent from passing `worker_type="general"`
3. The LLM-facing interface is clearer with two distinct tools

### WorkerAgent Class

```python
class WorkerAgent(AgentBase):
    def __init__(
        self,
        task: str,
        notebook: Notebook,
        *,
        tools: Optional[List[Callable]] = None,      # registered directly at init
        system_prompt: Optional[str] = None,           # custom or falls back to default
        provider, model, max_iterations, print_mode, temperature, chat_callback, user_id
    ):
```

- `tools` — list of @agent_tool-decorated callables, registered via `self.add_tool(**func.tool)`
- `system_prompt` — if set, used with date appended. If None, falls back to `build_worker_system_prompt()`
- Built-in tools always present: `write_note`, `web_search`, `calculator`
- No deferred tools, no `register_tools`

### WorkerSpec Dataclass

```python
@dataclass(frozen=True)
class WorkerSpec:
    name: str                    # "equity_researcher"
    system_prompt: str           # custom prompt for this worker type
    tools: frozenset[str]        # tool names: {"ticker_performance", "ticker_risk"}
    max_iterations: int = 30
```

### Tool Resolution

`resolve_tools_by_name(tool_functions, tool_names)` in `resolve.py`:
- Builds name→callable lookup from `func.tool["name"]`
- Resolves each requested name
- Raises `ValueError` with available tool names if any name is missing
- Used by both deploy functions (DRY)

### How Deploy Tools Are Registered on Parent Agents

Currently hardcoded in `Agent.__init__` (agent.py lines 144-160) — **Phase 2 must move this out**.

Lambda is used (not partial) because `self.chat_callback` is set to `WebSocketChatCallback` AFTER `__init__` in `send_message_controller`. Partial would capture the stale `NoOpChatCallback`.

For scoped workers, the workflow binds its own registry dict:

```python
FUND_WORKERS = {"equity_researcher": WorkerSpec(...), "macro_analyst": WorkerSpec(...)}

agent.add_tool(
    **DEPLOY_SCOPED_WORKER_TOOL,
    function=lambda **kwargs: deploy_scoped_worker(
        notebook, callback, user_id, registry=FUND_WORKERS, **kwargs
    ),
)
```

For general workers, no registry needed:

```python
agent.add_tool(
    **DEPLOY_GENERAL_WORKER_TOOL,
    function=lambda **kwargs: deploy_general_worker(
        notebook, callback, user_id, **kwargs
    ),
)
```

**Phase 2 change needed**: Move deploy tool registration out of `Agent.__init__`. Different parent agents register different deploy tools with different registries.

---

## What Stays Unchanged

- `register_tools.py` — still used by the chat Agent's deferred tools pattern
- `catalogue.py` — still builds deferred tools description for the chat Agent
- `write_note.py` — unchanged, always registered on workers
- `prompts/worker.py` — default worker system prompt, used when no custom prompt is set

---

## Phase 2: Integration

Phase 2 is about wiring the deploy tools into parent agents and building the first custom WorkerSpecs.

### Key Decisions Already Made

1. **Deploy tools are NOT auto-registered on Agent.__init__** — the caller decides which deploy tools the agent gets. Move the `self.add_tool(DEPLOY_SCOPED_WORKER_TOOL, ...)` out of Agent.__init__ and into the code that creates each agent.

2. **Scoped parent agents** (architecture workflow, fund workflow) → only `deploy_scoped_worker` registered. Cannot deploy general workers.

3. **Chat agent** → both `deploy_scoped_worker` and `deploy_general_worker` registered.

4. **WorkerSpec definitions live where they're used** — not in Atlas. Each workflow defines its own `dict[str, WorkerSpec]` (e.g., `FUND_WORKERS` in `projects/fund/`) and binds it via lambda when registering the deploy tool. No global registry.

5. **Worker system prompts use XML tags** for top-level sections (project standard from CLAUDE.md).

### What Needs to Happen

1. **Move deploy tool registration out of `Agent.__init__`** — make it the caller's responsibility
2. **Build first WorkerSpecs** — define specs for an existing workflow (e.g., fund/architecture)
3. **Register specs into WORKER_REGISTRY** at the project level
4. **Update parent agent system prompts** to list available worker types
5. **Test end-to-end** — parent agent deploys a scoped worker, worker runs with correct tools and prompt

### Available Tool Categories for Building Specs

| Category | Tools |
|----------|-------|
| ticker_analytics | ticker_performance, ticker_risk, ticker_factors, ticker_technicals |
| ticker_info | get_ticker_info, get_etf_info, get_ticker_peers, get_institutional_holders, get_product_segmentation, get_etf_holdings, get_stock_ratings |
| fundamentals | get_ticker_fundamental_data, get_analyst_estimates, get_ratios_ttm, get_price_target_data |
| portfolio | portfolio_performance, portfolio_risk, portfolio_stress_test, portfolio_factor_exposure, portfolio_correlation, portfolio_classification, portfolio_covariance, get_user_simulated_portfolio, get_watchlist |
| portfolio_construction | portfolio_allocator |
| broker | account_info, propose_trade, propose_options_trade, propose_multi_leg_options_trade, get_order_impact, get_orders, cancel_order, get_quotes, get_positions, close_position |
| options | get_option_quote, get_option_contracts, get_option_price_history, get_option_expirations, get_options_chain |
| research | strategy_research, credit_research_search, macro_research_search, economics_research_search, theory_research, earnings_call_search, tax_research_search, user_upload_search |
| market | us_treasury_rates, commodity_prices, macro_indicators, get_press_releases, get_ticker_news, general_news |
| screener | etf_screener, equity_screener |
| institutional | get_fund_13f_holdings |
| sectors | get_sector_industries, get_group_tickers |

### Known Minor Code Smell

Both deploy functions (`deploy_scoped.py` and `deploy_general.py`) share ~15 lines of WorkerAgent instantiation boilerplate. If WorkerAgent's init signature changes, both files need updating. This is acceptable at 2 call sites — abstract only if it grows to 5+.

---

## Import Cheatsheet

```python
# Models
from prophitai_atlas.models import WorkerSpec

# Deploy tools (for registering on parent agents)
from prophitai_atlas.tools.base import (
    DEPLOY_SCOPED_WORKER_TOOL,
    deploy_scoped_worker,
    DEPLOY_GENERAL_WORKER_TOOL,
    deploy_general_worker,
)

# Direct WorkerAgent instantiation (for testing)
from prophitai_atlas.agents.worker_agent import WorkerAgent
from prophitai_atlas.models.notebook import Notebook

# Tool resolution (used internally by deploy functions)
from prophitai_atlas.tools.base.worker_agent.resolve import resolve_tools_by_name
```

### Defining a Per-Workflow Registry

```python
# projects/fund/src/prophitai_fund/workers.py
from prophitai_atlas.models import WorkerSpec

FUND_WORKERS: dict[str, WorkerSpec] = {
    "equity_researcher": WorkerSpec(
        name="equity_researcher",
        system_prompt="<role>You are a senior equity analyst...</role>",
        tools=frozenset({
            "ticker_performance", "ticker_risk", "ticker_factors",
            "get_ticker_info", "get_ticker_fundamental_data",
            "get_analyst_estimates", "earnings_call_search",
        }),
        max_iterations=30,
    ),
}
```

### Registering Deploy Tools on a Parent Agent

```python
# Scoped agent — only scoped workers, bound to workflow's registry
agent.add_tool(
    **DEPLOY_SCOPED_WORKER_TOOL,
    function=lambda **kwargs: deploy_scoped_worker(
        notebook, callback, user_id, registry=FUND_WORKERS, **kwargs
    ),
)

# Chat agent — both (no registry needed for general)
agent.add_tool(
    **DEPLOY_SCOPED_WORKER_TOOL,
    function=lambda **kwargs: deploy_scoped_worker(
        notebook, callback, user_id, registry=SHARED_WORKERS, **kwargs
    ),
)
agent.add_tool(
    **DEPLOY_GENERAL_WORKER_TOOL,
    function=lambda **kwargs: deploy_general_worker(
        notebook, callback, user_id, **kwargs
    ),
)
```
