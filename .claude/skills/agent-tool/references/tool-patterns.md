# Common Tool Implementation Patterns

Reusable patterns for building agent tools in ProphitAI using the `@agent_tool` decorator.

## Pattern 1: Simple Data Retrieval Tool

Tools that fetch and return data without complex processing.

```python
"""Fetch ticker information tool."""

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response


@agent_tool(name="get_ticker_info")
def get_ticker_info(ticker: str) -> str:
    """
    Get basic information about a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Dict with company_name, sector, industry, and market_cap

    Examples:
        get_ticker_info(ticker="AAPL")
        >>> {"success": True, "data": {"ticker": "AAPL", "company_name": "Apple Inc.", ...}}
    """
    ticker = ticker.upper()

    try:
        info = fetch_ticker_info_from_db(ticker)

        if not info:
            return error_response(f"Ticker not found: {ticker}")

        return success_response({
            "ticker": ticker,
            "company_name": info.get("name"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("market_cap"),
        })
    except Exception as e:
        return error_response(f"Error fetching ticker info: {str(e)}")
```

## Pattern 2: Portfolio Analysis Tool

Tools that operate on portfolio dictionaries with `Schema()` injection.

```python
"""Portfolio concentration analysis tool."""

from app.core.atlas.tools.decorator import agent_tool, Schema
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
from typing import Annotated, Optional


@agent_tool(name="portfolio_concentration")
def portfolio_concentration(
    portfolio_dict: Annotated[dict, Schema(PORTFOLIO_DICT_SCHEMA)],
    *,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Analyze concentration risk in a portfolio.

    Args:
        portfolio_dict: Portfolio with ticker keys and allocation/position values

    Returns:
        Dict with num_holdings, top_5_concentration, hhi_index, and effective_positions

    Examples:
        portfolio_concentration(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, ...})
        >>> {"success": True, "data": {"num_holdings": 5, "top_5_concentration": 1.0, ...}}
    """
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    portfolio_dict = v.get('portfolio_dict')

    try:
        allocations = [h["allocation"] for h in portfolio_dict.values()]
        top_5 = sum(sorted(allocations, reverse=True)[:5])
        hhi = sum(a**2 for a in allocations)

        return success_response({
            "num_holdings": len(portfolio_dict),
            "top_5_concentration": round(top_5, 4),
            "hhi_index": round(hhi, 4),
            "effective_positions": round(1 / hhi, 2) if hhi > 0 else 0,
            "largest_position": max(allocations),
            "smallest_position": min(allocations),
        })
    except Exception as e:
        return error_response(f"Error calculating concentration: {str(e)}")
```

## Pattern 3: Calculation Tool with Multiple Outputs

Tools with several optional parameters using `Param` and `Literal` constraints.

```python
"""Risk metrics calculation tool."""

from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
from typing import Annotated, Literal, Optional
import numpy as np


@agent_tool(name="calculate_risk_metrics")
def calculate_risk_metrics(
    portfolio_dict: Annotated[dict, Schema(PORTFOLIO_DICT_SCHEMA)],
    lookback_days: Annotated[int, Param(min_val=30, max_val=756)] = 252,
    confidence_level: Annotated[float, Param(min_val=0.9, max_val=0.99)] = 0.95,
    method: Literal['param', 'hist'] = 'param',
    *,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Calculate comprehensive risk metrics for a portfolio.

    Args:
        portfolio_dict: Portfolio holdings
        lookback_days: Historical window for calculations
        confidence_level: VaR confidence level
        method: Calculation method

    Returns:
        Dict with volatility_annualized, var, expected_shortfall, max_drawdown, sharpe_ratio

    Examples:
        calculate_risk_metrics(
            portfolio_dict={...},
            lookback_days=126,
            confidence_level=0.95,
            method='param'
        )
    """
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    portfolio_dict = v.get('portfolio_dict')

    try:
        returns = fetch_portfolio_returns(portfolio_dict, lookback_days)

        volatility = np.std(returns) * np.sqrt(252)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        es = returns[returns <= var].mean()
        max_dd = calculate_max_drawdown(returns)

        return success_response({
            "volatility_annualized": round(volatility, 4),
            "var": {
                "confidence_level": confidence_level,
                "value": round(var, 4),
            },
            "expected_shortfall": round(es, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe_ratio": round(np.mean(returns) / np.std(returns) * np.sqrt(252), 2),
            "lookback_days": lookback_days,
        })
    except Exception as e:
        return error_response(f"Error calculating risk metrics: {str(e)}")
```

## Pattern 4: Enum-Heavy Tool (Broker/API Integration)

Tools with constrained string parameters using `Param(enum=...)`.

```python
"""Account activities tool."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.brokers.alpaca_broker.broker import ProphitBroker
from typing import Annotated


@agent_tool(name="account_activities")
def account_activities(
    account_id: str,
    activity_type: Annotated[str, Param(enum=['FILL', 'CSD', 'CSW', 'DIV', 'JNLC'])],
) -> str:
    """
    Query the account activities for the given account ID.

    Args:
        account_id: The ID of the account
        activity_type: The type of activity to filter by. Options:
            - FILL: Order fills (buys/sells)
            - CSD: Cash deposits into the account
            - CSW: Cash withdrawals from the account
            - DIV: Dividend payments received
            - JNLC: Journal entries (cash transfers between accounts)

    Returns:
        A list of activity dicts with id, activity_type, date, qty, price, symbol, side, net_amount

    Examples:
        account_activities(account_id="d27aa8c2-...", activity_type="FILL")
        >>> [{"id": "...", "activity_type": "FILL", "qty": "10.0", "price": "80.22", ...}]

    Raises:
        Exception: If the account ID is invalid or activities cannot be retrieved
    """
    broker = ProphitBroker(sandbox=True)

    try:
        activities = broker.get_account_activities(account_id, activity_type)
        return success_response(activities)
    except Exception as e:
        return error_response(f"Failed to get account activities for {account_id}: {str(e)}")
```

