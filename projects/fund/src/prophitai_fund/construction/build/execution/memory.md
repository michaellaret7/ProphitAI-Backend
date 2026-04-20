---
date: 2026-04-10
title: EarningsBlackoutControl uses days kwarg (int)
topic: risk_control_patterns
---
EarningsBlackoutControl.__init__ takes days: int as first arg plus optional earnings_dates: dict. NOT blackout_days or window.

---
date: 2026-04-10
title: RegimeHaltControl allowed_long_regimes must be tuple not list
topic: risk_control_patterns
---
RegimeHaltControl.__init__ signature: regime_column: str, allowed_long_regimes: tuple[str|int, ...] = (), allowed_short_regimes: tuple[str|int, ...] = (), force_exit_on_halt: bool = True. Pass tuples, not lists.

---
date: 2026-04-10
title: VectorizedBacktestEngine has NO risk_controls parameter
topic: wiring_gotchas
---
VectorizedBacktestEngine.__init__ accepts strategy, initial_capital, cost_model, sizer, warmup_bars, max_positions — NO risk_controls. Only EventDrivenBacktestEngine and LiveRunner accept risk_controls. The vectorized runner must not pass risk_controls to the constructor.

---
date: 2026-04-10
title: Non-standard sizing hints fall through to candidate.raw_features
topic: sizing_patterns
---
get_sizing_hints() hints that are not standard EntryCandidate fields (volatility, regime, direction) fall through to candidate.raw_features (the residual dict in build_entry_candidate). Custom sizers must read these from candidate.raw_features, not top-level candidate fields. Examples of hints that route to raw_features: score, vix_sizing_scale, market_state_scale, ticker_sector.

---
date: 2026-04-10
title: EntryCandidate.volatility maps from realized_vol automatically
topic: sizing_patterns
---
BaseStrategy.get_sizing_hints() auto-populates candidate.volatility via _first_finite(row, 'volatility', 'realized_vol', 'close_to_close_vol_20', 'parkinson_vol_20'), so a realized_vol column is picked up into candidate.volatility automatically. Custom get_sizing_hints() overrides should add non-standard hints to the raw_features dict, not redefine volatility routing.

---
date: 2026-04-10
title: RegimeHaltControl: missing column should block entries, not pass through
topic: risk_control_patterns
---
When building a custom RegimeHaltControl, block entries (return True) when the regime column is missing OR when the regime value is NaN — not just when the regime string is not in the allowed set. Missing column should be treated as unknown/dangerous regime. Code reviewers flag the permissive (return False on missing column) path as a correctness error.

---
date: 2026-04-10
title: Custom sizer: guard volatility for NaN/non-finite before dividing
topic: sizing_patterns
---
When implementing vol scaling in a custom BasePositionSizer, always check math.isfinite(realized_vol) AND realized_vol > 0 before computing target_volatility / realized_vol. Wrap the float() cast in try/except (TypeError, ValueError). Fallback to vol_scale=1.0 (neutral) on any bad data. Reviewers flag missing finite checks as errors.

---
date: 2026-04-10
title: pytest installation into venv: pip3 --target into site-packages
topic: verification_failures
---
When the sandbox venv has no pip, install pytest system-wide via pip3 then copy to the venv site-packages with pip3 install pytest --target=/home/user/strategies/.venv/lib/python3.13/site-packages/. After that, python3 -m pytest works. Run test files directly with python3 -m pytest test_file.py, not via exec paths.

---
date: 2026-04-14
title: SectorConcentrationControl: include incoming notional in cap check using per-name cap
topic: risk_control_patterns
---
should_block_entry only receives price (not proposed shares). The 1-share price estimate underestimates actual trade size — a trade from 24% to 26% can pass through a >= cap check. Use projected_pct = (existing_sector_notional + max(per_name_cap_pct * equity, price)) / equity > cap, where per_name_cap_pct matches manifest config_defaults.sizing.max_single_name_pct (e.g. 0.035). This gives a conservative upper-bound. Code reviewer flags the 1-share-only estimate as an error.

---
date: 2026-04-14
title: VIX / regime scale hints live in candidate.raw_features, not candidate.volatility
topic: sizing_patterns
---
get_sizing_hints() overrides that publish regime scale values (vix_scale, vix_sizing_scale, market_state_scale) put them into the hints dict, which populates candidate.raw_features — NOT candidate.volatility, candidate.regime, or any other top-level field. Custom sizers must read via: raw_features = getattr(candidate, 'raw_features', None); if isinstance(raw_features, dict): vix_scale = raw_features.get('vix_sizing_scale'). Always guard with math.isfinite() before using. Halt (return 0 shares) when vix_scale == 0.0.

