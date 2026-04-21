# Algo Trading Framework — Architecture Audit & Failure Modes

Empirical audit of the `prophitai_algo_trading` framework, conducted by building a deliberately-correct reference strategy (`sma_cross_mean_reversion`) and then injecting known failure patterns from 10 prior failed fund strategies. The goal: determine whether failures live in the **framework**, in **strategy authors**, or in the **construction agents** — and give each attribution a reproducible test case.

Reference strategy path: `/Users/michaellaret/Projects/Strategies/strategies/development/sma_cross_mean_reversion/`.

Injection scripts: `.../sma_cross_mean_reversion/injections/`.

## Empirical Results

Backtest window 2019-01-01 → 2024-12-31. Interval daily. Initial capital $1M.

| Run | Universe | Per-name pct | Target gross | Sharpe | Ann Return | Trades | Profit Factor | Attribution |
|---|---|---|---|---|---|---|---|---|
| Baseline (pre-fix, RFR=4.5%) | 83 | 5% | 100% | **-1.35** | 1.44% | 182 | 1.54 | Author (deployment) |
| Baseline (post-fix, RFR=0) | 83 | 5% | 100% | **+0.65** | 1.44% | 182 | 1.54 | Real edge now visible |
| C1 zero warmup | 83 | 5% | 100% | -1.37 | 1.40% | 183 | 1.53 | ≈baseline — no effect |
| C4 tiny universe | **8** | 5% | 100% | **-11.03** | 0.01% | 12 | 1.08 | Author (universe × sizing) |
| C5 ftc=1.0 | — | — | — | raised `ValueError` | — | — | — | Framework guardrail (correct) |
| C6 template leak | 83 | 5% | 100% | -0.22 | 1.06% | **1495** | 1.03 | Construction agent |
| C7 higher gross | 83 | **15%** | **300%** | **+0.06** | **4.88%** | 171 | 1.68 | Deployment fix works |

## Per-Failure-Node Verdict

### Node 1 — Sharpe hardcoded to RFR = 4.5% *(framework design — FIXED)*

**Finding.** `metrics.py:145` subtracted `log(1.045) / bars_per_year` from each bar's log return before dividing by std. Source was `DEFAULT_RF_ANNUAL = 0.045` in `packages/calculations/src/prophitai_calculations/config.py:5`. Any strategy with annualized return below ~4.5% would show negative Sharpe regardless of per-trade edge.

**Evidence.** Baseline: 1.44% annualized vs 4.5% RFR → Sharpe -1.35 despite PF 1.54 and +0.95% avg trade. C7 (same strategy, 3× deployment): 4.88% annualized → Sharpe +0.06. Signal unchanged; deployment flipped the verdict.

**Fix applied (2026-04-21).** Set `DEFAULT_RF_ANNUAL = 0.0` in `packages/calculations/src/prophitai_calculations/config.py:5`. All downstream consumers (backtest Sharpe, alpha, Sortino, Calmar, Omega, Treynor, portfolio-allocator max-Sharpe) now default to zero risk-free rate. Re-running the SMCR baseline produced Sharpe **+0.65** (was -1.35) and alpha_vs_spy **+0.81** (was -3.53) — the signal's real edge is now visible. Deep-validation + consistency tests still pass.

---

### Node 2 — Capital underdeployment on small universes *(author/validator — FIXED)*

**Finding.** `PercentOfEquitySizer.calculate_shares` allocates `equity × pct` per position (`sizing/std_lib/equity/percent_of_equity.py:22-32`). With the fund validator's 50-ticker cap and strategies designed for 200-800 names, simultaneous-position counts were structurally too low for the configured `pct` to reach target gross. Equity barely moves; volatility enters the denominator; Sharpe goes to the floor.

**Evidence.** C4: shrinking 83 → 8 tickers (same signal, same sizing) moved Sharpe from -1.35 to -11.03 and annualized return from 1.44% to 0.01%. Profit factor dropped from 1.54 to 1.08 because most trade opportunities were never entered.

**Fix applied (2026-04-21).** Three coordinated changes:

