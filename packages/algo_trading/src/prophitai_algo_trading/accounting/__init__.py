"""Portfolio state and trade ledger — cash, positions, closed trades, cost model.

The accounting layer is pure in-memory bookkeeping. ``Portfolio``
consumes fills (from an ``ExecutionModel`` via an ``OrderSink``) and
tracks cash, open ``Position``\\ s, completed ``Trade``\\ s, and mark-
to-market equity history. ``CostModel`` owns transaction cost math.
"""

from prophitai_algo_trading.accounting.cost_model import CostModel
from prophitai_algo_trading.accounting.portfolio import (
    Portfolio,
    Position,
    Trade,
)

__all__ = [
    "CostModel",
    "Portfolio",
    "Position",
    "Trade",
]
