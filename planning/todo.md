## Plan: Portfolio Factor Style Exposures (Long/Short) — Proof of Concept

Context
- Goal: Compute portfolio-level style tilts for long/short equity portfolios using existing `backend/src/calculations_v2/` modules.
- Approach: Characteristic-based tilts via cross-sectional factor exposures per ticker, then portfolio aggregation; optional regression-based tilts when factor return series are available.

Todos
1) Define POC scope and function shape (no code saved yet)
   - Function: `portfolio_factor_tilts(weights: dict[str, float], factor: str, start: datetime, end: datetime) -> dict`
   - Factors supported: `value`, `growth`, `momentum`, `quality`, `volatility`.
   - Outputs: per-ticker exposure, and portfolio-level net/long/short tilts.

2) Per-ticker factor attributes and exposures (use calculations_v2)
   - Value: `ValueFactors(ticker).compute_attributes()` → `compose_value_exposure()` → `orthogonalize_value()`
   - Growth: `GrowthFactors(ticker).compute_attributes()` → `compose_growth_exposure()` → `orthogonalize_growth()`
   - Momentum: `MomentumFactors(price_series, dividends?, market?)` → `compute_attributes()` → `compose_momentum_exposure()` → `orthogonalize_momentum()`
   - Quality: `QualityFactors(ticker).compute_attributes()` → `compose_quality_exposure()` → `orthogonalize_quality()`
   - Volatility: `VolatilityFactors(price_series, SPY?)` → `compute_attributes()` → `compose_volatility_exposure()` → `orthogonalize_volatility()`
   - Data via `DataService`: prices/dividends/fundamentals; sector optional (falls back to global z-score if absent).

3) Portfolio aggregation
   - Build DataFrame of per-ticker exposures (column: `<factor>_exposure`).
   - Compute: net tilt = Σ w_i * exp_i; long tilt = Σ w_i+ / Σ w+ * exp_i; short tilt = Σ |w_i-| / Σ |w-| * exp_i (report signed as long − short and separately by leg).
   - Return dict with tilts and per-ticker table.

4) Optional regression-based variant (if factor returns available)
   - Use `PortfolioReturnsCalculator.weighted_daily_returns` for portfolio daily r.
   - Regress on factor return series (e.g., Fama–French/Carhart) via `statsmodels` OLS; report betas as alternative style exposures.

5) Example usage (manual test)
   - Use a small ticker set and signed weights; time window ≈ 252–504 trading days.

Review (to complete after implementation)
- Summarize decisions (data sources, sector handling, orthogonalization steps), sample outputs, and any caveats.

---

Review (done)
- Implemented `portfolio_factor_tilts` POC in `backend/testing/factor_tilt.py`.
- Uses `DataService` for prices/dividends/fundamentals; composes/orthogonalizes exposures via
  existing calculators per factor (Value/Growth/Momentum/Quality/Volatility).
- Aggregates net tilt (Σ w·exp), and leg averages for long and short.
- Momentum/Volatility require price windows; defaults to ~1y; SPY used where helpful.
- Caveats: sector-aware z-scoring uses global z when sector is absent; exposure columns must exist
  after composition; tickers lacking data are skipped (NaN exposures).

