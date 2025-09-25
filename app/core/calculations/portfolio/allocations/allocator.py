"""Simple long/short allocator using risk-based weights and exposure targets.

This class keeps the logic intentionally minimal while leveraging the shared
calculations infrastructure (DataService, Returns/Risk calculators, Optimizer).

Inputs:
- portfolio_dict: {ticker: {"conviction": 0..1, "position": "long"|"short"}}
- target_annual_vol: float (e.g., 0.15 for 15%) [used for diagnostics; allocation
  primarily respects exposure targets to keep this simple]
- target_gross_exposure: float (sum of |weights|)
- target_net_exposure: float (sum of weights, positive=net long)

Output:
- dict[ticker, dict]: structured format with ticker, position, and allocation fields
  Format: {ticker: {"ticker": str, "position": "long"/"short", "allocation": float}}
  where allocation is the absolute value of the weight, and position is determined by sign

Design notes (simple yet effective):
- Within each book (longs, shorts), compute risk-based weights that down-weight
  high-vol/high-correlation assets while respecting convictions.
- Enforce net/gross exposures in closed-form: Long = (G+N)/2, Short = (G-N)/2.
- Keep DRY by reusing existing calculators and optimizer provided in the codebase.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.core.calculations.core.data_service import DataService
from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.utils.gpt_parser import canonical_portfolio


class SimplePortfolioAllocator:
    """Minimal allocator for long/short portfolios.

    Example usage:
        allocator = SimplePortfolioAllocator(
            portfolio_dict={
                "AAPL": {"conviction": 0.8, "position": "long"},
                "MSFT": {"conviction": 0.6, "position": "long"},
                "TSLA": {"conviction": 0.7, "position": "short"},
            },
            target_annual_vol=0.15,
            target_gross_exposure=1.0,
            target_net_exposure=0.0,
        )
        weights = allocator.allocate()
    """

    def __init__(
        self,
        portfolio_dict: Dict[str, Dict[str, float | str]],
        *,
        target_annual_vol: float,
        target_gross_exposure: float = 1.0,
        target_net_exposure: float = 0.0,
        lookback_days: int = 252,
        data_service: Optional[DataService] = None,
    ) -> None:
        self.portfolio_dict = portfolio_dict or {}
        self.target_vol = float(target_annual_vol)
        self.target_gross = float(target_gross_exposure)
        self.target_net = float(target_net_exposure)
        self.lookback_days = int(lookback_days)
        self.ds = data_service or DataService()

    # ---------------------------- public API ---------------------------- #
    def allocate(self) -> Dict[str, Dict[str, str | float]]:
        tickers_long, tickers_short, convictions = self._parse_portfolio()
        if not tickers_long and not tickers_short:
            return {}

        # Fetch prices and compute simple daily returns
        price_map = self._fetch_prices(list(set(tickers_long + tickers_short)))
        returns_df = self._build_returns(price_map)
        if returns_df.empty:
            return {}

        # Risk-based weights per book using covariance (annualized)
        cov = CorrelationAnalysis.covariance_matrix(returns_df, annualize=True)
        w_long = self._risk_based_book_weights(cov, tickers_long, convictions)
        w_short = self._risk_based_book_weights(cov, tickers_short, convictions)

        # Solve long/short exposures from gross/net targets
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

        # Normalize tiny drift (numeric safety)
        if final_weights:
            gross = float(np.sum([abs(x) for x in final_weights.values()]))
            if gross > 0:
                scale = self.target_gross / gross
                for k in list(final_weights.keys()):
                    final_weights[k] = float(final_weights[k] * scale)

        # Convert to structured format
        final: Dict[str, Dict[str, str | float]] = {}
        for ticker, weight in final_weights.items():
            final[ticker] = {
                "ticker": ticker,
                "position": "long" if weight >= 0 else "short",
                "allocation": abs(weight)
            }

        return final

    # --------------------------- implementation ------------------------- #
    def _parse_portfolio(self) -> Tuple[list[str], list[str], pd.Series]:
        longs: list[str] = []
        shorts: list[str] = []
        conv_map: Dict[str, float] = {}

        for t, cfg in (self.portfolio_dict or {}).items():
            if not t:
                continue
            tkr = t.upper()
            pos = str(cfg.get("position", "long")).strip().lower()
            conv = float(cfg.get("conviction", 1.0) or 0.0)
            conv = float(min(max(conv, 0.0), 1.0))
            if pos == "short":
                shorts.append(tkr)
            else:
                longs.append(tkr)
            conv_map[tkr] = conv

        # Basic feasibility: gross must be >= |net|
        if self.target_gross < abs(self.target_net):
            # Clamp net to feasible range while keeping sign
            self.target_net = float(np.sign(self.target_net)) * float(self.target_gross)

        return longs, shorts, pd.Series(conv_map)

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
        # Drop rows with any NA to keep covariance well-behaved
        return df.dropna(how="any")

    def optimize_weights_risk_based(
        self,
        cov: pd.DataFrame,
        base_convictions: Optional[pd.Series] = None
    ) -> pd.Series:
        """Calculate risk-based weights using inverse risk weighting.
        
        This replicates the original correlation portfolio builder approach:
        - risk score = volatility * (1 + avg_correlation)
        - weight inversely to risk score
        """
        if cov.empty:
            return pd.Series(dtype=float)
        
        n = len(cov)
        tickers = list(cov.index)
        
        # If no base convictions, use equal weight
        if base_convictions is None:
            base_convictions = pd.Series(np.full(n, 1.0 / n), index=tickers)
        
        # Individual volatilities from diagonal
        individual_vols = np.sqrt(np.diag(cov.values))
        
        # Calculate risk scores for each asset
        risk_scores: dict[str, float] = {}
        cov_matrix = cov.values
        
        for i, ticker in enumerate(tickers):
            vol_score = float(individual_vols[i])
            corr_with_others: list[float] = []
            for j in range(n):
                if i != j and individual_vols[i] > 0 and individual_vols[j] > 0:
                    correlation = cov_matrix[i, j] / (individual_vols[i] * individual_vols[j])
                    corr_with_others.append(abs(float(correlation)))
            avg_corr = float(np.mean(corr_with_others)) if corr_with_others else 0.0
            risk_scores[ticker] = vol_score * (1.0 + avg_corr)
        
        max_risk = max(risk_scores.values()) if risk_scores else 1.0
        
        # Inverse-risk adjust convictions, then normalize
        adjusted_weights: dict[str, float] = {}
        for ticker in tickers:
            if risk_scores[ticker] > 0:
                risk_adjustment = float(max_risk / risk_scores[ticker])
            else:
                risk_adjustment = 1.0
            adjusted_weights[ticker] = float(base_convictions.get(ticker, 0.0)) * risk_adjustment
        
        weights_series = pd.Series(adjusted_weights)
        total = float(weights_series.sum())
        if total > 0.0:
            weights_series = weights_series / total
        return weights_series

    def _risk_based_book_weights(
        self,
        cov_full: pd.DataFrame,
        book_tickers: list[str],
        convictions: pd.Series,
    ) -> pd.Series:
        if not book_tickers:
            return pd.Series(dtype=float)

        sub = cov_full.loc[
            [t for t in book_tickers if t in cov_full.index],
            [t for t in book_tickers if t in cov_full.columns],
        ]
        if sub.empty:
            # Fallback to equal weights if covariance not available
            n = len(book_tickers)
            return pd.Series(np.full(n, 1.0 / n), index=book_tickers)

        # Base convictions (fallback to equal if all zeros)
        base = convictions.reindex(sub.index).fillna(0.0)
        if float(base.sum()) <= 0.0:
            base = pd.Series(np.full(len(sub.index), 1.0 / len(sub.index)), index=sub.index)

        # Use risk-based weights (vol and avg-corr aware)
        w = self.optimize_weights_risk_based(sub, base_convictions=base)

        # Guard: if optimizer returned degenerate weights
        if w is None or w.empty or not np.isfinite(w.values).all():
            n = len(sub.index)
            w = pd.Series(np.full(n, 1.0 / n), index=sub.index)

        # Reweight by convictions multiplicatively (light tilt), then renormalize
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
    # Test with the provided consumer staples portfolio
    print("Testing SimplePortfolioAllocator with consumer staples portfolio...")
    
    # Convert the provided portfolio format to conviction format
    portfolio_data = {
        "ACI": {"conviction": 0.6, "position": "long"},
        "ADM": {"conviction": 0.8, "position": "long"},
        "BJ": {"conviction": 0.6, "position": "long"},
        "CCEP": {"conviction": 0.6, "position": "long"},
        "CL": {"conviction": 0.6, "position": "long"},
        "GIS": {"conviction": 0.6, "position": "long"},
        "INGR": {"conviction": 0.8, "position": "long"},
        "IPAR": {"conviction": 0.6, "position": "long"},
        "KDP": {"conviction": 0.6, "position": "long"},
        "KMB": {"conviction": 0.8, "position": "long"},
        "KO": {"conviction": 0.8, "position": "long"},
        "KVUE": {"conviction": 0.6, "position": "long"},
        "LW": {"conviction": 0.6, "position": "long"},
        "MO": {"conviction": 0.8, "position": "long"},
        "PPC": {"conviction": 0.6, "position": "long"},
        "REYN": {"conviction": 0.8, "position": "long"},
        "RLX": {"conviction": 0.4, "position": "long"},
        "SAM": {"conviction": 0.4, "position": "long"},
        
        "CELH": {"conviction": 0.8, "position": "short"},
        "CLX": {"conviction": 0.7, "position": "short"},
        "COTY": {"conviction": 0.6, "position": "short"},
        "EL": {"conviction": 0.8, "position": "short"},
        "ELF": {"conviction": 0.8, "position": "short"},
        "FRPT": {"conviction": 0.8, "position": "short"},
        "HSY": {"conviction": 0.6, "position": "short"},
        "PFGC": {"conviction": 0.6, "position": "short"},
        "SFM": {"conviction": 0.6, "position": "short"},
        "STZ": {"conviction": 0.6, "position": "short"},
        "USFD": {"conviction": 0.6, "position": "short"},
        "UTZ": {"conviction": 0.6, "position": "short"},
        "VITL": {"conviction": 0.6, "position": "short"},
        "WDFC": {"conviction": 0.6, "position": "short"},
    }

    portfolio_data = canonical_portfolio(portfolio_data)
    
    try:
        # Create allocator with market-neutral target (net exposure = 0)
        allocator = SimplePortfolioAllocator(
            portfolio_dict=portfolio_data,
            target_annual_vol=0.17,
            target_gross_exposure=1.8,
            target_net_exposure=0.3,
            lookback_days=252  # 3 years of trading days
        )
        
        # Run allocation
        weights = allocator.allocate()

        print("Allocations:")
        for ticker, data in weights.items():
            print(f"{ticker}: {round(data['allocation']*100, 2)}% ({data['position']})")
        
        # Calculate portfolio metrics
        if weights:
            print(f"\nPortfolio Analysis:")
            
            # Get price and dividend data for total return calculations
            tickers = list(weights.keys())
            price_map = allocator._fetch_prices(tickers)
            
            # Convert structured weights back to simple weight dict for calculations
            simple_weights = {}
            for ticker, data in weights.items():
                weight = data['allocation']
                if data['position'] == 'short':
                    weight = -weight  # Make short positions negative
                simple_weights[ticker] = weight
            
            # Build dicts of closes and dividends
            ticker_closes: dict[str, pd.Series] = {}
            for t in tickers:
                s = price_map.get(t)
                if s is not None and not s.empty:
                    ticker_closes[t] = s.astype(float)
            
            if ticker_closes:
                from datetime import datetime as _dt
                end_dt = _dt.now(timezone.utc)
                start_dt = end_dt - timedelta(days=allocator.lookback_days)
                ticker_dividends: dict[str, pd.Series] = {}
                for t in ticker_closes.keys():
                    try:
                        divs = allocator.ds.get_dividends(t, start_dt, end_dt).series
                        ticker_dividends[t] = divs
                    except Exception:
                        ticker_dividends[t] = pd.Series(dtype=float)
                
                # Total-return portfolio (price + dividends), with daily renormalization to keep gross constant
                portfolio_total = PortfolioReturnsCalculator.weighted_total_returns(
                    ticker_dividends,
                    ticker_closes,
                    simple_weights,
                    dropna=False,
                    renormalize_each_day=True,
                    normalization="gross",
                ).dropna()
                
                if len(portfolio_total) > 0:
                    # Risk and performance metrics on total returns
                    annual_vol = RiskCalculator.annualized_volatility(portfolio_total)
                    annual_return = ReturnsCalculator.annualized_return(portfolio_total)
                    sharpe = PerformanceCalculator.sharpe_ratio(portfolio_total)
                    var_1d = RiskCalculator.historical_var(portfolio_total, confidence=0.99)
                    
                    # Exposures
                    gross_exposure = sum(abs(w) for w in simple_weights.values())
                    net_exposure = sum(simple_weights.values())
                    long_exposure = sum(w for w in simple_weights.values() if w > 0)
                    short_exposure = abs(sum(w for w in simple_weights.values() if w < 0))
                    
                    print(f"Annualized Volatility: {annual_vol:.4f} ({annual_vol*100:.2f}%)")
                    print(f"Annualized Total Return: {annual_return:.4f} ({annual_return*100:.2f}%)")
                    print(f"Sharpe Ratio: {sharpe:.4f}")
                    print(f"1-Day VaR (99%): {var_1d:.4f} ({var_1d*100:.2f}%)")
                    print(f"Gross Exposure: {gross_exposure:.4f}")
                    print(f"Net Exposure: {net_exposure:.4f}")
                    print(f"Long Exposure: {long_exposure:.4f}")
                    print(f"Short Exposure: {short_exposure:.4f}")
                    
                    # Drawdown from equity curve built on total returns
                    cumulative_returns = (1.0 + portfolio_total).cumprod()
                    max_dd = RiskCalculator.max_drawdown(cumulative_returns)
                    print(f"Max Drawdown: {max_dd:.4f} ({max_dd*100:.2f}%)")
                    
                    # Verification stats
                    print(f"\nVerification:")
                    print(f"Number of trading days: {len(portfolio_total)}")
                    print(f"Mean daily return: {portfolio_total.mean():.6f}")
                    print(f"Std daily return: {portfolio_total.std():.6f}")
                    print(f"Min daily return: {portfolio_total.min():.6f}")
                    print(f"Max daily return: {portfolio_total.max():.6f}")
                else:
                    print("No valid portfolio total returns calculated")
            else:
                print("Could not calculate portfolio metrics - insufficient price data")
        else:
            print("No allocations returned")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


