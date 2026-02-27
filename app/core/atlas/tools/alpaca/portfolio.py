"""Alpaca portfolio position tools for agent framework."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.brokers.alpaca_broker.broker import ProphitBroker
from app.repositories.user.trade_proposal import create_close_proposal
from typing import Annotated, Dict, List, Optional
from datetime import datetime, timezone


# ================================
# --> Helper funcs
# ================================

def _summarize_history(raw: Dict) -> Dict:
    """Condense raw portfolio history arrays into key summary metrics."""
    equity: List[float] = [e for e in (raw.get("equity") or []) if e is not None]
    pl: List[float] = [p for p in (raw.get("profit_loss") or []) if p is not None]
    timestamps: List[int] = raw.get("timestamp") or []

    if not equity:
        return {"error": "No equity data available"}

    start_equity = equity[0]
    end_equity = equity[-1]
    high = max(equity)
    low = min(equity)
    total_return = end_equity - start_equity
    total_return_pct = (total_return / start_equity * 100) if start_equity else 0.0

    # Reason: max drawdown measures worst peak-to-trough decline
    peak = equity[0]
    max_drawdown = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak else 0.0
        if dd > max_drawdown:
            max_drawdown = dd

    fmt_ts = lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    return {
        "period_start": fmt_ts(timestamps[0]) if timestamps else None,
        "period_end": fmt_ts(timestamps[-1]) if timestamps else None,
        "start_equity": round(start_equity, 2),
        "end_equity": round(end_equity, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 4),
        "max_drawdown_pct": round(max_drawdown, 4),
        "total_pl": round(pl[-1], 2) if pl else None,
        "base_value": raw.get("base_value"),
        "timeframe": raw.get("timeframe"),
        "data_points": len(equity),
    }


def _get_trade_dates(broker: ProphitBroker, account_id: str) -> Dict[str, str]:
    """Fetch FILL activities and return a symbol -> most recent trade date mapping.

    Reads transaction_time directly from the raw TradeActivity objects since
    FILL activities store timestamps in transaction_time, not date.
    """
    from alpaca.broker.requests import GetAccountActivitiesRequest
    from alpaca.trading.enums import ActivityType

    request = GetAccountActivitiesRequest(
        account_id=account_id,
        activity_types=[ActivityType("FILL")],
    )
    fills = broker.accounts.client.get_account_activities(activity_filter=request)

    trade_dates: Dict[str, str] = {}
    for fill in fills:
        symbol = getattr(fill, "symbol", None)
        txn_time = getattr(fill, "transaction_time", None)
        if symbol and txn_time and symbol not in trade_dates:
            # Reason: fills come back most-recent-first, so first seen = latest trade date
            trade_dates[symbol] = str(txn_time.date())
    return trade_dates


# ================================
# --> Tools
# ================================

@agent_tool(name="get_position")
def get_position(
    account_id: str,
    symbol: str,
) -> str:
    """
    Get the current open position for a specific symbol in a user's brokerage account.

    Returns position details including quantity, entry price, market value, and
    unrealized P&L. Returns None if no position exists for the symbol.

    Args:
        account_id: The brokerage account UUID to query
        symbol: Ticker symbol to look up (e.g. 'AAPL', 'MSFT')

    Returns:
        Position dict with symbol, qty, avg_entry_price, market_value,
        unrealized_pl, unrealized_plpc, and side. Returns None if no position found.

    Examples:
        get_position(account_id="d27aa8c2-...", symbol="AAPL")
        >>> {"symbol": "AAPL", "qty": 10.0, "avg_entry_price": 150.25,
             "market_value": 1750.00, "unrealized_pl": 247.50,
             "unrealized_plpc": 0.1647, "side": "PositionSide.LONG"}

        get_position(account_id="d27aa8c2-...", symbol="XYZ")
        >>> None (no position found)

    Raises:
        Exception: If the account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        result = broker.get_position(account_id, symbol)
        if result is None:
            return success_response(f"No open position found for {symbol}")
        trade_dates = _get_trade_dates(broker, account_id)
        result["last_trade_date"] = trade_dates.get(symbol)
        return success_response(result)
    except Exception as e:
        return error_response(
            f"Failed to get position for {symbol} in {account_id}: {str(e)}"
        )