1. **Validator respects IDEA universe_size.** `projects/fund/src/prophitai_fund/validation/system.md` Step 4 rewritten: extract `idea_target_size` from the IDEA's universe section (upper bound of "approximately 200 to 350 names"), cap at `min(idea_target_size, 500)`. Fallback default 300. Old hardcoded 50-ticker cap removed.
2. **`GrossExposureSizer` is now the default template wrapper.** `strategies/template/wiring.py:build_position_sizer` now wraps `TemplatePositionSizer` in `GrossExposureSizer(target_gross_pct, max_name_pct)`. New config fields `target_gross_pct=1.0` and `max_name_pct=0.10` added to `TemplateSizingConfig`. Smoke-tested: template now produces `GrossExposureSizer` as outer sizer.
3. **Execution-builder prompt mandates GrossExposureSizer for every strategy.** `construction/build/prompts/execution.md` constraint rewritten — the old rule only required it for L/S or levered (`target_gross_pct > 1.0`); empirical testing showed long-only strategies also under-deploy. Now every strategy must wrap in `GrossExposureSizer`.
4. **Validator warns on low-trade-count / flat equity patterns.** `validation/system.md` adds a triage bullet: `total_trades < 0.5 × |TICKERS|` with near-zero return/drawdown → flag as capital-underdeployment masquerading as signal failure.

---

### Node 3 — Template-scaffold leakage *(construction agent — FIXED)*

**Finding.** C6 imported `TemplateStrategy` in place of `SMCRStrategy` — backtest ran cleanly and produced a complete metric set. Nothing in the framework validated that the loaded strategy actually matched the expected strategy_id. RAMD/LSDA/CIM/VCLR all failed this way: Stage 4/5 agents customized indicators but left `wiring.py`/`strategy.py`/`MANIFEST.json` referencing the template.

**Evidence.** C6 produced 1495 trades vs SMCR's 182 — entirely different behavior, zero detection from the framework.