## Pattern 5: Sub-Agent Tool

Tools that spawn another agent to handle complex tasks.

```python
"""Sector analyst sub-agent tool."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from typing import Annotated, Literal, Optional


@agent_tool(name="sector_analysis")
def sector_analysis(
    sector: Annotated[str, Param(enum=[
        'Technology', 'Healthcare', 'Financials', 'Consumer Discretionary',
        'Consumer Staples', 'Industrials', 'Energy', 'Materials',
        'Real Estate', 'Utilities', 'Communication Services'
    ])],
    analysis_type: Literal['overview', 'deep_dive', 'opportunities'] = 'overview',
    *,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Run sector analysis using specialized sub-agent.

    Args:
        sector: GICS sector name
        analysis_type: Depth of analysis

    Returns:
        Dict with sector, analysis_type, analysis text, iterations, and tokens_used

    Examples:
        sector_analysis(sector="Technology", analysis_type="deep_dive")
    """
    try:
        from app.core.atlas.tool_lib.sub_agents.sector_analyst.agent import SectorAnalystAgent

        analyst = SectorAnalystAgent(
            sector=sector,
            analysis_type=analysis_type,
            simulation_date=_simulation_date,
        )

        result = analyst.run()

        if result.get("stop_reason") == "final_answer":
            return success_response({
                "sector": sector,
                "analysis_type": analysis_type,
                "analysis": result.get("final_answer"),
                "iterations": result.get("iterations"),
                "tokens_used": result.get("total_tokens"),
            })
        else:
            return error_response(f"Analysis incomplete: {result.get('stop_reason')}")

    except Exception as e:
        return error_response(f"Error running sector analysis: {str(e)}")
```

## Pattern 6: Batch Processing Tool

Tools that handle multiple items efficiently.

```python
"""Batch ticker data retrieval tool."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from typing import Annotated, List, Literal, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


@agent_tool(name="batch_ticker_data")
def batch_ticker_data(
    tickers: List[str],
    data_types: Optional[List[str]] = None,
    *,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Retrieve data for multiple tickers in parallel.

    Args:
        tickers: List of ticker symbols (max 50)
        data_types: Types of data to fetch (default: ['price', 'fundamentals'])

    Returns:
        Dict with successful count, failed count, data by ticker, and errors list

    Examples:
        batch_ticker_data(tickers=["AAPL", "MSFT", "GOOGL"])
        >>> {"success": True, "data": {"successful": 3, "failed": 0, "data": {...}}}

    Raises:
        Exception: If batch processing fails entirely
    """
    tickers = [t.upper() for t in tickers]
    data_types = data_types or ['price', 'fundamentals']

    try:
        results = {}
        errors = []

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
            "errors": errors if errors else None,
        })

    except Exception as e:
        return error_response(f"Error in batch processing: {str(e)}")
```

## Pattern 7: Agent-Aware Tool (Wrapper Pattern)

Tools that need access to agent state. The wrapper captures the agent reference at registration time.

```python
"""Edit plan tool — requires access to agent.plan."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from typing import Annotated, Any, Callable, Literal, Optional


def create_edit_plan_tool(agent: Any) -> Callable:
    """Create an edit_plan tool function that captures the agent reference.

    Returns the decorated function with .tool already attached.
    """

    @agent_tool(name="edit_plan")
    def edit_plan(
        action: Literal['add_subtask', 'remove_subtask'],
        main_task: str,
        subtask: Optional[str] = None,
        new_task_name: Optional[str] = None,
        new_task_description: Optional[str] = None,
    ) -> str:
        """
        Modify the current execution plan by adding or removing subtasks.

        Args:
            action: Action to perform
            main_task: Name of the main task to modify
            subtask: Name of subtask (for remove operations)
            new_task_name: Name for new subtask (for add operations)
            new_task_description: Description for new subtask (for add operations)

        Examples:
            edit_plan(action="add_subtask", main_task="Research", new_task_name="Check competitors")
        """
        if agent.plan is None:
            return error_response("No plan available to edit")

        try:
            if action == "add_subtask":
                agent.plan.add_subtask(main_task, {
                    "name": new_task_name,
                    "description": new_task_description,
                })
                return success_response({"message": f"Added subtask to {main_task}"})
            elif action == "remove_subtask":
                agent.plan.remove_subtask(main_task, subtask)
                return success_response({"message": f"Removed {subtask} from {main_task}"})
            else:
                return error_response(f"Unknown action: {action}")
        except Exception as e:
            return error_response(f"Error editing plan: {str(e)}")

    return edit_plan


# Registration:
# edit_plan_fn = create_edit_plan_tool(agent)
# agent.add_tool(**edit_plan_fn.tool)
```
