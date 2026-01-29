# Common Tool Implementation Patterns

Reusable patterns for building agent tools in ProphitAI.

## Pattern 1: Simple Data Retrieval Tool

Tools that fetch and return data without complex processing.

```python
"""Fetch ticker information tool."""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
from typing import Optional


def get_ticker_info(ticker: str, _simulation_date: str = None) -> str:
    """
    Get basic information about a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        _simulation_date: Injected by agent framework

    Returns:
        str: YAML-formatted ticker information
    """
    v = ToolValidator()
    v.require_string('ticker', ticker)

    if not v.is_valid():
        return v.error_response()

    ticker = v.get('ticker').upper()

    try:
        # Fetch data from service/repository
        info = fetch_ticker_info_from_db(ticker)

        if not info:
            return error_response(f"Ticker not found: {ticker}")

        return success_response({
            "ticker": ticker,
            "company_name": info.get("name"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("market_cap")
        })
    except Exception as e:
        return error_response(f"Error fetching ticker info: {str(e)}")


# Schema constants
GET_TICKER_INFO_DESCRIPTION = (
    "Get basic information about a stock including company name, sector, industry, and market cap. "
    "Example: get_ticker_info(ticker='AAPL')"
)

GET_TICKER_INFO_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT')"
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_TICKER_INFO_TOOL = {
    "name": "get_ticker_info",
    "description": GET_TICKER_INFO_DESCRIPTION,
    "parameters": GET_TICKER_INFO_PARAMETERS,
    "function": get_ticker_info,
}
```

## Pattern 2: Portfolio Analysis Tool

Tools that operate on portfolio dictionaries.

```python
"""Portfolio concentration analysis tool."""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from app.core.atlas.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.utils.tool_validator import ToolValidator
from app.models.portfolio_models import PortfolioInput
from typing import Dict, Any, Optional


def portfolio_concentration(
    portfolio_dict: PortfolioInput | dict = None,
    _simulation_date: str = None
) -> str:
    """
    Analyze concentration risk in a portfolio.

    Args:
        portfolio_dict: Portfolio with ticker keys and allocation/position values
        _simulation_date: Injected by agent framework

    Returns:
        str: YAML-formatted concentration metrics
    """
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    portfolio_dict = v.get('portfolio_dict')

    try:
        # Calculate concentration metrics
        allocations = [h["allocation"] for h in portfolio_dict.values()]
        top_5 = sum(sorted(allocations, reverse=True)[:5])
        hhi = sum(a**2 for a in allocations)  # Herfindahl-Hirschman Index

        return success_response({
            "num_holdings": len(portfolio_dict),
            "top_5_concentration": round(top_5, 4),
            "hhi_index": round(hhi, 4),
            "effective_positions": round(1 / hhi, 2) if hhi > 0 else 0,
            "largest_position": max(allocations),
            "smallest_position": min(allocations)
        })
    except Exception as e:
        return error_response(f"Error calculating concentration: {str(e)}")


# Schema constants
CONCENTRATION_DESCRIPTION = (
    "Analyze concentration risk in a portfolio. Returns number of holdings, "
    "top-5 concentration, HHI index, and effective number of positions. "
    "CRITICAL: You MUST include portfolio_dict with ALL holdings. "
    "Example: portfolio_concentration(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...})"
)

CONCENTRATION_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CONCENTRATION_TOOL = {
    "name": "portfolio_concentration",
    "description": CONCENTRATION_DESCRIPTION,
    "parameters": CONCENTRATION_PARAMETERS,
    "function": portfolio_concentration,
}
```

## Pattern 3: Calculation Tool with Multiple Outputs

Tools that perform calculations and return structured results.

