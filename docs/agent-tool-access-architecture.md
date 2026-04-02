# Agent Tool Access Architecture Proposal

## Goal

Build a clean long-term agent architecture where:

- the broad chat agent can use dynamic tool discovery and `register_tools`
- scoped agents use fixed tools without dynamic registry overhead
- workers receive an explicit allowed tool universe
- the runtime loop, planner flow, and tool handler stay shared

This proposal keeps one execution engine and one main runtime implementation while separating tool exposure policy from the run loop.

## Why Change The Current Design

Today the framework-level [Agent](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/agents/agent.py) mixes four concerns:

- execution/runtime behavior
- prompt construction
- dynamic tool registration
- worker tool resolution

That makes the current abstraction too broad. The same class is trying to act like:

- a generic chat agent with a massive catalogue
- a scoped specialist agent with a small fixed tool set
- an orchestrator that can deploy workers

The result is avoidable coupling:

- prompts assume `register_tools` exists
- worker deployment depends on the same catalogue wiring used for parent discovery
- scoped agents are forced through dynamic-registry setup even when they do not need it

## Design Principles

The architecture should follow these rules:

1. One runtime loop.
2. One tool handler.
3. One planning/orchestration flow.
4. Tool exposure should be configurable without changing execution behavior.
5. Dynamic discovery should exist only where it is actually useful.
6. Worker tool access should be explicit and independent from the parent's current registration state.

## Core Recommendation

Do not maintain two separate large agent implementations.

Instead:

- keep one runtime `Agent`
- add explicit construction paths for chat and scoped use cases
- internally model three tool sets:
  - `initial_tools`
  - `deferred_tools`
  - `worker_tools`

This gives you one shared run loop with two clean policies:

- `Agent.for_chat(...)`
- `Agent.for_scope(...)`

These are constructor presets, not separate execution systems.

## High-Level Model

### 1. Initial Tools

Tools registered on the parent agent at initialization.

Use for:

- calculators
- retrieval tools that should always be callable
- fixed tool sets for scoped agents

### 2. Deferred Tools

Tools that the parent agent may load later through `register_tools`.

Use only for chat-like agents with a large catalogue.

### 3. Worker Tools

Tools that may be delegated through `deploy_worker_agent`.

This set should not depend on which tools are currently registered on the parent.

That is the key simplification:

- parent registration state controls direct parent tool calling
- worker tool universe controls delegation

These should be related, but not conflated.

## Recommended API

### Tool Access Profile

Use a small profile object that describes tool exposure.

```python
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolAccessProfile:
    initial_tools: list[Callable]
    deferred_tools: list[Callable]
    worker_tools: list[Callable]
    include_register_tools: bool
    include_catalogue_in_prompt: bool
```

This is better than a bare boolean because it models the actual architecture:

- what is available now
- what is loadable later
- what may be delegated

## Recommended Agent Construction

### Public Constructors

```python
class Agent(AgentBase):
    @classmethod
    def for_chat(
        cls,
        *,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str = "default",
        system_prompt: str | None = None,
        initial_tools: list[Callable] | None = None,
        deferred_tools: list[Callable],
        worker_tools: list[Callable] | None = None,
        **kwargs,
    ) -> "Agent":
        profile = ToolAccessProfile(
            initial_tools=initial_tools or [],
            deferred_tools=deferred_tools,
            worker_tools=worker_tools or deferred_tools,
            include_register_tools=True,
            include_catalogue_in_prompt=True,
        )
        return cls(
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
            system_prompt=system_prompt,
            tool_access=profile,
            **kwargs,
        )

    @classmethod
    def for_scope(
        cls,
        *,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str = "default",
        system_prompt: str | None = None,
        tools: list[Callable],
        worker_tools: list[Callable] | None = None,
        **kwargs,
    ) -> "Agent":
        profile = ToolAccessProfile(
            initial_tools=tools,
            deferred_tools=[],
            worker_tools=worker_tools or tools,
            include_register_tools=False,
            include_catalogue_in_prompt=False,
        )
        return cls(
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
            system_prompt=system_prompt,
            tool_access=profile,
            **kwargs,
        )
```

This keeps one framework agent while making chat and scoped use explicit.

## Internal Agent Structure

The `Agent` class should store normalized internal metadata:

