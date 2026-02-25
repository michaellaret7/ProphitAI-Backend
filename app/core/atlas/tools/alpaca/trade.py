"""Alpaca trade submission tool for agent framework."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.brokers.alpaca_broker.broker import ProphitBroker
from typing import Annotated, Optional, Literal


# ================================
# --> Tools
# ================================

@agent_tool(name="submit_trade")
def submit_trade(
    account_id: str,
    symbol: str,
    side: Literal['buy', 'sell'],
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    trail_price: Optional[float] = None,
    trail_percent: Optional[float] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
    order_class: Annotated[Optional[str], Param(enum=['simple', 'bracket', 'oco', 'oto'])] = None,
    time_in_force: Annotated[str, Param(enum=['day', 'gtc', 'ioc', 'fok', 'opg', 'cls'])] = "day",
) -> str:
    """
    Submit a buy or sell order for an account. Order type is inferred from which
    price parameters are provided.

    Order type inference:
    - Market order: only qty or notional (no price params)
    - Limit order: limit_price set
    - Stop order: stop_price set
    - Stop-limit order: both stop_price and limit_price set
    - Trailing stop: trail_price or trail_percent set

    You must provide exactly one of qty or notional, not both.

    Args:
        account_id: The brokerage account UUID to trade in
        symbol: Ticker symbol to trade (e.g. 'AAPL', 'MSFT')
        side: Trade direction — 'buy' or 'sell'
        qty: Number of shares to trade. Fractional shares supported (e.g. 0.5).
            Mutually exclusive with notional.
        notional: Dollar amount to trade (e.g. 1000.0 buys $1000 worth).
            Mutually exclusive with qty. Only for market orders.
        limit_price: Limit price for limit/stop-limit orders
        stop_price: Stop trigger price for stop/stop-limit orders
        trail_price: Dollar offset for trailing stop orders (e.g. 2.0 trails by $2)
        trail_percent: Percentage offset for trailing stop orders (e.g. 5.0 trails by 5%)
        take_profit: Take-profit limit price for bracket orders
        stop_loss: Stop-loss trigger price for bracket orders
        stop_loss_limit: Stop-loss limit price for bracket orders (creates stop-limit leg)
        order_class: Order class for advanced orders.
            - simple: Standard single order (default)
            - bracket: Entry + take-profit + stop-loss legs
            - oco: One-cancels-other (two legs, one cancels the other)
            - oto: One-triggers-other (first fills, then activates second)
        time_in_force: How long the order stays active.
            - day: Cancelled at end of trading day (default)
            - gtc: Good-til-cancelled
            - ioc: Immediate-or-cancel (fill what you can, cancel rest)
            - fok: Fill-or-kill (fill entirely or cancel)
            - opg: Execute at market open
            - cls: Execute at market close

    Returns:
        Order confirmation dict with id, symbol, qty, side, type, status,
        limit_price, stop_price, filled_qty, and filled_avg_price

    Examples:
        submit_trade(account_id="d27aa8c2-...", symbol="AAPL", side="buy", qty=10)
        >>> {"id": "...", "symbol": "AAPL", "qty": 10.0, "side": "OrderSide.BUY",
             "type": "OrderType.MARKET", "status": "OrderStatus.ACCEPTED"}

        submit_trade(account_id="d27aa8c2-...", symbol="MSFT", side="sell", qty=5, limit_price=450.0)
        >>> {"id": "...", "symbol": "MSFT", "qty": 5.0, "side": "OrderSide.SELL",
             "type": "OrderType.LIMIT", "status": "OrderStatus.ACCEPTED"}

        submit_trade(account_id="d27aa8c2-...", symbol="TSLA", side="buy", qty=10,
                     order_class="bracket", take_profit=300.0, stop_loss=200.0)
        >>> {"id": "...", "symbol": "TSLA", "order_class": "OrderClass.BRACKET", ...}

    Raises:
        Exception: If the order is rejected or account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        trade_fn = broker.buy if side == "buy" else broker.sell
        result = trade_fn(
            account_id=account_id,
            symbol=symbol,
            qty=qty,
            notional=notional,
            limit_price=limit_price,
            stop_price=stop_price,
            trail_price=trail_price,
            trail_percent=trail_percent,
            take_profit=take_profit,
            stop_loss=stop_loss,
            stop_loss_limit=stop_loss_limit,
            order_class=order_class,
            time_in_force=time_in_force,
        )
        return success_response(result)
    except Exception as e:
        return error_response(
            f"Failed to {side} {symbol} for {account_id}: {str(e)}"
        )


