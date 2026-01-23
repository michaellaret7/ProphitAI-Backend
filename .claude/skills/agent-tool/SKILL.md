---
name: agent-tool
description: Build agent tool schemas and tool functions for the ProphitAI agentic framework. Use when creating new tools for agents, defining tool schemas, or building tool registries. Covers OpenAI function calling format, parameter validation, and tool patterns.
---

## Overview

Build tools for the ProphitAI agentic framework following established patterns. Tools enable agents to perform actions via the ReAct pattern with native tool-calling.

## Quick Reference

```
Tool Location: app/core/agentic_framework/tool_lib/<category>/<tool_name>.py
Schema Format: OpenAI function calling (JSON Schema)
Response Format: YAML via success_response() / error_response()
```

## Tool File Structure

Every tool file follows this structure:

```python
"""Tool description in docstring."""

from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA  # If needed
from app.utils.tool_validator import ToolValidator  # For validation
from typing import Dict, Any, List, Optional

# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def tool_name(
    param1: str,
    param2: Optional[int] = None,
    _simulation_date: str = None  # Injected by agent framework
) -> str:
    """
    Brief description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2
        _simulation_date: Optional simulation date (injected by agent framework, not used by tool)

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Result data when successful
            - 'error' (str): Error message when unsuccessful
    """
    # Validate inputs
    v = ToolValidator()
    v.require_string('param1', param1)  # Validation

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    param1 = v.get('param1')

    try:
        # Core tool logic
        result = perform_operation(param1, param2)
        return success_response(result)
    except Exception as e:
        return error_response(f"Error in tool_name: {str(e)}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

TOOL_NAME_DESCRIPTION = (
    "Brief description for LLM. Explain what the tool does and when to use it. "
    "Include return value description. "
    "CRITICAL: Include any mandatory parameters with examples. "
    "Example: tool_name(param1='value', param2=10)"
)

TOOL_NAME_PARAMETERS = {
    "type": "object",
    "properties": {
        "param1": {
            "type": "string",
            "description": "Description of param1"
        },
        "param2": {
            "type": "integer",
            "description": "Description of param2",
            "default": 10
        }
    },
    "required": ["param1"],
    "additionalProperties": False
}

TOOL_NAME_TOOL = {
    "name": "tool_name",
    "description": TOOL_NAME_DESCRIPTION,
    "parameters": TOOL_NAME_PARAMETERS,
    "function": tool_name,
}


# ==============================================================================
# STANDALONE TESTING
# ==============================================================================

if __name__ == "__main__":
    # Test the tool directly
    print(tool_name(param1="test_value", param2=5))
```

## JSON Schema Parameter Types

### Basic Types

```python
# String parameter
"param_name": {
    "type": "string",
    "description": "What this parameter does"
}

# Integer parameter
"param_name": {
    "type": "integer",
    "description": "What this parameter does",
    "minimum": 0,
    "maximum": 100
}

# Number (float) parameter
"param_name": {
    "type": "number",
    "description": "Decimal value",
    "minimum": 0.0,
    "maximum": 1.0
}

# Boolean parameter
"param_name": {
    "type": "boolean",
    "description": "True/False flag"
}
```

### Enum (Fixed Choices)

```python
"period": {
    "type": "string",
    "description": "Time period for analysis",
    "enum": ["daily", "weekly", "monthly", "quarterly", "annual"]
}
```

### Array Parameters

```python
# Array of strings
"tickers": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of ticker symbols (e.g., ['AAPL', 'MSFT'])",
    "minItems": 1,
    "maxItems": 50
}

# Array of objects
"holdings": {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string"},
            "weight": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": ["ticker", "weight"]
    },
    "description": "Portfolio holdings with weights"
}
```

### Object Parameters

```python
# Simple object
"filters": {
    "type": "object",
    "properties": {
        "sector": {"type": "string"},
        "min_market_cap": {"type": "number"}
    },
    "description": "Filter criteria"
}

# Portfolio dict (use shared schema)
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA

"portfolio_dict": PORTFOLIO_DICT_SCHEMA  # Reuse standard schema
```

### Pattern Properties (Dynamic Keys)

```python
# For objects with ticker symbols as keys
"portfolio_dict": {
    "type": "object",
    "description": "Portfolio with ticker keys",
    "patternProperties": {
        "^[A-Z]{1,5}$": {  # Regex for ticker symbols
            "type": "object",
            "properties": {
                "allocation": {"type": "number", "minimum": 0, "maximum": 1},
                "position": {"type": "string", "enum": ["long", "short"]}
            },
            "required": ["allocation", "position"]
        }
    },
    "minProperties": 1,
    "additionalProperties": False
}
```

## Input Validation with ToolValidator