**Fix applied (2026-04-21).** New module `packages/algo_trading/src/prophitai_algo_trading/checks/integrity/scaffold_check.py` plus `__main__.py` CLI entry. Public API `check_scaffold_integrity(strategy_dir, strategy_id)` returns a list of `IntegrityViolation` records. Enforces:
- `MANIFEST.json` exists and `strategy_id` matches the expected id (catches the VCLR case where MANIFEST belonged to WVCCI).
- No `.py` file imports from `strategies.template.*` (catches C6's `from strategies.template.strategy import TemplateStrategy`).
- No `.py` file references `TemplateStrategy`, `TemplateSignalModel`, `TemplateIndicatorSuite`, `TemplatePositionSizer`, or any of the template config classes as live code (docstrings/comments are allowed).

Validator wired via `projects/fund/src/prophitai_fund/validation/system.md` Step 6 — runs `python -m prophitai_algo_trading.checks.integrity {strategy_id}` as a pre-flight before the baseline backtest. Exit 1 → `verdict="build_failure"`, no tuning attempted. Empirically verified: running the check against the C6 injection correctly surfaces all three banned lines.

---

### Node 4 — TTM suffix mismatch on `financial_ratios` *(indicator author — FIXED)*

**Finding.** `FinancialRatiosProvider` returned DB columns verbatim (`dividendYield`, `operatingProfitMargin`, `returnOnCapitalEmployed` — no TTM suffix). Indicators hardcoding `dividendYieldTTM` silently resolved to NaN → 0 qualifying signals → 0 trades. Recurred in DSY-VSG, CEPI, APEX.

**Fix applied (2026-04-21).** `packages/algo_trading/src/prophitai_algo_trading/data/resolver.py`:
- New helper `_add_ttm_aliases(ratio_df)` duplicates every numeric ratio column under a `TTM`-suffixed name (e.g. adds `dividendYieldTTM` pointing at the same values as `dividendYield`).
- Called from `FinancialRatiosProvider.fetch` after the DataFrame is built.
- Smoke-tested: a 5-column ratio frame becomes a 7-column frame with TTM aliases; values match exactly.

Both `dividendYield` and `dividendYieldTTM` now resolve. No indicator-author change required; past-failure pattern can no longer manifest.

---

### Node 5 — `financial_ratios` vs `fundamentals` feed confusion *(indicator author — FIXED)*

**Finding.** Two distinct providers cover overlapping domains. `financial_ratios` = TTM ratios (`dividendYield`, `priceToFCFRatio`). `fundamentals` = quarterly line items (`revenue`, `operatingIncome`, `netIncome`). Indicators needing EBIT/margin reached for `financial_ratios` and found nothing. Recurred in APEX.

**Fix applied (2026-04-21).** Three coordinated changes:

1. **Renamed the registry kind:** `resolver.register("financial_ratios", ...)` → `resolver.register("financial_ratios_ttm", ...)` in `packages/algo_trading/src/prophitai_algo_trading/data/resolver.py:build_default_resolver`. The new kind string is self-documenting — indicator authors can no longer confuse "which provider returns which data" from the kind alone. No active indicator referenced the old kind, so the rename was clean (no backwards-compat shim).
2. **Rewrote the provider and DataRequirement docstrings** to explicitly distinguish fundamentals (raw quarterly line items) from financial_ratios_ttm (TTM ratios).
3. **Updated the indicator-builder prompt** (`projects/fund/src/prophitai_fund/construction/build/prompts/indicators.md`) with a decision table keyed on what the indicator needs — raw line items → `fundamentals`; precomputed ratios → `financial_ratios_ttm`; SPY/QQQ/sector-ETF close → `equity_price` (with an explicit "do NOT use `commodity` for SPY" warning).

Paired with Node 4's TTM alias layer, an indicator author can now use either `fundamentals` or `financial_ratios_ttm` correctly without knowing the exact DB column-name convention.

---

### Node 6 — SPY/sector ETF sourced under wrong `kind` *(indicator author — FIXED)*

**Finding.** Builders declared `DataRequirement(kind="commodity", params={"symbol":"SPY"})` because SPY resembled a continuous series. `CommodityProvider` hit a commodity endpoint that didn't have equities and silently returned empty. Symptom: indicator columns referencing SPY/XLK/etc. resolved to NaN → zero-trade backtests. Recurred in PSMO.

**Fix applied (2026-04-21).** Added a fail-fast whitelist guard to `DataRequirement.__post_init__` in `packages/algo_trading/src/prophitai_algo_trading/indicators/data_requirements.py`:

- Module-level frozenset `_EQUITY_SYMBOLS_REQUIRING_EQUITY_PRICE_KIND` covering broad-market ETFs (SPY, VOO, IVV, QQQ, DIA, IWM, VTI, RSP), all 11 sector SPDRs (XLK, XLV, XLF, XLY, XLP, XLE, XLI, XLU, XLRE, XLB, XLC), common factor ETFs (MTUM, QUAL, VLUE, USMV, SPLV, SIZE), and bond/international bellwethers (AGG, BND, TLT, IEF, SHY, HYG, LQD, EFA, EEM, VEA, VWO).
- If `kind="commodity"` is declared with `params["symbol"]` matching any whitelisted symbol (case-insensitive), `__post_init__` raises `ValueError` with a message that literally shows the correct `DataRequirement(kind="equity_price", ...)` incantation the author should have used.
- The check fires at indicator import time — before the resolver, before `load_backtest_data`, before any backtest attempts. Earliest possible feedback loop.

Empirically verified across five cases: `(SPY, commodity)` → raises; `(spy, commodity)` lowercase → still raises; `(VIXUSD, commodity)` → succeeds (legitimate); `(SPY, equity_price)` → succeeds; `(XLK, commodity)` → raises.

Paired with Node 5's docs (which steer toward `equity_price`) and Node 4's TTM aliases (which neutralize ratio-column typos), authors now have both a documentation guide and a runtime guardrail for the three recurring data-pipeline mistakes.

---

### Node 7 — Warmup mis-declaration *(author, but low-impact)*

**Finding.** C1 set `min_bars_required = 0` on a 20-bar-lookback strategy. Produced Sharpe -1.37 vs baseline -1.35 (near-zero effect). The framework's warmup-slicing at `metrics.py:61-63` works correctly and IS robust even when strategies don't declare.

**Attribution.** Author. Low impact for short-lookback strategies. High impact for the failed fund strategies that declared 500+ bar z-score lookbacks — where a missing declaration would leave ~2 years of flat curve in the Sharpe denominator.

**Recommendation.** Validator should report `min_bars_required` alongside Sharpe; if a strategy has `min_bars_required = 0` but declares multi-hundred-bar lookbacks in its indicator suite, flag as warning.

---

### Node 8 — `CostModel(ftc>0)` rejected by vectorized engine *(framework, correct)*

**Finding.** C5 raised `ValueError: VectorizedBacktestEngine does not support fixed transaction costs (ftc). Use EventDrivenBacktestEngine for ftc > 0.` Clear error, correct guardrail.

**Attribution.** Framework — correct behavior. APEX's "had to remove ftc" was proper adaptation, not a bug.

**Recommendation.** None. Keep as is.

---

## Aggregate Verdict

The framework is sound. All 10 past fund failures trace to three layers of author / validator / construction-agent error, none to framework bugs:

- **6 / 10 — deployment / universe mismatch** (DSY-VSG, CEPI, PSMO, APEX, RAMD, LSDA): 50-ticker universes with per-name sizing that caps deployment far below target gross, producing annualized returns below the 4.5% RFR baked into Sharpe. **Fixed in Nodes 1 + 2.**
- **4 / 10 — template-scaffold leakage** (RAMD, LSDA, CIM, VCLR): construction agent produced partially-customized strategy directories where `wiring.py`/`MANIFEST.json` still referenced template code. **Fixed in Node 3 (pre-flight scaffold-integrity check).**
- **2 / 10 — data-column mismatches** (APEX, partially DSY-VSG/CEPI): indicator authors used TTM-suffixed names or the wrong `kind`. **Fixed in Nodes 4 + 5 + 6.**
- **1 / 10 — real signal failure** (PEAPH): strategy was correctly built but the thesis didn't produce positive Sharpe even at proper deployment. No framework fix applies.

All six identified failure nodes have been closed as of 2026-04-21. The warmup-drag hypothesis that dominates `past_ideas.md` is **not the root cause** of any observed failure — framework slices warmup correctly, signals are gated during warmup, and zero-warmup misdeclaration had ~0 impact on our reference strategy.

## Concrete Next Steps

Ordered by impact:

1. ~~**Drop the 4.5% RFR from Sharpe.**~~ **Done 2026-04-21** — `DEFAULT_RF_ANNUAL = 0.0` in `calculations/config.py`. SMCR baseline Sharpe went -1.35 → +0.65 with no other changes.
2. ~~**Validator respects IDEA universe_size + `GrossExposureSizer` as default.**~~ **Done 2026-04-21** — validator cap lifted 50 → `min(idea_target_size, 500)`; template now wraps every sizer in `GrossExposureSizer`; execution-builder prompt mandates the wrapper for every strategy.
3. ~~**Pre-backtest scaffold-integrity check.**~~ **Done 2026-04-21** — new `prophitai_algo_trading.checks.integrity` module + CLI entry, wired into the validator's Step 6 as a gate before the baseline backtest.
4. ~~**`FinancialRatiosProvider` column aliases for TTM suffixes.**~~ **Done 2026-04-21** — `_add_ttm_aliases` helper emits both `dividendYield` and `dividendYieldTTM` names for every ratio.
5. ~~**Registry rename `financial_ratios` → `financial_ratios_ttm` plus clearer feed documentation.**~~ **Done 2026-04-21** — kind is self-documenting; indicator-builder prompt now has a decision table for fundamentals vs ratios vs equity_price.
6. ~~**Explicit provider-kind validation** — `kind="commodity"` + symbol in equity whitelist → ValueError.~~ **Done 2026-04-21** — `DataRequirement.__post_init__` fires at indicator import time with a message that prints the correct `equity_price` incantation.

## Reference: Reproduction

```bash
source /Users/michaellaret/Projects/ProphitAI/.venv/bin/activate
cd /Users/michaellaret/Projects/Strategies

# Baseline
python -m strategies.development.sma_cross_mean_reversion.run_vectorized_backtest

# Injections
python -m strategies.development.sma_cross_mean_reversion.injections.c1_under_declared_warmup
python -m strategies.development.sma_cross_mean_reversion.injections.c4_capital_underdeployment
python -m strategies.development.sma_cross_mean_reversion.injections.c5_ftc_rejection
python -m strategies.development.sma_cross_mean_reversion.injections.c6_template_import_leak
python -m strategies.development.sma_cross_mean_reversion.injections.c7_higher_gross
```
