"""Portfolio tracker reporting helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd


class PortfolioTrackerReportingMixin:
    """Equity and trade-log reporting helpers."""

    def record_equity(self, timestamp: datetime, prices: dict[str, float]) -> None:
        """Snapshot current portfolio equity using live prices for open positions."""
        self.update_market_prices(prices)
        position_value = self._mark_to_market(prices)
        equity = self.cash + position_value
        self._peak_equity = max(self._peak_equity, equity)
        self._equity_history.append(
            {
                "timestamp": timestamp,
                "equity": round(equity, 2),
                "cash": round(self.cash, 2),
                "position_value": round(position_value, 2),
            }
        )

    def get_equity_curve(self) -> pd.DataFrame:
        """Return equity history as a DataFrame indexed by timestamp."""
        if not self._equity_history:
            return pd.DataFrame(columns=["equity", "cash", "position_value"])
        df = pd.DataFrame(self._equity_history)
        return df.set_index("timestamp")

    def get_trades_df(self) -> pd.DataFrame:
        """Return trade log as a DataFrame."""
        if not self._trades:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "entry_date",
                    "exit_date",
                    "direction",
                    "entry_price",
                    "exit_price",
                    "shares",
                    "pnl",
                    "return_pct",
                ]
            )
        return pd.DataFrame([vars(trade) for trade in self._trades])
