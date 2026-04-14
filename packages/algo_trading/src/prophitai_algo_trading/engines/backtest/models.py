from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    """Container for all backtest outputs.

    Attributes:
        metrics: Dictionary of computed performance metrics.
        equity_curve: Timestamp-indexed equity history.
        trades: One row per round-trip trade.
        strategy_data: Strategy's DataFrame with indicators and signals.
    """

    metrics: dict[str, float | int]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    strategy_data: pd.DataFrame


class SignalData(NamedTuple):
    """Phase 1 outputs: aligned data, raw position arrays, and entry scores."""

    common_index: pd.DatetimeIndex
    aligned: dict[str, pd.DataFrame]
    strategy_frames: dict[str, pd.DataFrame]
    raw_positions: dict[str, np.ndarray]
    entry_scores: dict[str, np.ndarray]
    entry_candidates: dict[str, np.ndarray]


class SimulationArrays(NamedTuple):
    """Pre-built numpy arrays for Phase 2 simulation."""

    close_matrix: np.ndarray
    ffilled_close_matrix: np.ndarray
    vol_matrix: np.ndarray
    positions_matrix: np.ndarray
    score_matrix: np.ndarray
    candidate_matrix: np.ndarray
    ticker_list: list[str]
