"""Shared helpers for ExecutionModels.

Both simulated and broker executions share the same diffing logic:
  - Resolve a fill price for the target symbol.
  - Compute current signed shares in the portfolio.
  - Decide whether the change is material enough to trade (tolerance).

Extracted so the two ExecutionModels stay tight and focused on "what
side-effect do I fire for each decision" rather than "what decision to
make."
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prophitai_algo_trading.framework.models import AlgorithmContext
    from prophitai_algo_trading.portfolio import Portfolio


#     ================================
# --> Price
#     ================================

def get_fill_price(ctx: "AlgorithmContext", symbol: str) -> float | None:
    """Last-close price for ``symbol`` at the current bar, or None if
    the symbol has no data or a non-positive price."""
    df = ctx.data.get(symbol)

    if df is None or df.empty:
        return None

    price = float(df["close"].iloc[-1])

    if price <= 0.0:
        return None

    return price


#     ================================
# --> Portfolio introspection
#     ================================

def current_signed_shares(portfolio: "Portfolio", symbol: str) -> float:
    """Return +shares (long), -shares (short), or 0 (flat) for ``symbol``."""
    pos = portfolio.positions.get(symbol)

    if pos is None:
        return 0.0

    return pos.shares * pos.direction


#     ================================
# --> Material-change filter
#     ================================

def is_material_change(
    target_shares: float,
    current_signed: float,
    price: float,
    equity: float,
    min_change_pct: float,
) -> bool:
    """True if the |notional delta| exceeds ``min_change_pct * equity``.

    Used to skip trivial rebalance churn — e.g. "100 shares held, target
    101 shares" is not worth a commission. Notional-based so the
    threshold scales with position size rather than raw share count.
    """
    if equity <= 0 or min_change_pct <= 0:
        return True

    delta_shares = abs(target_shares - current_signed)
    delta_notional = delta_shares * price

    return delta_notional > equity * min_change_pct
