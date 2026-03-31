"""VWAP Reversion + Hurst Regime strategy for 1-minute BTC data.

Combines rolling VWAP as a dynamic fair-value anchor with the Hurst exponent
for regime detection. Trades mean-reversion when BTC is anti-persistent
(Hurst < 0.45) and momentum via EMA crossovers when persistent (Hurst > 0.55).
Stays flat during random-walk regimes to preserve capital.

Optimised for 1-minute crypto OHLCV data. Default parameters tuned for BTC
intraday behaviour: high noise, frequent regime switches, and strong
liquidation-driven momentum bursts.

Recommended warmup_bars: 180 (covers hurst_window + vwap_window convergence).
Default data_interval: 1min.
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.indicators.vwap_hurst import VwapHurst
from prophitai_algo_trading.strategies.vwap_hurst_btc.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class VwapHurstBTC(BaseStrategy):
    """VWAP Reversion + Hurst Regime strategy for 1-minute BTC.

    Args:
        vwap_window: Rolling VWAP lookback in bars.
        hurst_window: Lookback for Hurst exponent R/S estimation.
        atr_period: ATR period for normalising VWAP deviation.
        ema_fast_period: Fast EMA for trending-regime momentum signals.
        ema_slow_period: Slow EMA for trending-regime momentum signals.
        hurst_mr_threshold: Hurst below this = mean-reverting regime.
        hurst_trend_threshold: Hurst above this = trending regime.
        vwap_entry_mult: ATR multiplier for VWAP reversion entry.
        vwap_exit_mult: ATR multiplier for VWAP reversion exit.
    """

    def __init__(
        self,
        vwap_window: int = 60,
        hurst_window: int = 120,
        atr_period: int = 14,
        ema_fast_period: int = 8,
        ema_slow_period: int = 21,
        hurst_mr_threshold: float = 0.45,
        hurst_trend_threshold: float = 0.55,
        vwap_entry_mult: float = 1.5,
        vwap_exit_mult: float = 0.3,
    ):
        self.vwap_window = vwap_window
        self.hurst_window = hurst_window
        self.atr_period = atr_period
        self.ema_fast_period = ema_fast_period
        self.ema_slow_period = ema_slow_period
        self.hurst_mr_threshold = hurst_mr_threshold
        self.hurst_trend_threshold = hurst_trend_threshold
        self.vwap_entry_mult = vwap_entry_mult
        self.vwap_exit_mult = vwap_exit_mult
        self._indicator: VwapHurst | None = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute VWAP, Hurst, ATR, and EMAs on the full DataFrame."""
        if df.empty:
            return df

        self._indicator = VwapHurst(
            df,
            vwap_window=self.vwap_window,
            hurst_window=self.hurst_window,
            atr_period=self.atr_period,
            ema_fast_period=self.ema_fast_period,
            ema_slow_period=self.ema_slow_period,
            hurst_mr_threshold=self.hurst_mr_threshold,
            hurst_trend_threshold=self.hurst_trend_threshold,
        )
        return self._indicator.df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicator outputs for the last row."""
        if self._indicator is None:
            return self.calculate_indicators(df)

        return self._indicator.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on VWAP + Hurst regime logic."""
        return {
            "long_entry": long_entry(df, self.vwap_entry_mult),
            "long_exit": long_exit(df, self.vwap_exit_mult),
            "short_entry": short_entry(df, self.vwap_entry_mult),
            "short_exit": short_exit(df, self.vwap_exit_mult),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """VWAP z-score magnitude — larger deviation from fair value = stronger signal."""
        return df["vwap_z_score"].abs()

    def get_sizing_hints(
        self,
        row: pd.Series,
        target_position: int,
    ) -> dict[str, object]:
        """Publish regime and ATR-based stop hints for shared sizers."""
        hints = super().get_sizing_hints(row, target_position)
        atr = self._coerce_positive_float(row.get("atr"))
        if atr is not None:
            hints["stop_distance"] = atr * max(self.vwap_exit_mult, 1.0)
            hints["risk_per_share"] = hints["stop_distance"]
        hints["regime"] = row.get("hurst_regime")
        hints["expected_holding_bars"] = self.vwap_window
        return hints

    @property
    def min_bars_required(self) -> int:
        """Hurst window is the longest lookback; add VWAP window for convergence."""
        return self.hurst_window + self.vwap_window
