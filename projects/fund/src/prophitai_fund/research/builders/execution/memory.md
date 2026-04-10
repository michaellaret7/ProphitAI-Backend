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