```python
from app.utils.tool_validator import ToolValidator

def my_tool(ticker, lookback_days=None, portfolio_dict=None, metric=None) -> str:
    v = ToolValidator()

    # Ticker validation (single ticker symbol)
    v.require_ticker('ticker', ticker)

    # Multiple tickers validation
    v.require_tickers('tickers', tickers)  # List of ticker symbols

    # Portfolio validation (normalizes and validates structure)
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    # Enum validation (fixed choices)
    v.require_enum('metric', metric, ['vol', 'var', 'sharpe'])

    # Numeric validation with range
    v.require_numeric('value', value, min_val=0, max_val=100, positive_only=True)

    # Optional numeric with default
    v.optional_numeric('lookback_days', lookback_days, default=252, min_val=30, max_val=756)

    # Optional enum with default
    v.optional_enum('period', period, ['daily', 'weekly', 'monthly'], default='daily')

    # Check validation
    if not v.is_valid():
        return v.error_response()  # Returns formatted error

    # Get validated/normalized values
    ticker = v.get('ticker')
    portfolio_dict = v.get('portfolio_dict')
    lookback_days = v.get('lookback_days')

    # Continue with tool logic...
```

### Available Validator Methods

| Method | Purpose | Parameters |
|--------|---------|------------|
| `require_ticker` | Single ticker symbol | `name, value` |
| `require_tickers` | List of ticker symbols | `name, value` |
| `require_portfolio` | Portfolio dict | `name, value, normalize=True` |
| `require_enum` | Fixed choices | `name, value, allowed` |
| `require_numeric` | Number with range | `name, value, min_val, max_val, positive_only` |
| `optional_numeric` | Optional number with default | `name, value, default, min_val, max_val` |
| `optional_enum` | Optional enum with default | `name, value, allowed, default` |

## Response Formatting

```python
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

# Success response
return success_response({
    "result": calculated_value,
    "metrics": {"metric1": 0.5, "metric2": 0.3},
    "summary": "Analysis complete"
})
# Output: YAML with success: true, data: {...}

# Error response
return error_response("Invalid ticker symbol: XYZ123")
# Output: YAML with success: false, error: "..."

# Error with exception
except Exception as e:
    return error_response(f"Error calculating metrics: {str(e)}")
```

## Tool Categories

| Category | Path | Purpose |
|----------|------|---------|
| `base_tools/` | Core utilities | Calculator, notes, search, finalize |
| `data_tools/` | Market data | Prices, fundamentals, news, screeners |
| `portfolio_tools/` | Portfolio analysis | Returns, concentration, beta, performance |
| `risk_tools/` | Risk metrics | VaR, stress tests, drawdowns, correlations |
| `ticker_tools/` | Single-ticker analysis | Performance, factors, technicals |
| `macro_tools/` | Macro data | Rates, commodities, indicators |
| `agent_specific_tools/` | Specialized | CIO, CRO, optimizer-specific tools |
| `sub_agents/` | Agent-as-tool | Sector analyst, ticker analyst |

## Registering Tools with Agents

### Method 1: Direct Registration

```python
# In agent setup code
from app.core.agentic_framework.tool_lib.risk_tools.stress_test import (
    stress_test,
    STRESS_TEST_DESCRIPTION,
    STRESS_TEST_PARAMETERS
)

agent.add_tool(
    name="portfolio_stress_test",
    description=STRESS_TEST_DESCRIPTION,
    parameters=STRESS_TEST_PARAMETERS,
    function=stress_test
)
```

### Method 2: Tool Dict Pattern

```python
# In tool file
STRESS_TEST_TOOL = {
    "name": "portfolio_stress_test",
    "description": STRESS_TEST_DESCRIPTION,
    "parameters": STRESS_TEST_PARAMETERS,
    "function": stress_test,
}

# In agent setup
from app.core.agentic_framework.tool_lib.risk_tools.stress_test import STRESS_TEST_TOOL

agent.add_tool(**STRESS_TEST_TOOL)
```

### Method 3: Registry Function

```python
# Create a registry function for related tools
def register_risk_tools(agent) -> None:
    """Register all risk analysis tools on the agent."""

    agent.add_tool(
        name="portfolio_stress_test",
        description=STRESS_TEST_DESCRIPTION,
        parameters=STRESS_TEST_PARAMETERS,
        function=stress_test
    )

    agent.add_tool(
        name="var_analysis",
        description=VAR_DESCRIPTION,
        parameters=VAR_PARAMETERS,
        function=var_analysis
    )

# In agent initialization
register_risk_tools(agent)
```

## Best Practices

**DO:**
- Use `success_response()` / `error_response()` for all returns
- Validate inputs with `ToolValidator`
- Include `_simulation_date` parameter for time-sensitive tools
- Import shared schemas from `common/schemas.py`
- Write descriptive tool descriptions with examples
- Include standalone `if __name__ == "__main__"` testing
- Mark required parameters in schema
- Use `additionalProperties: False` to prevent extra params

**DON'T:**
- Return raw dicts/strings (always use response functions)
- Hardcode data that should be fetched
- Catch and swallow exceptions silently
- Use mutable default arguments
- Create tools with overlapping functionality
- Skip input validation

## Reference Files

- `references/schema-examples.md` - Complete JSON schema examples
- `references/tool-patterns.md` - Common tool implementation patterns
- `assets/templates/basic_tool.py` - Basic tool template
- `assets/templates/portfolio_tool.py` - Portfolio-aware tool template
