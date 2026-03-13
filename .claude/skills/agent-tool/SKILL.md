---
name: agent-tool
description: Build agent tool schemas and tool functions for the ProphitAI agentic framework. Use when creating new tools for agents, defining tool schemas, or building tool registries. Covers the @agent_tool decorator, Param/Schema metadata, and tool patterns.
---

## Overview

Build tools for the ProphitAI agentic framework using the `@agent_tool` decorator. The decorator auto-generates OpenAI function-calling schemas from function signatures, eliminating manual schema boilerplate.

## Quick Reference

```
Tool Location: app/core/atlas/tools/<category>/<tool_name>.py
Decorator: @agent_tool from app.core.atlas.tools.decorator
Response Format: YAML via success_response() / error_response()
Registration: agent.add_tool(**func.tool)
```

## Tool File Structure

Every tool file follows this structure:

```python
"""Tool description in docstring."""

from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.responses import success_response, error_response
from typing import Annotated, Optional

# ================================
# --> Helper funcs
# ================================


# ================================
# --> Tools
# ================================

@agent_tool(name="tool_name")
def tool_name(
    param1: str,
    param2: Annotated[int, Param(min_val=1, max_val=100)] = 10,
) -> str:
    """
    Brief description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        YAML-formatted result with success/data or error

    Examples:
        tool_name(param1="value", param2=10)
        >>> {"success": True, "data": {...}}

    Raises:
        ValueError: If param1 is invalid
    """
    try:
        result = perform_operation(param1, param2)
        return success_response(result)
    except Exception as e:
        return error_response(f"Error in tool_name: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(tool_name(param1="test_value", param2=5))
```

## The @agent_tool Decorator

The decorator introspects the function signature, type hints, and docstring to auto-generate the tool schema dict. No more manual `DESCRIPTION`, `PARAMETERS`, or `TOOL` constants.

### How It Works

1. **Reads type hints** to determine JSON Schema types
2. **Parses the docstring** for tool description and parameter descriptions
3. **Extracts `Param`/`Schema` metadata** from `Annotated` types for constraints
4. **Hides `_`-prefixed params** from the schema
5. **Attaches a `.tool` dict** to the function for registration

### Decorator Usage

```python
# Simple — name = function name, description = docstring
@agent_tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    ...

# Custom name
@agent_tool(name="portfolio_vol_es")
def vol_es(portfolio_dict: dict) -> str:
    """Calculate portfolio VaR and ES."""
    ...
```

### Registration

```python
# Single tool
from app.core.atlas.tools.portfolio.vol_es import vol_es
agent.add_tool(**vol_es.tool)

# Registry function for related tools
def register_risk_tools(agent) -> None:
    """Register all risk analysis tools on the agent."""
    from app.core.atlas.tools.portfolio.vol_es import vol_es
    from app.core.atlas.tools.portfolio.stress_test import stress_test

    agent.add_tool(**vol_es.tool)
    agent.add_tool(**stress_test.tool)
```

## Parameter Constraints with Annotated

Use `typing.Annotated` with `Param` or `Schema` to add constraints beyond basic type hints.

### Param — Add Constraints to Individual Parameters

```python
from typing import Annotated
from app.core.atlas.tools.decorator import Param

# Enum constraint
activity_type: Annotated[str, Param(enum=['FILL', 'CSD', 'CSW', 'DIV', 'JNLC'])]

# Numeric range
lookback_days: Annotated[int, Param(min_val=30, max_val=756)] = 252

# Custom description (overrides docstring)
conf: Annotated[float, Param(description="Confidence level for VaR", min_val=0.5, max_val=0.999)] = 0.99
```

**Param fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `description` | `str \| None` | Override docstring description for this param |
| `min_val` | `float \| None` | JSON Schema `minimum` |
| `max_val` | `float \| None` | JSON Schema `maximum` |
| `enum` | `list[str] \| None` | JSON Schema `enum` (fixed choices) |