```python
class Agent(AgentBase):
    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str = "default",
        system_prompt: str | None = None,
        tool_access: ToolAccessProfile | None = None,
        **kwargs,
    ):
        super().__init__(
            provider=provider,
            model=model,
            session_id=session_id,
            **kwargs,
        )

        self.user_id = user_id
        self.notebook = Notebook()
        self.tool_access = tool_access or ToolAccessProfile(
            initial_tools=[],
            deferred_tools=[],
            worker_tools=[],
            include_register_tools=False,
            include_catalogue_in_prompt=False,
        )

        self.initial_tools = list(self.tool_access.initial_tools)
        self.deferred_tools = list(self.tool_access.deferred_tools)
        self.worker_tools = list(self.tool_access.worker_tools)
```

## Tool Metadata Normalization

Even scoped agents should still build internal metadata from their tools.

Important: a catalogue is not the same thing as dynamic registration.

For both chat and scoped agents, build:

- a map of deferred tools by name
- a map of worker tools by name
- optional grouped catalogue text for prompts

Suggested internal helpers:

```python
def _tool_map(tools: list[Callable]) -> dict[str, dict]:
    return {func.tool["name"]: func.tool for func in tools}


def _build_catalogue_text(tools: list[Callable]) -> str:
    if not tools:
        return ""
    return ToolCatalogue(tools).build_catalogue_description()
```

And inside `Agent.__init__`:

```python
self.deferred_catalogue = ToolCatalogue(self.deferred_tools) if self.deferred_tools else None
self.deferred_tool_registry = (
    self.deferred_catalogue.tool_registry if self.deferred_catalogue else {}
)
self.deferred_tool_map = (
    self.deferred_catalogue.all_tools if self.deferred_catalogue else {}
)
self.worker_tool_map = _tool_map(self.worker_tools)
```

This solves the worker issue cleanly:

- scoped agents do not need `register_tools`
- scoped agents still have `worker_tool_map`
- workers can be resolved without exposing a runtime discovery tool

## Prompt Strategy

This is critical.

The prompt must match the actual tool exposure model.

### Current Problem

Today the shared prompt builders hardcode dynamic registration instructions:

- [base.py](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/prompts/base.py)
- [chat.py](C:/Dev/ProphitAI/projects/api/src/prophitai_api/agents/prompts/chat.py)

That is wrong for scoped agents.

### Recommendation

Split prompt generation into two modes.

#### Dynamic Prompt

Used by chat agents.

Includes:

- description of `register_tools`
- deferred catalogue text
- instructions to register tools before use

#### Scoped Prompt

Used by scoped agents.

Includes:

- only the guidance relevant to the fixed tool set
- no mention of `register_tools`
- optional short strategy note about how to use the scoped tools

### Suggested Prompt Builder API

```python
def build_agent_system_prompt(
    *,
    prompt_mode: str,
    deferred_tool_catalogue: str = "",
    scoped_tool_guide: str = "",
) -> str:
    if prompt_mode == "dynamic":
        return build_dynamic_system_prompt(
            tool_catalogue=deferred_tool_catalogue,
        )
    return build_scoped_system_prompt(
        scoped_tool_guide=scoped_tool_guide,
    )
```

For scoped agents, the tool guide should be short and strategic, for example:

```text
Use `equity_screener` to generate candidates.
Use `ticker_factors` and `ticker_risk` to validate quality and downside.
Use `get_ticker_info` to confirm business model fit.
```

That is enough. The schemas already provide the detailed discovery surface.

## Registration Rules

### Shared Built-In Tools

These remain registered as framework defaults:

- `calculator`
- `think` where applicable

These can continue to live in [base.py](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/agents/base.py).

### Always-On Orchestration Tools

These should still be added where needed:

- `llm_web_search`
- `retrieve_notes`
- `deploy_worker_agent`
- `update_plan` during plan execution

### Dynamic-Only Tool

Only add `register_tools` when:

- `include_register_tools` is true
- `deferred_tools` is non-empty

Recommended check:

```python
if self.tool_access.include_register_tools and self.deferred_tool_map:
    self.add_tool(
        **build_register_tools_schema(
            self.deferred_tool_registry,
            self.deferred_tool_map,
        ),
        function=partial(
            register_tools_fn,
            self.deferred_tool_registry,
            self.deferred_tool_map,
            self,
        ),
    )
```