---
date: 2026-04-14
title: Interval.from_string accepts 'daily' not '1d'
topic: wiring_gotchas
---
get_price_data_df() calls Interval.from_string(interval) which only accepts: 'daily', 'hourly', '30min', '15min', '5min', '1min'. Using '1d' or '1h' raises ValueError at runtime. Always use 'daily' (not '1d') and 'hourly' (not '1h') in runner scripts, wiring.py load_backtest_data(), and config interval fields.

---
date: 2026-04-16
title: build_live_runner must reuse components.cost_model, not rebuild it
topic: wiring_gotchas
---
When building build_live_runner() in wiring.py, always pass components.cost_model directly to LiveRunner instead of calling _build_cost_model() again. Rebuilding creates a second source of truth that can silently diverge. Pattern: components = build_X_engine(...); return LiveRunner(..., cost_model=components.cost_model, ...).

---
date: 2026-04-16
title: Never define should_block_entry twice in a RiskControl — F811 duplicate
topic: risk_control_patterns
---
When building a custom RiskControl that needs to update internal cache during should_block_entry, implement the full logic in a single definition. If you draft a stub then override it, ruff catches the redefinition as F811. Pattern: one should_block_entry method that both updates internal state (sector cache, claims counter) and returns the bool result.

---
date: 2026-04-16
title: Macro-counter controls: update state in should_block_entry, not on_bar
topic: risk_control_patterns
---
When building a macro-counter custom RiskControl (claims threshold counting, consecutive-weeks triggers), update internal state inside should_block_entry (not on_bar). Reason: should_block_entry is guaranteed to be called for every candidate entry bar — on_bar is not reliably called for all tickers. Use a _last_update_timestamp guard to prevent double-counting when multiple tickers share the same bar. Pattern: read value from df, check timestamp != self._last_update_timestamp before calling self.update_macro_state(value), then return self._halted.

---
date: 2026-04-16
title: SectorConcentrationControl: ticker_sector_cache must be instance-level dict
topic: risk_control_patterns
---
The cache dict MUST be instance-level (initialized in __init__ as self._ticker_sector_cache = {}), NOT class-level. Class-level mutable dicts pollute state across separate backtests, live sessions, and test runs. Code reviewer flags class-level mutable dicts as correctness warnings.

---
date: 2026-04-17
title: PortfolioTracker correct import path: execution.portfolio_tracker
topic: risk_control_patterns
---
PortfolioTracker imports from prophitai_algo_trading.execution.portfolio_tracker NOT prophitai_algo_trading.portfolio.tracker. The latter module does not exist. Confirmed from risk/base.py and template custom_control.py.

---
date: 2026-04-17
title: Alpaca broker correct import path: broker not brokers (singular)
topic: wiring_gotchas
---
Alpaca class imports from prophitai_algo_trading.broker.alpaca (singular 'broker') NOT prophitai_algo_trading.brokers.alpaca (plural). Template wiring.py uses the singular form. Common mistake to write 'brokers' — always use 'broker'.

---
date: 2026-04-17
title: Runner scripts: build components once, construct engine inline
topic: runner_patterns
---
Runner scripts should call build_X_engine() once to get EngineComponents, then pass components.* directly to the engine constructor inline (EventDrivenBacktestEngine(...) / VectorizedBacktestEngine(...)). Do NOT call both build_X_engine() for data loading AND a separate build_event_backtest_engine() — that creates two independent instances (double-construction). Pattern: components = build_X_engine(); data = load_backtest_data(strategy=components.strategy); engine = EventDrivenBacktestEngine(strategy=components.strategy, ..., risk_controls=components.risk_controls).

---
date: 2026-04-17
title: BasePositionSizer has no __init__ — never call super().__init__() with kwargs
topic: sizing_patterns
---
BasePositionSizer is an ABC with no __init__ defined. Custom sizers must NOT call super().__init__(cost_model=...) — that raises TypeError: object.__init__() takes exactly one argument. Store cost_model directly: self._cost_model = cost_model or CostModel(). Confirmed from template sizing/policy.py pattern.

---
date: 2026-04-17
title: PortfolioTracker.build_portfolio_context() is the correct API for equity/positions
topic: risk_control_patterns
---
In custom RiskControl.should_block_entry(), use portfolio.build_portfolio_context() to get a PortfolioContext snapshot with equity, cash, positions, latest_prices. Do NOT use portfolio.context (property does not exist) or portfolio._positions (private). The PortfolioContext type lives at prophitai_algo_trading.execution.models.PortfolioContext.