### Literal — Inline Enum via Type Hints

```python
from typing import Literal

method: Literal['param', 'hist'] = 'param'
# Generates: {"type": "string", "enum": ["param", "hist"], "default": "param"}
```

## Type Resolution

The decorator maps Python types to JSON Schema:

| Python Type | JSON Schema | Notes |
|-------------|-------------|-------|
| `str` | `"string"` | |
| `int` | `"integer"` | |
| `float` | `"number"` | |
| `bool` | `"boolean"` | |
| `dict` | `"object"` | Use `Schema()` for complex objects |
| `list` | `"array"` | |
| `List[str]` | `"array"` + `items: {type: string}` | |
| `Optional[T]` | Unwraps to `T`, not in `required` | |
| `Literal['a','b']` | `"string"` + `enum: ["a","b"]` | |
| `Annotated[T, Param(...)]` | Base type `T` + constraints | |
| `Annotated[T, Schema({...})]` | Uses pre-built schema dict | |

### Required vs Optional

- **Required**: Parameters with no default value → added to `required` list
- **Optional**: Parameters with a default value → not in `required`, default recorded in schema
- **Hidden**: Parameters prefixed with `_` → excluded from schema entirely

## Docstring Rules

The decorator parses Google-style docstrings. The `Args` section is stripped from the tool description (used only for param descriptions). All other sections (`Returns`, `Examples`, `Raises`) are kept in the description so the LLM sees them.

```python
@agent_tool(name="my_tool")
def my_tool(ticker: str, lookback: int = 252) -> str:
    """
    Brief one-line summary of the tool.

    More detailed explanation if needed. This text plus Returns/Examples/Raises
    becomes the tool description the LLM sees.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        lookback: Historical lookback period in trading days

    Returns:
        Dict with volatility, VaR, and ES metrics

    Examples:
        my_tool(ticker="AAPL", lookback=126)
        >>> {"success": True, "data": {"vol": 0.25}}

    Raises:
        ValueError: If ticker is invalid
    """
```

## Response Formatting

```python
from app.core.atlas.tools.responses import success_response, error_response

# Success
return success_response({
    "result": calculated_value,
    "metrics": {"metric1": 0.5, "metric2": 0.3},
})

# Error
return error_response("Invalid ticker symbol: XYZ123")

# Error with exception
except Exception as e:
    return error_response(f"Error calculating metrics: {str(e)}")
```

## Portfolio Parameters

Portfolio tools always use `tickers: list[str]` and `weights: list[float]` (decimal percentages, e.g. 0.30 = 30%):

```python
@agent_tool(name="portfolio_risk")
def portfolio_risk(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=10)] = 1,
) -> str:
    """Calculate portfolio risk metrics."""
    ...
```

| Method | Purpose | Parameters |
|--------|---------|------------|
| `require_ticker` | Single ticker symbol | `name, value` |
| `require_tickers` | List of ticker symbols | `name, value` |
| `require_portfolio` | Portfolio dict | `name, value, normalize=True` |
| `require_enum` | Fixed choices | `name, value, allowed` |
| `require_numeric` | Number with range | `name, value, min_val, max_val, positive_only` |
| `optional_numeric` | Optional number with default | `name, value, default, min_val, max_val` |
| `optional_enum` | Optional enum with default | `name, value, allowed, default` |

## Tool Categories

| Category | Path | Purpose |
|----------|------|---------|
| `base/` | Core utilities | Calculator, think, finalize |
| `data/` | Market data | Prices, fundamentals, news, screeners |
| `portfolio/` | Portfolio analysis | Returns, concentration, beta, performance |
| `risk/` | Risk metrics | VaR, stress tests, drawdowns, correlations |
| `ticker/` | Single-ticker analysis | Performance, factors, technicals |
| `macro/` | Macro data | Rates, commodities, indicators |
| `foundry/` | Research tools | Credit research, macro research |