### Scoped Tool Registration

Scoped tools should be registered directly:

```python
for func in self.initial_tools:
    self.add_tool(**func.tool)
```

No catalogue text and no `register_tools` are required.

## Worker Tool Resolution

This is the main architectural rule:

`deploy_worker_agent` should resolve from `worker_tool_map`, not from the parent's currently registered tools.

That means:

- a chat agent may delegate tools it has not yet directly registered
- a scoped agent may delegate from its fixed allowed set
- worker permissions stay explicit

### Recommended Implementation

```python
self.add_tool(
    **build_deploy_worker_schema(self.worker_tool_map),
    function=lambda **kwargs: _resolve_and_deploy(
        self.worker_tool_map,
        self.notebook,
        self.chat_callback,
        self.user_id,
        **kwargs,
    ),
)
```

This is exactly why a `get_tool_catalogue` tool is unnecessary.

The model already sees the worker tool universe in the `deploy_worker_agent` schema enum.

## Direct Imports vs Global Registry

The global registry should stay, but its job should narrow.

Keep [registry.py](C:/Dev/ProphitAI/packages/tools/src/prophitai_tools/registry.py) for:

- broad chat assembly
- testing
- centralized inventory

Do not use it as the default import hub for specialized agents.

For scoped agents, import tools directly from their modules:

```python
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.ticker.factors import ticker_factors
from prophitai_tools.ticker.risk import ticker_risk
from prophitai_tools.ticker.info.description import get_ticker_info
```

Then define the scoped list locally:

```python
WATCHLIST_TOOLS = [
    equity_screener,
    ticker_factors,
    ticker_risk,
    get_ticker_info,
]
```

This avoids eagerly importing the entire global tool registry just to access four tools.

## Concrete Usage Examples

### Chat Agent

```python
from prophitai_atlas.agents import Agent
from prophitai_tools.registry import ALL_TOOL_FUNCTIONS


chat_agent = Agent.for_chat(
    provider="anthropic",
    model="claude-sonnet-4-6",
    user_id=user_id,
    deferred_tools=ALL_TOOL_FUNCTIONS,
)
```

Behavior:

- small initial tool set
- large deferred catalogue
- `register_tools` available
- `deploy_worker_agent` can delegate from the allowed worker universe

### Scoped Agent

```python
from prophitai_atlas.agents import Agent
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.risk import ticker_risk
from prophitai_tools.ticker.info.description import get_ticker_info


WATCHLIST_TOOLS = [
    equity_screener,
    ticker_performance,
    ticker_risk,
    get_ticker_info,
]

watchlist_agent = Agent.for_scope(
    provider="anthropic",
    model="claude-sonnet-4-6",
    tools=WATCHLIST_TOOLS,
)
```

Behavior:

- fixed tools registered immediately
- no `register_tools`
- no large catalogue prompt section
- workers can use `WATCHLIST_TOOLS` unless overridden

### Scoped Agent With Narrower Worker Access

```python
watchlist_agent = Agent.for_scope(
    provider="anthropic",
    model="claude-sonnet-4-6",
    tools=WATCHLIST_TOOLS,
    worker_tools=[
        equity_screener,
        ticker_performance,
        ticker_risk,
    ],
)
```

This is useful when the parent can use a tool directly but workers should not.

## File-Level Implementation Plan

### 1. Update `Agent`

File:

- [agent.py](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/agents/agent.py)

Changes:

- add `ToolAccessProfile`
- add `Agent.for_chat(...)`
- add `Agent.for_scope(...)`
- normalize `initial_tools`, `deferred_tools`, and `worker_tools`
- build internal deferred and worker maps
- only add `register_tools` when deferred tools exist
- always build `deploy_worker_agent` from `worker_tool_map`
- remove the assumption that `tools=` always means dynamic catalogue

### 2. Add Prompt Builders

Files:

- [base.py](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/prompts/base.py)
- [chat.py](C:/Dev/ProphitAI/projects/api/src/prophitai_api/agents/prompts/chat.py)

Changes:

- split dynamic and scoped prompt builders
- remove hard dependency on `register_tools` from scoped prompts
- keep catalogue text injection only for dynamic chat agents

### 3. Migrate Chat Session