@agent_tool(name="get_positions")
def get_positions(
    account_id: str,
) -> str:
    """
    Get all open positions for a user's brokerage account.

    Returns a list of every currently held position with quantity, entry price,
    market value, and unrealized P&L for each.

    Args:
        account_id: The brokerage account UUID to query

    Returns:
        List of position dicts, each with symbol, qty, avg_entry_price,
        market_value, unrealized_pl, unrealized_plpc, and side

    Examples:
        get_positions(account_id="d27aa8c2-...")
        >>> [{"symbol": "AAPL", "qty": 10.0, "avg_entry_price": 150.25,
              "market_value": 1750.00, "unrealized_pl": 247.50,
              "unrealized_plpc": 0.1647, "side": "PositionSide.LONG"},
             {"symbol": "MSFT", "qty": 5.0, "avg_entry_price": 420.00,
              "market_value": 2200.00, "unrealized_pl": 100.00,
              "unrealized_plpc": 0.0476, "side": "PositionSide.LONG"}]

    Raises:
        Exception: If the account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        positions = broker.get_positions(account_id)
        if not positions:
            return success_response("No open positions found for this account")
        trade_dates = _get_trade_dates(broker, account_id)
        for pos in positions:
            pos["last_trade_date"] = trade_dates.get(pos["symbol"])
        return success_response(positions)
    except Exception as e:
        return error_response(
            f"Failed to get positions for {account_id}: {str(e)}"
        )


@agent_tool(name="close_position")
def close_position(
    user_id: str,
    account_id: str,
    symbol: str,
    reasoning: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
) -> str:
    """
    Submit a close-position proposal for user approval. The position is NOT
    closed immediately — it is stored as a pending proposal that the user must
    approve or reject from the trade proposals page.

    IMPORTANT: Do NOT call this tool until the user has explicitly confirmed
    the close in chat. You must first present your analysis and reasoning,
    and wait for the user to say 'yes', 'go ahead', or otherwise confirm.

    Omit both qty and percentage to propose closing the entire position.
    Provide exactly one of qty or percentage for a partial close.

    Args:
        user_id: The internal user UUID (provided in system prompt)
        account_id: The brokerage account UUID
        symbol: Ticker symbol of the position to close (e.g. 'AAPL')
        reasoning: Your explanation for why this position should be closed.
            Must clearly explain the rationale so the user can make an informed decision.
        qty: Number of shares to sell. Omit for full close.
        percentage: Percentage of position to close (e.g. 50.0 for 50%). Omit for full close.

    Returns:
        Confirmation that the close-position proposal was created and is pending.

    Examples:
        close_position(user_id="abc-123", account_id="d27aa8c2-...", symbol="AAPL",
                       reasoning="Position hit stop-loss target")
        >>> "Close position proposal created: CLOSE 100% of AAPL — pending user approval"

        close_position(user_id="abc-123", account_id="d27aa8c2-...", symbol="AAPL",
                       reasoning="Taking partial profits", percentage=50.0)
        >>> "Close position proposal created: CLOSE 50.0% of AAPL — pending user approval"

    Raises:
        ValueError: If both qty and percentage are provided
        Exception: If the proposal could not be created
    """
    if qty is not None and percentage is not None:
        return error_response("Cannot specify both qty and percentage")

    try:
        proposal = create_close_proposal(
            user_id=user_id,
            account_id=account_id,
            symbol=symbol,
            qty=qty,
            percentage=percentage,
            agent_reasoning=reasoning,
        )

        # Reason: Build a clear summary for the agent's response
        if qty is not None:
            amount_str = f"{qty} shares of"
        elif percentage is not None:
            amount_str = f"{percentage}% of"
        else:
            amount_str = "100% of"

        return success_response(
            f"Close position proposal created: CLOSE {amount_str} {symbol.upper()} "
            f"— pending user approval. Proposal ID: {proposal['id']}"
        )
    except Exception as e:
        msg = str(e)
        if "psycopg2" in msg or "sqlalchemy" in msg.lower():
            msg = msg.split("\n")[0]
        return error_response(f"Failed to create close position proposal: {msg}")


@agent_tool(name="get_portfolio_history")
def get_portfolio_history(
    account_id: str,
    period: Annotated[str, Param(enum=['1D', '1W', '1M', '3M', '6M', '1A', 'all'])] = "1M",
    timeframe: Annotated[str, Param(enum=['1Min', '5Min', '15Min', '1H', '1D'])] = "1D",
    extended_hours: Optional[bool] = None,
) -> str:
    """
    Get historical portfolio equity and profit/loss over time.

    Args:
        account_id: The brokerage account UUID to query
        period: Lookback period for history.
            - 1D: 1 day
            - 1W: 1 week
            - 1M: 1 month (default)
            - 3M: 3 months
            - 6M: 6 months
            - 1A: 1 year
            - all: All available history
        timeframe: Granularity of data points.
            - 1Min: 1-minute bars
            - 5Min: 5-minute bars
            - 15Min: 15-minute bars
            - 1H: Hourly bars
            - 1D: Daily bars (default)
        extended_hours: Include pre-market and after-hours data

    Returns:
        Summary dict with period_start, period_end, start_equity, end_equity,
        high, low, total_return, total_return_pct, max_drawdown_pct, total_pl,
        base_value, timeframe, and data_points

    Examples:
        get_portfolio_history(account_id="d27aa8c2-...", period="1M", timeframe="1D")
        >>> {"period_start": "2026-01-23 00:00", "period_end": "2026-02-23 00:00",
             "start_equity": 70000.0, "end_equity": 71851.78, "high": 71921.01,
             "low": 70755.56, "total_return": 1851.78, "total_return_pct": 2.6454,
             "max_drawdown_pct": 1.62, "total_pl": 71851.78, "base_value": 0.0,
             "timeframe": "1D", "data_points": 22}

    Raises:
        Exception: If the account ID is invalid
    """
    broker = ProphitBroker(sandbox=True)

    try:
        raw = broker.get_portfolio_history(
            account_id=account_id,
            period=period,
            timeframe=timeframe,
            extended_hours=extended_hours,
        )
        summary = _summarize_history(raw)
        return success_response(summary)
    except Exception as e:
        return error_response(
            f"Failed to get portfolio history for {account_id}: {str(e)}"
        )


if __name__ == "__main__":
    print(get_portfolio_history(account_id="d27aa8c2-5931-499b-bdfa-05c47b07ad70", period="1D", timeframe="1Min"))