```python
"""Risk metrics calculation tool."""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from app.core.atlas.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.utils.tool_validator import ToolValidator
from typing import Optional
import numpy as np


def calculate_risk_metrics(
    portfolio_dict: dict = None,
    lookback_days: int = 252,
    confidence_level: float = 0.95,
    _simulation_date: str = None
) -> str:
    """
    Calculate comprehensive risk metrics for a portfolio.

    Args:
        portfolio_dict: Portfolio holdings
        lookback_days: Historical window for calculations (default: 252 = 1 year)
        confidence_level: VaR confidence level (default: 0.95)
        _simulation_date: Injected by agent framework

    Returns:
        str: YAML-formatted risk metrics
    """
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.optional_int('lookback_days', lookback_days, min_val=30, max_val=756)
    v.optional_float('confidence_level', confidence_level, min_val=0.9, max_val=0.99)

    if not v.is_valid():
        return v.error_response()

    portfolio_dict = v.get('portfolio_dict')
    lookback_days = v.get('lookback_days', 252)
    confidence_level = v.get('confidence_level', 0.95)

    try:
        # Fetch returns data
        returns = fetch_portfolio_returns(portfolio_dict, lookback_days)

        # Calculate metrics
        volatility = np.std(returns) * np.sqrt(252)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        es = returns[returns <= var].mean()
        max_dd = calculate_max_drawdown(returns)

        return success_response({
            "volatility_annualized": round(volatility, 4),
            "var": {
                "confidence_level": confidence_level,
                "value": round(var, 4),
                "interpretation": f"{confidence_level*100}% chance daily loss won't exceed {abs(var)*100:.2f}%"
            },
            "expected_shortfall": round(es, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe_ratio": round(np.mean(returns) / np.std(returns) * np.sqrt(252), 2),
            "lookback_days": lookback_days
        })
    except Exception as e:
        return error_response(f"Error calculating risk metrics: {str(e)}")


# Schema constants
RISK_METRICS_DESCRIPTION = (
    "Calculate comprehensive risk metrics including volatility, VaR, Expected Shortfall, "
    "max drawdown, and Sharpe ratio. "
    "CRITICAL: You MUST include portfolio_dict with ALL holdings. "
    "Optional: lookback_days (default 252), confidence_level (default 0.95). "
    "Example: calculate_risk_metrics(portfolio_dict={...}, lookback_days=126)"
)

RISK_METRICS_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "lookback_days": {
            "type": "integer",
            "description": "Historical lookback period in trading days (default: 252)",
            "minimum": 30,
            "maximum": 756,
            "default": 252
        },
        "confidence_level": {
            "type": "number",
            "description": "Confidence level for VaR calculation (default: 0.95)",
            "minimum": 0.9,
            "maximum": 0.99,
            "default": 0.95
        }
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

RISK_METRICS_TOOL = {
    "name": "calculate_risk_metrics",
    "description": RISK_METRICS_DESCRIPTION,
    "parameters": RISK_METRICS_PARAMETERS,
    "function": calculate_risk_metrics,
}
```

## Pattern 4: Agent-Aware Tool (Wrapper Pattern)

Tools that need access to agent state, wrapped at registration time.

```python
"""Edit plan tool - requires access to agent.plan."""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from typing import Any, Callable


def edit_plan_impl(
    plan: Any,
    action: str,
    main_task: str = None,
    subtask: str = None,
    new_task: dict = None
) -> str:
    """
    Internal implementation of plan editing.

    Args:
        plan: The agent's current plan object
        action: Action to perform ('add_subtask', 'remove_subtask', 'reorder')
        main_task: Name of main task to modify
        subtask: Name of subtask (for remove operations)
        new_task: New subtask definition (for add operations)

    Returns:
        str: YAML-formatted result
    """
    if plan is None:
        return error_response("No plan available to edit")

    try:
        if action == "add_subtask":
            # Add subtask logic
            plan.add_subtask(main_task, new_task)
            return success_response({"message": f"Added subtask to {main_task}"})

        elif action == "remove_subtask":
            plan.remove_subtask(main_task, subtask)
            return success_response({"message": f"Removed {subtask} from {main_task}"})

        else:
            return error_response(f"Unknown action: {action}")

    except Exception as e:
        return error_response(f"Error editing plan: {str(e)}")


def create_edit_plan_wrapper(agent: Any) -> Callable:
    """Create a wrapper that captures agent reference."""
    def wrapper(action: str, main_task: str = None, subtask: str = None, new_task: dict = None, **kwargs) -> str:
        return edit_plan_impl(
            plan=agent.plan,
            action=action,
            main_task=main_task,
            subtask=subtask,
            new_task=new_task
        )
    return wrapper


# Schema constants
EDIT_PLAN_DESCRIPTION = (
    "Modify the current execution plan by adding or removing subtasks. "
    "Actions: 'add_subtask', 'remove_subtask'. "
    "Example: edit_plan(action='add_subtask', main_task='Research', new_task={'name': 'Check competitors'})"
)

EDIT_PLAN_PARAMETERS = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Action to perform",
            "enum": ["add_subtask", "remove_subtask", "reorder"]
        },
        "main_task": {
            "type": "string",
            "description": "Name of the main task to modify"
        },
        "subtask": {
            "type": "string",
            "description": "Name of subtask (for remove operations)"
        },
        "new_task": {
            "type": "object",
            "description": "New subtask definition (for add operations)",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    },
    "required": ["action"],
    "additionalProperties": False
}

# Note: TOOL dict not created here - wrapper created at registration time
# In base_tool_registry.py:
# agent.add_tool(
#     name="edit_plan",
#     description=EDIT_PLAN_DESCRIPTION,
#     parameters=EDIT_PLAN_PARAMETERS,
#     function=create_edit_plan_wrapper(agent),  # Wrapper captures agent
# )
```

## Pattern 5: Sub-Agent Tool

Tools that spawn another agent to handle complex tasks.