File:

- [chat_session.py](C:/Dev/ProphitAI/projects/api/src/prophitai_api/services/sessions/chat_session.py)

Changes:

- replace direct `Agent(...)` construction with `Agent.for_chat(...)`
- keep `ALL_TOOL_FUNCTIONS` as the deferred tool universe
- keep prompt builder aligned with dynamic mode

### 4. Migrate Scoped Agents

Files:

- [watchlist.py](C:/Dev/ProphitAI/projects/api/src/prophitai_api/agents/watchlist.py)
- [portfolio_builder.py](C:/Dev/ProphitAI/projects/api/src/prophitai_api/agents/portfolio_builder.py)

Changes:

- use `Agent.for_scope(...)`
- remove `ToolCatalogue` prompt injection unless genuinely helpful
- optionally add a small scoped tool guide
- prefer direct module imports over importing through the global registry

### 5. Keep Worker Agent As-Is

File:

- [worker_agent.py](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/agents/worker_agent.py)

Minimal change expected:

- none, or almost none

Reason:

- the worker already accepts explicit tool defs
- the parent should continue resolving those before deployment

### 6. Keep `ToolCatalogue`

File:

- [catalogue.py](C:/Dev/ProphitAI/packages/atlas/src/prophitai_atlas/tools/catalogue.py)

Minimal change expected:

- none

Reason:

- it remains useful for dynamic prompt text and grouped metadata
- it should just stop being treated as synonymous with runtime registration

## Testing Plan

### Unit/Smoke Coverage To Add Or Update

1. Dynamic agent initialization
- `register_tools` exists
- deferred catalogue appears in prompt
- deferred tools are not registered initially

2. Scoped agent initialization
- scoped tools are registered initially
- `register_tools` does not exist
- prompt contains no dynamic registration instructions

3. Worker deployment from scoped agent
- `deploy_worker_agent` exposes only scoped `worker_tools`
- worker receives allowed tool defs correctly

4. Worker deployment from chat agent
- worker can receive tools from the deferred worker universe
- parent does not need to have directly registered them first

5. Prompt correctness
- dynamic prompt includes registration instructions
- scoped prompt does not

### Existing Tests Likely To Touch

- [test_agent.py](C:/Dev/ProphitAI/packages/atlas/tests/test_agent.py)
- [test_prompt_restructure.py](C:/Dev/ProphitAI/packages/atlas/tests/test_prompt_restructure.py)
- [test_agent.py](C:/Dev/ProphitAI/projects/api/tests/test_agent.py)
- tool tests that currently instruct the model to call `register_tools`

## Migration Strategy

### Phase 1: Introduce The New Construction Paths

Implement:

- `Agent.for_chat(...)`
- `Agent.for_scope(...)`

Do not remove existing `Agent(...)` behavior yet.

This keeps migration low risk.

### Phase 2: Migrate Real Call Sites

Move:

- chat session -> `for_chat`
- watchlist -> `for_scope`
- portfolio builder -> `for_scope`

### Phase 3: Clean Up Old Constructor Semantics

Once all call sites are migrated, simplify the base constructor semantics so they are no longer ambiguous.

At that point, the direct bare constructor can either:

- remain internal-only
- or become a thin low-level escape hatch

## Why This Is The Cleanest Long-Term Architecture

This design is strong because it matches the actual product reality:

- only chat really needs large-scale discovery
- scoped agents should stay explicit and stable
- workers need an explicit allowed tool universe
- prompt behavior should match actual tool behavior

It avoids the two main failure modes:

1. forcing all agents through dynamic registry machinery
2. duplicating the entire runtime into separate chat/scoped implementations

Instead it gives you:

- one runtime
- one planner flow
- one worker mechanism
- explicit tool exposure profiles

That is the right balance between framework cleanliness and implementation simplicity.

## Final Recommendation

Implement one shared `Agent` runtime with two construction paths:

- `Agent.for_chat(...)`
- `Agent.for_scope(...)`

Use a `ToolAccessProfile` internally with:

- `initial_tools`
- `deferred_tools`
- `worker_tools`

Treat dynamic discovery as a chat-only capability, not a universal agent behavior.

Treat worker delegation as a separate policy based on `worker_tools`, not on current parent registration state.

That is the cleanest long-term direction for this codebase.
