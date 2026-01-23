# JSON Schema Examples for Agent Tools

Complete examples of JSON Schema parameter definitions for OpenAI function calling format.

## Complete Schema Structures

### Minimal Schema

```python
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query"
        }
    },
    "required": ["query"],
    "additionalProperties": False
}
```

### Multiple Required Parameters

```python
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL')"
        },
        "start_date": {
            "type": "string",
            "description": "Start date in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date in YYYY-MM-DD format"
        }
    },
    "required": ["ticker", "start_date", "end_date"],
    "additionalProperties": False
}
```

### Mixed Required and Optional

```python
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of ticker symbols",
            "minItems": 1
        },
        "period": {
            "type": "string",
            "description": "Analysis period",
            "enum": ["1M", "3M", "6M", "1Y", "3Y", "5Y"],
            "default": "1Y"
        },
        "include_benchmark": {
            "type": "boolean",
            "description": "Include SPY benchmark comparison",
            "default": True
        }
    },
    "required": ["tickers"],
    "additionalProperties": False
}
```

## Real Tool Schema Examples

### Portfolio Dict Schema (Shared)

```python
# From app/core/agentic_framework/tool_lib/common/schemas.py
PORTFOLIO_DICT_SCHEMA = {
    "type": "object",
    "description": (
        "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
        "Complete portfolio with ALL holdings. "
        "Keys = ticker symbols (e.g., 'AAPL'). "
        "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
        "Example: {'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}}"
    ),
    "patternProperties": {
        "^[A-Z]{1,5}$": {
            "type": "object",
            "properties": {
                "allocation": {
                    "type": "number",
                    "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                    "minimum": 0,
                    "maximum": 1
                },
                "position": {
                    "type": "string",
                    "description": "Must be 'long' or 'short'",
                    "enum": ["long", "short"]
                }
            },
            "required": ["allocation", "position"],
            "additionalProperties": False
        }
    },
    "minProperties": 1,
    "additionalProperties": False
}
```

### Stress Test Schema

```python
STRESS_TEST_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}
```

### Screener Schema (Complex)

```python
EQUITY_SCREENER_PARAMETERS = {
    "type": "object",
    "properties": {
        "filters": {
            "type": "object",
            "description": "Filter criteria for screening",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "GICS sector name"
                },
                "industry": {
                    "type": "string",
                    "description": "GICS industry name"
                },
                "market_cap_min": {
                    "type": "number",
                    "description": "Minimum market cap in billions"
                },
                "market_cap_max": {
                    "type": "number",
                    "description": "Maximum market cap in billions"
                },
                "country": {
                    "type": "string",
                    "description": "Country code (e.g., 'US')"
                }
            }
        },
        "sort_by": {
            "type": "string",
            "description": "Field to sort results by",
            "enum": ["market_cap", "pe_ratio", "dividend_yield", "volume"]
        },
        "sort_order": {
            "type": "string",
            "description": "Sort direction",
            "enum": ["asc", "desc"],
            "default": "desc"
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results",
            "minimum": 1,
            "maximum": 100,
            "default": 25
        }
    },
    "required": [],
    "additionalProperties": False
}
```

### Web Search Schema

```python
LLM_WEB_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of search queries to execute",
            "minItems": 1,
            "maxItems": 5
        },
        "recency_filter": {
            "type": "string",
            "description": "Filter results by recency",
            "enum": ["hour", "day", "week", "month", "year"]
        },
        "reasoning_effort": {
            "type": "string",
            "description": "Depth of analysis",
            "enum": ["low", "medium", "high"]
        },
        "mode": {
            "type": "string",
            "description": "Search mode",
            "enum": ["regular-search", "deep-research"],
            "default": "regular-search"
        }
    },
    "required": ["queries"],
    "additionalProperties": False
}
```

### Task Update Schema

```python
UPDATE_TASKS_PARAMETERS = {
    "type": "object",
    "properties": {
        "main_task": {
            "type": "string",
            "description": "Name of the main task being updated"
        },
        "subtasks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of subtask names to update"
        },
        "status": {
            "type": "string",
            "description": "New status for the tasks",
            "enum": ["pending", "in_progress", "completed", "blocked"]
        },
        "work_summary": {
            "type": "string",
            "description": "Summary of work completed"
        }
    },
    "required": ["main_task"],
    "additionalProperties": False
}
```

## Type Reference

### String Variations

```python
# Basic string
{"type": "string", "description": "..."}

# String with enum
{"type": "string", "enum": ["option1", "option2"], "description": "..."}

# String with pattern (regex)
{"type": "string", "pattern": "^[A-Z]{1,5}$", "description": "Ticker symbol"}

# String with length constraints
{"type": "string", "minLength": 1, "maxLength": 100, "description": "..."}

# String with format
{"type": "string", "format": "date", "description": "Date in YYYY-MM-DD"}
{"type": "string", "format": "date-time", "description": "ISO 8601 datetime"}
{"type": "string", "format": "email", "description": "Email address"}
```

### Number Variations

```python
# Integer
{"type": "integer", "description": "..."}

# Integer with range
{"type": "integer", "minimum": 0, "maximum": 100, "description": "..."}

# Number (float)
{"type": "number", "description": "..."}

# Number with range
{"type": "number", "minimum": 0.0, "maximum": 1.0, "description": "Percentage as decimal"}

# Number with exclusive bounds
{"type": "number", "exclusiveMinimum": 0, "description": "Must be positive"}
```

### Array Variations

```python
# Array of strings
{"type": "array", "items": {"type": "string"}, "description": "..."}

# Array with length constraints
{
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
    "maxItems": 50,
    "description": "..."
}

# Array of objects
{
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"}
        },
        "required": ["name", "value"]
    },
    "description": "..."
}

# Array with unique items
{"type": "array", "items": {"type": "string"}, "uniqueItems": True}
```

### Object Variations

```python
# Simple object
{
    "type": "object",
    "properties": {
        "key1": {"type": "string"},
        "key2": {"type": "number"}
    },
    "required": ["key1"],
    "additionalProperties": False
}

# Object with pattern properties (dynamic keys)
{
    "type": "object",
    "patternProperties": {
        "^[A-Z]+$": {"type": "number"}
    },
    "additionalProperties": False
}

# Nested object
{
    "type": "object",
    "properties": {
        "config": {
            "type": "object",
            "properties": {
                "setting1": {"type": "boolean"},
                "setting2": {"type": "string"}
            }
        }
    }
}
```

### Nullable and Optional

```python
# Nullable value
{"type": ["string", "null"], "description": "Optional string value"}

# Default value
{"type": "string", "default": "default_value", "description": "..."}

# Optional in Python (not in required list)
# Just omit from the "required" array
```
