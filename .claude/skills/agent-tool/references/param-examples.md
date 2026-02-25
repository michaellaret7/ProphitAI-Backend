# Parameter Constraint Examples for @agent_tool

Examples of parameter definitions using `Annotated`, `Param`, `Schema`, and `Literal` with the `@agent_tool` decorator.

## Basic Parameters (No Constraints Needed)

```python
# String — required (no default)
def my_tool(ticker: str) -> str: ...

# String — optional with default
def my_tool(ticker: str = "AAPL") -> str: ...

# Integer with default
def my_tool(lookback_days: int = 252) -> str: ...

# Float with default
def my_tool(confidence: float = 0.95) -> str: ...

# Boolean with default
def my_tool(include_benchmark: bool = True) -> str: ...

# Optional (not required, default None)
def my_tool(ticker: Optional[str] = None) -> str: ...
```

## Enum Constraints

### Using Literal (simplest for inline enums)

```python
from typing import Literal

# Method selection
method: Literal['param', 'hist'] = 'param'
# Schema: {"type": "string", "enum": ["param", "hist"], "default": "param"}

# Period selection
period: Literal['daily', 'weekly', 'monthly'] = 'daily'

# Sort order
sort_order: Literal['asc', 'desc'] = 'desc'
```

### Using Param(enum=...) (when you need other constraints too)

```python
from typing import Annotated
from app.core.atlas.tools.decorator import Param

# Activity type filter
activity_type: Annotated[str, Param(enum=['FILL', 'CSD', 'CSW', 'DIV', 'JNLC'])]

# Sector selection
sector: Annotated[str, Param(enum=[
    'Technology', 'Healthcare', 'Financials', 'Consumer Discretionary',
    'Consumer Staples', 'Industrials', 'Energy', 'Materials',
    'Real Estate', 'Utilities', 'Communication Services'
])]
```

## Numeric Range Constraints

```python
from typing import Annotated
from app.core.atlas.tools.decorator import Param

# Integer with min/max
lookback_days: Annotated[int, Param(min_val=30, max_val=756)] = 252
# Schema: {"type": "integer", "minimum": 30, "maximum": 756, "default": 252}

# Float with min/max
confidence: Annotated[float, Param(min_val=0.5, max_val=0.999)] = 0.99

# Integer with only min
horizon_days: Annotated[int, Param(min_val=1)] = 1

# Integer with only max
limit: Annotated[int, Param(max_val=100)] = 25
```

## Custom Description Override

```python
from typing import Annotated
from app.core.atlas.tools.decorator import Param

# Override the docstring-derived description
conf: Annotated[float, Param(
    description="Confidence level for VaR/ES (0.9 to 0.999). Higher = more conservative.",
    min_val=0.5,
    max_val=0.999
)] = 0.99
```

## Array Parameters

```python
from typing import List

# List of strings (auto-detected)
tickers: List[str]
# Schema: {"type": "array", "items": {"type": "string"}}

# Optional list with default
tickers: List[str] = None
```

## Hidden Parameters

Parameters starting with `_` are excluded from the generated schema:

```python
@agent_tool(name="my_tool")
def my_tool(
    ticker: str,
    *,
    _internal_context: Optional[dict] = None,  # Hidden from LLM
) -> str:
    ...
```

## Complete Real-World Examples

### Simple Tool — Account Info

```python
@agent_tool(name="account_info")
def account_info(account_id: str) -> str:
    """
    Query the account information for the given account ID.

    Args:
        account_id: The ID of the account to get the account information for

    Returns:
        A dictionary containing the account information

    Examples:
        account_info(account_id="d27aa8c2-5931-499b-bdfa-05c47b07ad70")
        >>> {"account_id": "...", "status": "ACTIVE", "cash": 10000}
    """
    ...
```

### Enum Tool — Account Activities

```python
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
            - CSD: Cash deposits
            - CSW: Cash withdrawals
            - DIV: Dividend payments
            - JNLC: Journal entries (cash transfers)
    """
    ...
```

### Portfolio Tool — VaR/ES

```python
@agent_tool(name="portfolio_risk")
def portfolio_risk(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=10)] = 1,
    conf: Annotated[float, Param(min_val=0.5, max_val=0.999)] = 0.99,
) -> str:
    """
    Calculate portfolio volatility, Value at Risk (VaR), and Expected Shortfall (ES).

    Args:
        tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights matching tickers (e.g., [0.40, 0.35, 0.25])
        years_back: Historical lookback period in years
        conf: Confidence level

    Returns:
        VaR, ES, and annualized volatility metrics
    """
    ...
```

### Multi-Optional Tool — Submit Trade

```python
@agent_tool(name="submit_trade")
def submit_trade(
    account_id: str,
    symbol: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "day",
) -> str:
    """
    Submit a trade to the given account ID.

    Args:
        account_id: The account to trade in
        symbol: Ticker symbol to trade
        qty: Number of shares (mutually exclusive with notional)
        notional: Dollar amount to trade (mutually exclusive with qty)
        limit_price: Limit price for limit orders
        stop_price: Stop price for stop orders
        time_in_force: Order duration
    """
    ...
```