@agent_tool(name="get_orders")
def get_orders(
    account_id: str,
    status: Literal['open', 'closed', 'all'] = "open",
) -> str:
    """
    Get orders for a brokerage account filtered by status.

    Args:
        account_id: The brokerage account UUID to query
        status: Filter orders by status.
            - open: Only unfilled/partially filled orders (default)
            - closed: Only completed/cancelled/expired orders
            - all: All orders regardless of status

    Returns:
        List of order dicts, each with id, symbol, qty, side, type, status,
        limit_price, filled_qty, filled_avg_price, submitted_at, and filled_at

    Examples:
        get_orders(account_id="d27aa8c2-...", status="open")
        >>> [{"id": "...", "symbol": "AAPL", "qty": 10.0, "side": "OrderSide.BUY",
              "type": "OrderType.LIMIT", "status": "OrderStatus.NEW", ...}]

        get_orders(account_id="d27aa8c2-...", status="closed")
        >>> [{"id": "...", "symbol": "MSFT", "qty": 5.0, "status": "OrderStatus.FILLED", ...}]

    Raises:
        Exception: If the account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        result = broker.get_orders(account_id, status)
        if not result:
            return success_response(f"No {status} orders found for this account")
        return success_response(result)
    except Exception as e:
        return error_response(
            f"Failed to get orders for {account_id}: {str(e)}"
        )


@agent_tool(name="cancel_order")
def cancel_order(
    account_id: str,
    order_id: str,
) -> str:
    """
    Cancel a specific open order by its UUID.

    Args:
        account_id: The brokerage account UUID that owns the order
        order_id: The UUID of the order to cancel

    Returns:
        Confirmation message that the order was cancelled

    Examples:
        cancel_order(account_id="d27aa8c2-...", order_id="b1e2f3a4-...")
        >>> "Order b1e2f3a4-... cancelled successfully"

    Raises:
        Exception: If the order does not exist, is already filled, or account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        broker.cancel_order(account_id, order_id)
        return success_response(f"Order {order_id} cancelled successfully")
    except Exception as e:
        return error_response(
            f"Failed to cancel order {order_id} for {account_id}: {str(e)}"
        )


@agent_tool(name="cancel_all_orders")
def cancel_all_orders(
    account_id: str,
) -> str:
    """
    Cancel all open orders for a brokerage account.

    Args:
        account_id: The brokerage account UUID

    Returns:
        Confirmation message that all orders were cancelled

    Examples:
        cancel_all_orders(account_id="d27aa8c2-...")
        >>> "All open orders cancelled for account d27aa8c2-..."

    Raises:
        Exception: If the account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        broker.cancel_all_orders(account_id)
        return success_response(f"All open orders cancelled for account {account_id}")
    except Exception as e:
        return error_response(
            f"Failed to cancel all orders for {account_id}: {str(e)}"
        )


@agent_tool(name="get_asset")
def get_asset(
    symbol: str,
) -> str:
    """
    Get detailed information for a single tradeable asset.

    Returns asset metadata including tradability, fractionability, marginability,
    shortability, exchange, and order size constraints.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL'), crypto pair (e.g. 'BTC/USD'),
            or asset UUID

    Returns:
        Asset detail dict with id, symbol, name, asset_class, exchange, status,
        tradable, fractionable, marginable, shortable, easy_to_borrow,
        min_order_size, min_trade_increment, price_increment,
        and maintenance_margin_requirement

    Examples:
        get_asset(symbol="AAPL")
        >>> {"id": "...", "symbol": "AAPL", "name": "Apple Inc.", "asset_class": "us_equity",
             "exchange": "NASDAQ", "status": "active", "tradable": True,
             "fractionable": True, "marginable": True, "shortable": True, ...}

        get_asset(symbol="BTC/USD")
        >>> {"id": "...", "symbol": "BTC/USD", "name": "Bitcoin", "asset_class": "crypto",
             "tradable": True, "fractionable": True, ...}

    Raises:
        Exception: If the symbol is invalid or not found
    """
    broker = ProphitBroker(sandbox=True)

    try:
        result = broker.get_asset(symbol)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to get asset info for {symbol}: {str(e)}")


