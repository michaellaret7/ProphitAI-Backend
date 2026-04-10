---
date: 2026-04-10
title: EarningsBlackoutControl uses days kwarg (int)
topic: risk_control_patterns
---
EarningsBlackoutControl.__init__ takes `days: int` as first arg plus optional `earnings_dates: dict`. NOT blackout_days or window. Confirmed from source.

t.py.

---
date: 2026-04-10
title: RegimeHaltControl allowed_long_regimes must be tuple not list
topic: risk_control_patterns
---
RegimeHaltControl.__init__ signature: regime_column: str, allowed_long_regimes: tuple[str|int, ...] = (), allowed_short_regimes: tuple[str|int, ...] = (), force_exit_on_halt: bool = True. Pass tuples, not lists. Confirmed from source.

---
date: 2026-04-10
title: VectorizedBacktestEngine has NO risk_controls parameter
topic: wiring_gotchas
---
VectorizedBacktestEngine.__init__ accepts: strategy, initial_capital, cost_model, sizer, warmup_bars, max_positions — NO risk_controls. Only EventDrivenBacktestEngine and LiveRunner accept risk_controls. Confirmed from source.

---
date: 2026-04-10
title: AQM52 sizing hints: score_h52 and market_state_regime go to raw_features
topic: sizing_patterns
---
In AQM52Strategy.get_sizing_hints(), score_h52 and market_state_regime are added to hints dict but NOT standard EntryCandidate fields — they fall through to candidate.raw_features (the residual dict in build_entry_candidate). Custom sizer must read them from candidate.raw_features, not top-level candidate fields.

---
date: 2026-04-10
title: EntryCandidate.volatility maps from realized_vol via BaseStrategy._first_finite
topic: sizing_patterns
---
BaseStrategy.get_sizing_hints() auto-populates volatility via _first_finite(row, "volatility", "realized_vol", ...) — so realized_vol column IS picked up into candidate.volatility automatically. Custom sizing hints in AQM52Strategy override to also add score_h52 and market_state_regime to raw_features.

---
date: 2026-04-10
title: RegimeHaltControl conservative missing-column behavior
topic: risk_control_patterns
---
When building a custom RegimeHaltControl, block entries (return True) when the regime column is missing OR when the regime value is NaN — not just when the regime string is not in the allowed set. Missing column should be treated as unknown/dangerous regime. A code reviewer will flag the permissive (return False) path as a correctness error.

---
date: 2026-04-10
title: Custom sizer: always guard volatility for NaN/non-finite before dividing
topic: sizing_patterns
---
When implementing vol-scaling in a custom BasePositionSizer, always check math.isfinite(realized_vol) AND realized_vol > 0 before computing target_volatility / realized_vol. Also wrap the float() cast in try/except (TypeError, ValueError). Fallback to vol_scale=1.0 (neutral) on any bad data. Reviewers flag missing finite check as an error.

---
date: 2026-04-10
title: pytest not in venv; install to site-packages with pip3 --target
topic: verification_failures
---
In sandbox iyqhoe5gcufg6tz7ilrk9, the venv has no pip. pytest must be installed system-wide via pip3 then copied to the venv site-packages with: pip3 install pytest --target=/home/user/strategies/.venv/lib/python3.13/site-packages/. After that, python3 -m pytest works. Run test files directly with python3 -m pytest test_file.py, not via exec paths.