---
date: 2026-04-17
title: Wiring MUST import strategy/config/suite from the current strategy's directory
topic: wiring_gotchas
---
wiring.py for the strategy at strategies/development/<strategy_id>/ MUST import config, strategy, and indicator suite from that SAME directory — never from another strategy's directory. Pattern: from strategies.development.<strategy_id>.config import <Strategy>Config; from strategies.development.<strategy_id>.strategy import <Strategy>Strategy; from strategies.development.<strategy_id>.indicators import <Strategy>IndicatorSuite. If the upstream Signal+Strategy Build Result's file_path points to a different strategy's directory or its class_name is another strategy's class, that is a critical build failure — HALT and re-run the upstream builder. Do NOT import the other strategy's classes as a workaround.

---
date: 2026-04-17
title: raw_features guard: use getattr + isinstance(dict) before .get()
topic: sizing_patterns
---
When reading custom sizing hints from candidate.raw_features, guard with: raw_features = getattr(candidate, 'raw_features', None); if isinstance(raw_features, dict): ... This prevents AttributeError if raw_features is None or not dict-like. The dataclass defines it as dict with default_factory=dict, but defensive coding prevents runtime surprises from None candidates.

---
date: 2026-04-17
title: SectorConcentrationControl: pre-populate cache from ticker_sector_map in __init__
topic: risk_control_patterns
---
When building a ticker-sector caching control, pre-populate _ticker_sector_cache from the constructor's ticker_sector_map parameter: self._ticker_sector_cache = dict(ticker_sector_map or {}). This ensures held positions are classified correctly even before _get_sector() is called for them. Without this, the loop over portfolio positions uses self._ticker_sector_cache.get(sym, '__UNKNOWN__'), misclassifies mapped tickers that haven't been looked up yet, understates sector exposure, and potentially allows entries that should be blocked.

---
date: 2026-04-17
title: Stored-but-unused RiskControl params: add clarifying comment to prevent reviewer flags
topic: risk_control_patterns
---
When a risk control's constructor param (e.g. reschedule_threshold_days) is encoded into a binary flag by the upstream indicator rather than being re-evaluated in the control, keep the param for API clarity but add a comment: 'Upstream indicator encodes this threshold into the binary flag — this param is stored for documentation and future use, not re-evaluated here.' Code reviewers flag stored-but-unused params as dead configuration; the comment prevents the finding.
---
date: 2026-04-17
title: Test manifests must mirror production risk-control params explicitly
topic: risk_control_patterns
---
When writing contract test manifests (RiskControlContract, full suite), always instantiate custom controls with the same explicit kwargs as production defaults.py — not relying on class defaults. Code reviewer flags implicit default reliance as a warning. Pattern: test SectorConcentrationControl(max_sector_gross_pct=0.25, sector_column="sector_code", per_name_cap_pct=0.0167) matching defaults.py exactly.

---
date: 2026-04-18
title: EqualWeightPositionSizer: use open_count + 1 for post-entry target weight
topic: sizing_patterns
---
When implementing equal-weight dynamic sizing (pct = 1/N), use open_count = max(context.open_position_count + 1, 1) — the +1 targets the post-entry equal-weight allocation across all holdings including the incoming name. Using open_position_count without +1 sizes the NEW position using the CURRENT count, which overestimates the target weight during ramp-up. The cap min(dyn_pct, max_name_pct) handles the 2.5% per-name hard limit without needing the base_equity_pct in the formula.

---
date: 2026-04-18
title: SectorConcentrationControl: _resolve_sector_for_held helper prevents reviewer flags
topic: risk_control_patterns
---
When _compute_sector_exposure iterates portfolio holdings and classifies sectors, extract the per-symbol lookup into a _resolve_sector_for_held(sym) helper method. This makes the conservative classification decision explicit and documentable (unknown symbols excluded from sector gross but included in total_gross — conservative direction for a blocking control). Reviewers flag direct dict.get(sym, '__UNKNOWN__') inline calls as "never attempts to resolve" — the named helper makes the deliberate design choice clear.

---
date: 2026-04-20
title: has_columns() is variadic *args, NOT list arg
topic: risk_control_patterns
---
RiskControl.has_columns(df, *columns: str) is variadic — pass individual string args, NOT a list. Calling has_columns(df, [col]) passes a list as a single arg, causing TypeError: unhashable type 'list' in pandas __contains__. Correct: self.has_columns(df, self._column_name). Wrong: self.has_columns(df, [self._column_name]).

