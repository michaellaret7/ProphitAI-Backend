"""Cross-sectional result cache for universe-scoped indicators.

Universe indicators compute the same cross-sectional panel for every ticker
in a backtest (sector z-scores, universe-wide rank, rolling dispersion,
etc.), then slice per-ticker at the end. Without caching this is O(n²) in
universe size — a 220-ticker run spent ~58 minutes recomputing identical
panels 220 times.

This module provides:

- ``stamp_shared_panel(df)`` — attach a run-scoped UUID to a shared panel
  BEFORE it's attached to per-ticker ``df.attrs``. The UUID survives
  pandas ``__finalize__`` (which deep-copies ``attrs``) because Python
  ``copy.deepcopy`` treats strings as atomic. Without the stamp, every
  ticker would see a freshly-copied panel object with a new ``id(...)``
  and the cache would miss on every call.

- ``crosssectional_cache_key(panel, *params)`` — build a stable key from
  the stamped UUID plus the indicator's parameters.

- ``get_or_compute_crosssectional(key, compute)`` — standard cache-aside
  wrapper with bounded size.

- ``clear_crosssectional_cache()`` — reset for tests.

## Typical strategy-side usage

In your panel-construction helper (or ``DataResolver`` shared-scope path
which auto-stamps — see ``DataResolver.resolve``):

    from prophitai_algo_trading.indicators import stamp_shared_panel

    panel = build_panel(...)
    stamp_shared_panel(panel)
    for ticker_df in data.values():
        ticker_df.attrs["my_panel"] = panel

In your universe indicator:

    from prophitai_algo_trading.indicators import (
        crosssectional_cache_key,
        get_or_compute_crosssectional,
    )

    class MyUniverseIndicator(BaseIndicator):
        def calculate(self):
            panel = self.df.attrs.get("my_panel")
            key = crosssectional_cache_key(
                panel, self.window, self.quantile,  # include all params
            )
            full = get_or_compute_crosssectional(
                key, lambda: self._compute_full(panel),
            )
            # Per-ticker slice — cheap, not cached
            mine = full[full["symbol"] == self._symbol()]
            ...
"""

from __future__ import annotations

import uuid
from typing import Callable

import pandas as pd


# ================================
# --> Module state
# ================================

# Reason: bounded cache prevents memory leaks across long-lived processes
# (e.g., live backtest servers) while preserving hits for a single run
# which only needs one entry per (panel, param-set) tuple.
_CACHE: dict = {}
_CACHE_MAX_ENTRIES = 4

_PANEL_RUN_ID_KEY = "_prophit_universe_run_id"


# ================================
# --> Public API
# ================================


def stamp_shared_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Attach a run-scoped UUID to ``panel.attrs`` so consumers can cache on it.

    Call ONCE per run, before the panel is attached to per-ticker
    ``df.attrs``. Subsequent pandas operations (reindex, copy, drop) will
    deep-copy ``attrs`` but strings are atomic in ``copy.deepcopy`` — the
    UUID value is preserved across every copy, giving universe indicators
    a stable cache key.

    Idempotent: if the panel already has a run id, it is preserved.

    Args:
        panel: The shared cross-sectional DataFrame.

    Returns:
        The same DataFrame (for chaining).
    """

    if _PANEL_RUN_ID_KEY not in panel.attrs:
        panel.attrs[_PANEL_RUN_ID_KEY] = uuid.uuid4().hex

    return panel


def crosssectional_cache_key(
    panel: pd.DataFrame | None,
    *params: object,
) -> tuple:
    """Build a cache key for a universe indicator's full-panel output.

    The key combines the panel's run-scoped UUID (set by
    ``stamp_shared_panel``) with the caller's indicator parameters so two
    indicators that use the same panel but different params don't collide.

    Args:
        panel: The shared panel DataFrame (or ``None``).
        *params: Indicator params that change the computed output.

    Returns:
        A hashable tuple usable as a ``dict`` key.
    """

    run_id: object = None

    if isinstance(panel, pd.DataFrame):
        run_id = panel.attrs.get(_PANEL_RUN_ID_KEY)

        # Reason: fall back to a content tag if the panel wasn't stamped.
        # Safe for a single-process run; different processes building
        # identical panels will collide, which is acceptable because the
        # output would be identical anyway.
        if run_id is None and not panel.empty:
            run_id = ("shape-fallback", panel.shape, len(panel))

    return (run_id, *params)


def get_or_compute_crosssectional(
    cache_key: tuple,
    compute: Callable[[], pd.DataFrame],
) -> pd.DataFrame:
    """Return cached cross-sectional result or compute + cache it.

    Args:
        cache_key: Key from ``crosssectional_cache_key``.
        compute: Zero-arg callable that produces the full cross-sectional
            output when the cache misses.

    Returns:
        The cached or freshly computed DataFrame.
    """

    cached = _CACHE.get(cache_key)

    if cached is not None:
        return cached

    result = compute()

    # Reason: clear rather than LRU-evict to keep the implementation
    # trivial and correct. One backtest run populates one entry per
    # indicator; 4 slots comfortably holds a multi-stage pipeline.
    if len(_CACHE) >= _CACHE_MAX_ENTRIES:
        _CACHE.clear()

    _CACHE[cache_key] = result

    return result


def clear_crosssectional_cache() -> None:
    """Drop all cached entries. Use in tests or before a fresh backtest run."""

    _CACHE.clear()