```python
"""Sector analyst sub-agent tool."""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from app.core.atlas.tool_lib.sub_agents.sector_analyst.agent import SectorAnalystAgent
from typing import Optional


def sector_analysis(
    sector: str,
    analysis_type: str = "overview",
    _simulation_date: str = None
) -> str:
    """
    Run sector analysis using specialized sub-agent.

    Args:
        sector: GICS sector name (e.g., 'Technology', 'Healthcare')
        analysis_type: Type of analysis ('overview', 'deep_dive', 'opportunities')
        _simulation_date: Injected by agent framework

    Returns:
        str: YAML-formatted analysis results
    """
    try:
        # Create and run sub-agent
        analyst = SectorAnalystAgent(
            sector=sector,
            analysis_type=analysis_type,
            simulation_date=_simulation_date
        )

        result = analyst.run()

        if result.get("stop_reason") == "final_answer":
            return success_response({
                "sector": sector,
                "analysis_type": analysis_type,
                "analysis": result.get("final_answer"),
                "iterations": result.get("iterations"),
                "tokens_used": result.get("total_tokens")
            })
        else:
            return error_response(f"Analysis incomplete: {result.get('stop_reason')}")

    except Exception as e:
        return error_response(f"Error running sector analysis: {str(e)}")


# Schema constants
SECTOR_ANALYSIS_DESCRIPTION = (
    "Run comprehensive sector analysis using a specialized sub-agent. "
    "Provides sector overview, trends, key players, and opportunities. "
    "Analysis types: 'overview' (quick summary), 'deep_dive' (detailed), 'opportunities' (investment ideas). "
    "Example: sector_analysis(sector='Technology', analysis_type='deep_dive')"
)

SECTOR_ANALYSIS_PARAMETERS = {
    "type": "object",
    "properties": {
        "sector": {
            "type": "string",
            "description": "GICS sector name",
            "enum": [
                "Technology", "Healthcare", "Financials", "Consumer Discretionary",
                "Consumer Staples", "Industrials", "Energy", "Materials",
                "Real Estate", "Utilities", "Communication Services"
            ]
        },
        "analysis_type": {
            "type": "string",
            "description": "Depth of analysis",
            "enum": ["overview", "deep_dive", "opportunities"],
            "default": "overview"
        }
    },
    "required": ["sector"],
    "additionalProperties": False
}

SECTOR_ANALYSIS_TOOL = {
    "name": "sector_analysis",
    "description": SECTOR_ANALYSIS_DESCRIPTION,
    "parameters": SECTOR_ANALYSIS_PARAMETERS,
    "function": sector_analysis,
}
```

## Pattern 6: Batch Processing Tool

Tools that handle multiple items efficiently.

```python
"""Batch ticker data retrieval tool."""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


def batch_ticker_data(
    tickers: List[str],
    data_types: List[str] = None,
    _simulation_date: str = None
) -> str:
    """
    Retrieve data for multiple tickers in parallel.

    Args:
        tickers: List of ticker symbols
        data_types: Types of data to fetch (default: ['price', 'fundamentals'])
        _simulation_date: Injected by agent framework

    Returns:
        str: YAML-formatted batch results
    """
    v = ToolValidator()
    v.require_list('tickers', tickers, min_length=1, max_length=50)

    if not v.is_valid():
        return v.error_response()

    tickers = [t.upper() for t in v.get('tickers')]
    data_types = data_types or ['price', 'fundamentals']

    try:
        results = {}
        errors = []

        # Parallel fetch
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(fetch_single_ticker, ticker, data_types): ticker
                for ticker in tickers
            }

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    errors.append({"ticker": ticker, "error": str(e)})

        return success_response({
            "successful": len(results),
            "failed": len(errors),
            "data": results,
            "errors": errors if errors else None
        })

    except Exception as e:
        return error_response(f"Error in batch processing: {str(e)}")


# Schema constants
BATCH_TICKER_DESCRIPTION = (
    "Fetch data for multiple tickers in parallel. Efficient for bulk operations. "
    "Returns consolidated results with any errors noted. "
    "Max 50 tickers per call. "
    "Example: batch_ticker_data(tickers=['AAPL', 'MSFT', 'GOOGL'])"
)

BATCH_TICKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of ticker symbols",
            "minItems": 1,
            "maxItems": 50
        },
        "data_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["price", "fundamentals", "news", "ratings"]
            },
            "description": "Types of data to retrieve",
            "default": ["price", "fundamentals"]
        }
    },
    "required": ["tickers"],
    "additionalProperties": False
}

BATCH_TICKER_TOOL = {
    "name": "batch_ticker_data",
    "description": BATCH_TICKER_DESCRIPTION,
    "parameters": BATCH_TICKER_PARAMETERS,
    "function": batch_ticker_data,
}
```
