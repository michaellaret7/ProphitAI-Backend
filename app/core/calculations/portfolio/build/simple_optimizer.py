"""Simple long/short optimizer using provided allocations and exposure targets.

This optimizer mirrors the structure of the simple allocator but assumes the
incoming portfolio already contains per-ticker allocations (not convictions).
It uses the existing correlation-aware, risk-based optimizer to refine weights
within the long and short books, then enforces gross and net exposure targets.

Inputs:
- portfolio_dict: {ticker: {"allocation": float, "position": "long"|"short"}}
- target_gross_exposure: float (sum of |weights|)
- target_net_exposure: float (sum of weights; positive = net long)

Output:
- dict[ticker, dict]: {ticker: {"ticker": str, "position": str, "allocation": float}}
  where allocation is the absolute value and position is the sign-derived side.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.core.calculations.core.data_service import DataService
from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.portfolio.build.optimizer import PortfolioOptimizer


class SimplePortfolioOptimizer:
    """Minimal optimizer for long/short portfolios with provided allocations."""

    def __init__(
        self,
        portfolio_dict: Dict[str, Dict[str, float | str]],
        *,
        target_gross_exposure: float = 1.0,
        target_net_exposure: float = 0.0,
        lookback_days: int = 252,
        data_service: Optional[DataService] = None,
    ) -> None:
        self.portfolio_dict = portfolio_dict or {}
        self.target_gross = float(target_gross_exposure)
        self.target_net = float(target_net_exposure)
        self.lookback_days = int(lookback_days)
        self.ds = data_service or DataService()
        self.optimizer = PortfolioOptimizer()

    # ---------------------------- public API ---------------------------- #
    def optimize(self) -> Dict[str, Dict[str, str | float]]:
        tickers_long, tickers_short, base_allocations = self._parse_portfolio()
        if not tickers_long and not tickers_short:
            return {}

        # Fetch prices and compute daily returns
        price_map = self._fetch_prices(list(set(tickers_long + tickers_short)))
        returns_df = self._build_returns(price_map)
        if returns_df.empty:
            return {}

        # Covariance (annualized)
        cov = CorrelationAnalysis.covariance_matrix(returns_df, annualize=True)

        # Risk-aware refinement within each book
        w_long = self._risk_based_book_weights(cov, tickers_long, base_allocations)
        w_short = self._risk_based_book_weights(cov, tickers_short, base_allocations)

        # Solve book exposures from gross/net targets
        L, S = self._solve_exposures(self.target_gross, self.target_net)

        # Combine signed weights
        final_weights: Dict[str, float] = {}
        if not w_long.empty and L > 0:
            wL = (w_long / float(w_long.sum())) * L if float(w_long.sum()) > 0 else w_long
            for tkr, w in wL.items():
                final_weights[tkr] = float(w)
        if not w_short.empty and S > 0:
            wS = (w_short / float(w_short.sum())) * S if float(w_short.sum()) > 0 else w_short
            for tkr, w in wS.items():
                final_weights[tkr] = -float(w)

        # Normalize any numerical drift to target gross
        if final_weights:
            gross = float(np.sum([abs(x) for x in final_weights.values()]))
            if gross > 0:
                scale = self.target_gross / gross
                for k in list(final_weights.keys()):
                    final_weights[k] = float(final_weights[k] * scale)

        # Structured output
        final: Dict[str, Dict[str, str | float]] = {}
        for ticker, weight in final_weights.items():
            final[ticker] = {
                "ticker": ticker,
                "position": "long" if weight >= 0 else "short",
                "allocation": abs(weight),
            }

        return final

    # --------------------------- implementation ------------------------- #
    def _parse_portfolio(self) -> Tuple[list[str], list[str], pd.Series]:
        longs: list[str] = []
        shorts: list[str] = []
        alloc_map: Dict[str, float] = {}

        for t, cfg in (self.portfolio_dict or {}).items():
            if not t:
                continue
            tkr = t.upper()
            pos = str(cfg.get("position", "long")).strip().lower()
            alloc_raw = cfg.get("allocation", 0.0)
            try:
                alloc = float(alloc_raw)
            except Exception:
                alloc = 0.0
            alloc = float(max(0.0, alloc))

            if pos == "short":
                shorts.append(tkr)
            else:
                longs.append(tkr)
            alloc_map[tkr] = alloc

        # Feasibility: gross must be >= |net|
        if self.target_gross < abs(self.target_net):
            self.target_net = float(np.sign(self.target_net)) * float(self.target_gross)

        return longs, shorts, pd.Series(alloc_map)

    def _fetch_prices(self, tickers: list[str]) -> Dict[str, pd.Series]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.lookback_days)
        return self.ds.get_bulk_close_series(tickers, start, end)

    def _build_returns(self, price_map: Dict[str, pd.Series]) -> pd.DataFrame:
        rets: Dict[str, pd.Series] = {}
        for t, px in (price_map or {}).items():
            if px is not None and not px.empty:
                r = ReturnsCalculator.daily_price_returns(px)
                if r is not None and not r.empty:
                    rets[t] = r
        if not rets:
            return pd.DataFrame()
        df = pd.concat(rets, axis=1)
        return df.dropna(how="any")

    def _risk_based_book_weights(
        self,
        cov_full: pd.DataFrame,
        book_tickers: list[str],
        base_allocations: pd.Series,
    ) -> pd.Series:
        if not book_tickers:
            return pd.Series(dtype=float)

        sub = cov_full.loc[
            [t for t in book_tickers if t in cov_full.index],
            [t for t in book_tickers if t in cov_full.columns],
        ]
        if sub.empty:
            n = len(book_tickers)
            return pd.Series(np.full(n, 1.0 / n), index=book_tickers)

        # Base allocations (fallback to equal if all zeros)
        base = base_allocations.reindex(sub.index).fillna(0.0)
        if float(base.sum()) <= 0.0:
            base = pd.Series(np.full(len(sub.index), 1.0 / len(sub.index)), index=sub.index)

        # Use existing risk-based optimizer (vol and avg-corr aware)
        w = self.optimizer.optimize_weights_risk_based(sub, base_convictions=base)

        # Guard against degenerate solutions
        if w is None or w.empty or not np.isfinite(w.values).all():
            n = len(sub.index)
            w = pd.Series(np.full(n, 1.0 / n), index=sub.index)

        # Light multiplicative tilt by base allocations then renormalize
        w_adj = (w * (base / base.sum()).fillna(0.0))
        total = float(w_adj.sum())
        if total > 0:
            w_adj = w_adj / total
        return w_adj

    @staticmethod
    def _solve_exposures(gross: float, net: float) -> Tuple[float, float]:
        """Return (L, S) from gross/net targets with non-negativity guards.

        L + S = gross, L - S = net  => L = (gross+net)/2, S = (gross-net)/2
        """
        L = 0.5 * (float(gross) + float(net))
        S = 0.5 * (float(gross) - float(net))
        L = max(0.0, float(L))
        S = max(0.0, float(S))
        return (L, S)

if __name__ == "__main__":
    # Test with a small consumer staples portfolio (allocations provided)
    print("Testing SimplePortfolioOptimizer (before vs after annualized total returns)...")

    def _print_weights(label: str, weights: dict[str, float]) -> None:
        print(f"{label} weights:")
        for t, w in sorted(weights.items(), key=lambda x: x[0]):
            side = "long" if w >= 0 else "short"
            print(f"  {t:6s}: {w:+.5f} ({side})")
        gross = sum(abs(v) for v in weights.values())
        net = sum(weights.values())
        print(f"  -> Gross: {gross:.5f}, Net: {net:.5f}")
        print()
    
    from app.utils.gpt_parser import canonical_portfolio
    from app.db.core.db_config import ProphitAltsSession
    from app.db.core.prophit_alts_models import FundFinalPosition

    session = ProphitAltsSession()
    portfolio_data = session.query(FundFinalPosition).filter(FundFinalPosition.fund_name == "consumer_staples_fund").all()
    portfolio_data = {position.ticker_name: {
        "allocation": position.portfolio_allocation,
        "position": position.position.value,
    } for position in portfolio_data}
    portfolio_data = canonical_portfolio(portfolio_data)
    session.close()

    # Build signed weights for "before" (positive longs, negative shorts)
    before_weights: dict[str, float] = {}
    for t, cfg in portfolio_data.items():
        a = float(cfg.get("allocation", 0.0) or 0.0)
        before_weights[t.upper()] = a if str(cfg.get("position", "long")).lower() != "short" else -a

    # Compute initial exposures to reuse as optimizer targets
    gross0 = float(sum(abs(w) for w in before_weights.values()))
    net0 = float(sum(before_weights.values()))

    # Fetch closes and dividends over the same lookback as the optimizer will use
    lookback = 252
    ds = DataService()
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=lookback)

    tickers = list(before_weights.keys())
    price_map = ds.get_bulk_close_series(tickers, start_dt, end_dt)

    # Prepare closes/dividends dicts
    ticker_closes: dict[str, pd.Series] = {}
    ticker_dividends: dict[str, pd.Series] = {}
    for t in tickers:
        s = price_map.get(t)
        if s is not None and not pd.Series(s).empty:
            ser = pd.Series(s).astype(float)
            ticker_closes[t] = ser
            try:
                divs = ds.get_dividends(t, start_dt, end_dt).series
                ticker_dividends[t] = pd.Series(divs).astype(float)
            except Exception:
                ticker_dividends[t] = pd.Series(dtype=float)

    if not ticker_closes:
        print("Insufficient price data to run test")
    else:
        # Portfolio total returns BEFORE optimization (gross-normalized renormalization)
        before_daily = PortfolioReturnsCalculator.weighted_total_returns(
            ticker_dividends,
            ticker_closes,
            before_weights,
            dropna=False,
            renormalize_each_day=True,
            normalization="gross",
        ).dropna()

        ann_before = ReturnsCalculator.annualized_return(before_daily)

        _print_weights("Before", before_weights)

        # Run optimizer with same gross/net targets for fair comparison
        opt = SimplePortfolioOptimizer(
            portfolio_dict=portfolio_data,
            target_gross_exposure=gross0,
            target_net_exposure=net0,
            lookback_days=lookback,
        )
        after = opt.optimize()

        # Convert optimized structured output back to signed weights
        after_weights: dict[str, float] = {}
        for t, meta in after.items():
            w = float(meta.get("allocation", 0.0) or 0.0)
            after_weights[t] = w if str(meta.get("position", "long")).lower() != "short" else -w

        # Portfolio total returns AFTER optimization
        after_daily = PortfolioReturnsCalculator.weighted_total_returns(
            ticker_dividends,
            ticker_closes,
            after_weights,
            dropna=False,
            renormalize_each_day=True,
            normalization="gross",
        ).dropna()

        ann_after = ReturnsCalculator.annualized_return(after_daily)

        # Exposures for reference
        long_before = sum(w for w in before_weights.values() if w > 0)
        short_before = abs(sum(w for w in before_weights.values() if w < 0))
        long_after = sum(w for w in after_weights.values() if w > 0)
        short_after = abs(sum(w for w in after_weights.values() if w < 0))

        _print_weights("After", after_weights)

        print("Results:")
        print(f"  Before (annualized total return): {ann_before:.2%}")
        print(f"  After  (annualized total return): {ann_after:.2%}")
        print(f"  Before exposures  -> Gross: {long_before + short_before:.2f}, Net: {long_before - short_before:.2f}")
        print(f"  After exposures   -> Gross: {long_after + short_after:.2f}, Net: {long_after - short_after:.2f}")