## Registering in the Tool Registry

After creating a tool in `app/core/atlas/tools/`, you **must** register it in the centralized tool registry so both the ChatAgent and WorkerAgent can discover it.

**File:** `app/core/atlas/tools/registry.py`

### Steps

1. **Add the import** in the appropriate `# --> Imports: <category>` section at the top of the file:

```python
# ================================
# --> Imports: portfolio
# ================================
from app.core.atlas.tools.portfolio.performance import portfolio_performance
from app.core.atlas.tools.portfolio.risk import portfolio_risk
from app.core.atlas.tools.portfolio.my_new_tool import my_new_tool  # <-- add here
```

2. **Add the function** to the matching category list in `TOOL_REGISTRY`:

```python
TOOL_REGISTRY: Dict[str, List[Callable]] = {
    # ...
    "portfolio": [
        portfolio_performance, portfolio_risk, portfolio_stress_test,
        portfolio_factor_exposure, portfolio_classification, portfolio_covariance,
        portfolio_correlation, get_user_simulated_portfolio, get_watchlist,
        my_new_tool,  # <-- add here
    ],
    # ...
}
```

3. If the tool belongs to a **new category** that doesn't exist yet, create a new import block and add a new key to `TOOL_REGISTRY`:

```python
# ================================
# --> Imports: my_new_category
# ================================
from app.core.atlas.tools.my_new_category.my_tool import my_tool

# Then in TOOL_REGISTRY:
"my_new_category": [
    my_tool,
],
```

### How It Works

- `TOOL_REGISTRY` is the single source of truth: `category_name -> list of @agent_tool-decorated functions`.
- `ALL_TOOLS` is derived automatically: `{func.tool["name"]: func.tool for func in all registry functions}`.
- **ChatAgent** uses `ALL_TOOLS` via `register_tools` — the LLM dynamically loads tools by category or name.
- **WorkerAgent** uses `ALL_TOOLS` minus `CHAT_ONLY_TOOLS` via `setup.py` — no separate registration needed.
- `build_catalogue_description()` auto-generates the prompt catalogue from the registry.
- No other registration step is needed — adding the function to `TOOL_REGISTRY` is sufficient.

### CHAT_ONLY_TOOLS

If your new tool involves real money / trade execution and must never be delegated to a worker agent, add it to the `CHAT_ONLY_TOOLS` set in `registry.py`:

```python
CHAT_ONLY_TOOLS: Set[str] = {
    "propose_trade",
    "propose_options_trade",
    "propose_multi_leg_options_trade",
    "close_position",
    "cancel_order",
    "my_new_trade_tool",  # <-- add here if applicable
}
```

## Best Practices

**DO:**
- Use `@agent_tool(name="...")` on every tool function
- Use `success_response()` / `error_response()` for all returns
- Write detailed docstrings with Args, Returns, Examples, and Raises sections
- Use `Annotated[T, Param(...)]` for enum/range constraints
- Use `Annotated[T, Schema({...})]` for complex pre-built schemas (portfolio_dict)
- Use `Literal['a', 'b']` for simple enum choices
- Prefix internal params with `_` to hide them from schemas
- Include `if __name__ == "__main__"` testing block
- Register via `agent.add_tool(**func.tool)`

**DON'T:**
- Manually define `TOOL_NAME_DESCRIPTION`, `TOOL_NAME_PARAMETERS`, or `TOOL_NAME_TOOL` constants
- Return raw dicts/strings (always use response functions)
- Hardcode data that should be fetched
- Catch and swallow exceptions silently
- Create tools with overlapping functionality
- Skip input validation for complex types like portfolio dicts

## Reference Files

- `references/param-examples.md` - Annotated parameter constraint examples
- `references/tool-patterns.md` - Common tool implementation patterns
- `assets/templates/basic_tool.py` - Basic tool template
- `assets/templates/portfolio_tool.py` - Portfolio-aware tool template
