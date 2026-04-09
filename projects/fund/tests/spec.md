Now I'll perform the complete translation with full self-validation. Let me reason through the manifest systematically before writing the final JSON.

**Key design decisions from the framework analysis:**

1. **Rolling 252-day max** → No std_lib equivalent → Custom `RollingMaxIndicator`
2. **6-month return** → `RateOfChangeIndicator(window=126)` from std_lib
3. **Realized vol for vol-scaling** → Custom `RealizedVolIndicator` with `output_column="realized_vol"` (exactly this name so `get_sizing_hints()` auto-populates `candidate.volatility`)
4. **FCF Conversion** → Custom `FcfConversionIndicator` (fundamental data join)
5. **Market state regime** → Custom `MarketStateIndicator` (benchmark return based)
6. **SMA 200 trend gate** → `SimpleMovingAverageIndicator(window=200)` from std_lib
7. **Cross-sectional ranking** → Framework gap: simplified to absolute `h52_ratio >= 0.80` threshold (documented)
8. **Sizing** → Custom `AQM52PositionSizer` combining vol-scaling + conviction boost + regime multiplier
9. **Risk controls** → `StopLossExitControl` + `EarningsBlackoutControl` (std_lib) + Custom `RegimeHaltControl` + Custom `QualityDecayExitControl`
10. **`market_state_regime` → `candidate.regime`** → Requires `get_sizing_hints()` override in strategy class (not auto-picked since column isn't named `"regime"`)

**Self-validation checklist completed:**
- ✅ All `required_columns` resolve to indicator `output_columns` or `derived_features`
- ✅ All signal conditions reference columns in `required_columns` or OHLCV
- ✅ All `sizing_hints` columns (`realized_vol`, `market_state_regime`, `score_h52`) exist
- ✅ Indicator order respects dependencies (RollingMax before h52_ratio derived feature)
- ✅ `min_bars_required = 252` ≥ max warmup (252) across all indicators
- ✅ All std_lib params verified against actual constructor signatures
- ✅ All custom `calculation` descriptions are implementation-complete

---

```json
{
  "strategy_id": "AQM-52",
  "strategy_name": "52-Week Anchor Momentum with Cash Quality Gate",
  "version": "1.0.0",
  "description": "Exploits the 52-week high anchoring bias (George & Hwang 2004): stocks with high proximity to their annual high exhibit predictable price drift as behavioral resistance is gradually overcome. A mandatory FCF conversion gate (Op CF TTM / Net Income TTM > 1.0) removes distressed names whose proximity may reflect speculative momentum rather than fundamental underreaction. Volatility scaling (Barroso & Santa-Clara 2015) targets constant portfolio variance, reducing crash-risk kurtosis. Long-only, monthly rebalance, US mid/large-cap equity universe.",

  "indicators": [
    {
      "id": "rolling_max_252",
      "class": "RollingMaxIndicator",
      "is_custom": true,
      "file": "strategies/development/aqm_52/indicators/custom_indicator.py",
      "params": {
        "window": 252,
        "source_column": "close",
        "output_column": "rolling_max_252"
      },
      "output_columns": ["rolling_max_252"],
      "warmup_bars": 252,
      "calculation": "Compute the rolling maximum of the close price series over the past `window` bars: df['rolling_max_252'] = df['close'].rolling(window=252, min_periods=252).max(). Returns NaN until exactly 252 bars of close data are available. This is the 52-week high reference price used in the proximity ratio numerator. Use close (not high) per George & Hwang (2004) methodology."
    },
    {
      "id": "roc_126",
      "class": "RateOfChangeIndicator",
      "is_custom": false,
      "registry_key": "roc",
      "params": {
        "window": 126,
        "skip_recent": 0,
        "source_column": "close",
        "output_column": "roc_126"
      },
      "output_columns": ["roc_126"],
      "warmup_bars": 126,
      "description": "6-month (126 trading-day) cumulative return. Used as the momentum confirmation gate: roc_126 > 0 confirms sustained uptrend before entry. skip_recent=0 because AQM-52 explicitly wants recent return included (not a 12-1 skip-month factor)."
    },
    {
      "id": "realized_vol_126",
      "class": "RealizedVolIndicator",
      "is_custom": true,
      "file": "strategies/development/aqm_52/indicators/custom_indicator.py",
      "params": {
        "window": 126,
        "source_column": "close",
        "output_column": "realized_vol",
        "annualize": true,
        "trading_days_per_year": 252
      },
      "output_columns": ["realized_vol"],
      "warmup_bars": 127,
      "calculation": "Compute annualized 6-month realized volatility: df['realized_vol'] = df['close'].pct_change().rolling(window=126, min_periods=126).std() * (252 ** 0.5). CRITICAL: the output column MUST be named exactly 'realized_vol' so that BaseStrategy.get_sizing_hints() auto-populates candidate.volatility, which AQM52PositionSizer reads for the Barroso-Santa-Clara vol-scaling calculation. Returns NaN for first 127 bars."
    },
    {
      "id": "fcf_conversion",
      "class": "FcfConversionIndicator",
      "is_custom": true,
      "file": "strategies/development/aqm_52/indicators/custom_indicator.py",
      "params": {
        "output_column": "fcf_conversion_ttm",
        "staleness_limit_days": 45
      },
      "output_columns": ["fcf_conversion_ttm"],
      "warmup_bars": 0,
      "calculation": "Join point-in-time quarterly fundamental data into the OHLCV DataFrame to produce a daily-frequency FCF conversion ratio series. Calculation: fcf_conversion_ttm = operating_cash_flow_ttm / net_income_ttm. Point-in-time construction: for each calendar date, use only the most recently reported quarterly data whose fiscal quarter-end date is at least 45 calendar days in the past (to model the SEC filing lag). If no qualifying fundamental data exists within the last 45 days from the most recent report, output NaN. Forward-fill the ratio value from the filing date until the next qualifying filing or until staleness is exceeded. Fundamental data must be passed into calculate() via df.attrs['fundamentals'] as a DataFrame with columns ['date', 'operating_cash_flow_ttm', 'net_income_ttm'], indexed by fiscal period end date. When net_income_ttm <= 0, output NaN (universe screen requires net_income_ttm > 0 but defensive guard is required)."
    },
    {
      "id": "market_state",
      "class": "MarketStateIndicator",
      "is_custom": true,
      "file": "strategies/development/aqm_52/indicators/custom_indicator.py",
      "params": {
        "window": 252,
        "return_output_column": "market_return_252",
        "regime_output_column": "market_state_regime",
        "down_moderate_threshold": -0.15,
        "down_severe_threshold": -0.25
      },
      "output_columns": ["market_return_252", "market_state_regime"],
      "warmup_bars": 252,
      "calculation": "Compute trailing 252-bar (12-month) price return and classify into three regime strings. Return: df['market_return_252'] = df['benchmark_close'].pct_change(252). Regime classification: 'up' when market_return_252 >= 0.0; 'down_moderate' when market_return_252 < 0 and >= down_severe_threshold (-0.25); 'down_severe' when market_return_252 < down_severe_threshold (-0.25). IMPORTANT: This indicator must operate on the BROAD MARKET benchmark close (e.g., SPY), not the individual stock's close. The benchmark close series must be passed in via df.attrs['benchmark_close'] (a pd.Series indexed like df) or pre-joined as a column named 'benchmark_close' in the input DataFrame before calculate() is called. The coding agent must implement the benchmark data injection mechanism in the indicator suite's calculate() override and in the data-loading layer (wiring.py)."
    },
    {
      "id": "sma_200",
      "class": "SimpleMovingAverageIndicator",
      "is_custom": false,
      "registry_key": "sma",
      "params": {
        "window": 200,
        "source_column": "close",
        "output_column": "sma_200"
      },
      "output_columns": ["sma_200"],
      "warmup_bars": 200,
      "description": "200-day simple moving average of close. Used as an optional trend alignment filter: close > sma_200 required for long entry, providing a downside gate consistent with the strategy's goal of avoiding positions in established downtrends."
    }
  ],

  "derived_features": [
    {
      "column_name": "h52_ratio",
      "depends_on": ["close", "rolling_max_252"],
      "calculation": "Compute proximity of current price to its 52-week high: h52_ratio = close / rolling_max_252. Values range from 0.0 to 1.0 where 1.0 = trading at or above the 52-week high. Guard: when rolling_max_252 is NaN or <= 0, output NaN. Use np.clip(close / rolling_max_252, 0.0, 1.0) after the NaN guard."
    },
    {
      "column_name": "h52_quintile_entry",
      "depends_on": ["h52_ratio"],
      "calculation": "Boolean entry gate approximating top-quintile sector-neutral rank: h52_quintile_entry = (h52_ratio >= h52_entry_threshold). Config default h52_entry_threshold=0.80. True when stock is likely in top quintile of 52H proximity. Set to False when h52_ratio is NaN."
    },
    {
      "column_name": "h52_top_decile",
      "depends_on": ["h52_ratio"],
      "calculation": "Boolean flag for top-decile 52H proximity: h52_top_decile = (h52_ratio >= h52_top_decile_threshold). Config default h52_top_decile_threshold=0.90. True = approximately top-decile rank, triggers 1.3x conviction weight in the sizer. Set to False when h52_ratio is NaN."
    },
    {
      "column_name": "fcf_quality_gate",
      "depends_on": ["fcf_conversion_ttm"],
      "calculation": "Boolean quality gate: fcf_quality_gate = (fcf_conversion_ttm > fcf_conversion_min) AND NOT pd.isna(fcf_conversion_ttm). Config default fcf_conversion_min=1.0. Returns False when fundamental data is stale, unavailable, or when FCF conversion is at or below the threshold."
    },
    {
      "column_name": "momentum_confirmation",
      "depends_on": ["roc_126"],
      "calculation": "Boolean 6-month momentum confirmation: momentum_confirmation = (roc_126 > 0.0) AND NOT pd.isna(roc_126). True = positive 6-month cumulative return, confirming sustained uptrend and ruling out stocks whose 52-week high proximity reflects a pre-drawdown peak."
    },
    {
      "column_name": "score_h52",
      "depends_on": ["h52_ratio", "h52_top_decile"],
      "calculation": "Float conviction score for signal ranking and sizer conviction logic. Base score = h52_ratio * 100.0. When h52_top_decile is True, apply boost: score_h52 = h52_ratio * 100.0 * top_decile_score_boost (config default 1.3). When h52_top_decile is False: score_h52 = h52_ratio * 100.0. Set to 0.0 when h52_ratio is NaN. Range: 0.0 to 130.0. Higher values get priority fill when entry slots are limited."
    }
  ],

  "signals": {
    "direction": "long_only",
    "required_columns": [
      "h52_ratio",
      "h52_quintile_entry",
      "h52_top_decile",
      "fcf_quality_gate",
      "momentum_confirmation",
      "fcf_conversion_ttm",
      "market_state_regime",
      "score_h52",
      "sma_200",
      "close"
    ],
    "long_entry": {
      "conditions": [
        "h52_quintile_entry == True",
        "fcf_quality_gate == True",
        "momentum_confirmation == True",
        "close > sma_200"
      ],
      "logic": "AND",
      "rebalance_gate": "Only fire True on designated monthly rebalance bars (2 trading days after month-end). Signal model must track bar timestamps and suppress entry signals on non-rebalance bars. Intra-month entries are not generated; only risk controls may trigger intra-month exits.",
      "description": "Enter long when: (1) stock is in approximate top quintile of 52H proximity ratio (h52_ratio >= 0.80 — sector-neutral ranking approximation); (2) FCF conversion > 1.0 (cash quality gate active); (3) 6-month return > 0 (momentum confirmation, rules out stale pre-drawdown highs); (4) price above 200-day SMA (trend alignment downside gate). All four conditions must be simultaneously True on a monthly rebalance bar."
    },
    "long_exit": {
      "conditions": [
        "h52_ratio < h52_exit_threshold",
        "fcf_quality_gate == False"
      ],
      "logic": "OR",
      "rebalance_gate": "Scheduled exits (h52_ratio < threshold) only fire on monthly rebalance bars. Quality decay exit (fcf_quality_gate == False) fires on any bar when fresh fundamental data is available. Hard stop and earnings exits are handled by risk controls, not signal model.",
      "description": "Exit long when: (A) at monthly rebalance, h52_ratio drops below h52_exit_threshold (config default 0.75), indicating signal has decayed below approximate median sector rank; OR (B) on any bar, fcf_quality_gate turns False (fcf_conversion_ttm drops below 0.80 per quality decay check in QualityDecayExitControl, or fundamental data becomes stale). Note: hard stop (12%), earnings blackout (2 days pre-announcement), and regime halt are handled by risk controls and fire intra-month."
    },
    "short_entry": {
      "conditions": ["False"],
      "logic": "AND",
      "description": "Long-only strategy. short_entry always returns a Series of False."
    },
    "short_exit": {
      "conditions": ["False"],
      "logic": "AND",
      "description": "No short positions. short_exit always returns a Series of False."
    },
    "entry_score": {
      "column": "score_h52",
      "description": "Score entries by score_h52 (h52_ratio * 100, boosted to * 130 for top-decile names). Higher score = higher priority for fill when available position slots are limited at rebalance. The signal model's score_entries() method returns df['score_h52'] directly."
    }
  },

  "strategy_class": {
    "class_name": "AQM52Strategy",
    "file": "strategies/development/aqm_52/strategy.py",
    "base_class": "BaseComposableStrategy",
    "min_bars_required": 252,
    "get_sizing_hints_override": true,
    "sizing_hints_logic": "Override get_sizing_hints(row, target_position) to: (1) call hints = super().get_sizing_hints(row, target_position) which auto-extracts 'realized_vol' into candidate.volatility; (2) read row.get('market_state_regime') and if not None/NaN, set hints['regime'] = row['market_state_regime'] — this populates candidate.regime used by AQM52PositionSizer for market-state scaling; (3) read row.get('score_h52') and if not None/NaN, set hints['conviction'] = float(row['score_h52']) for optional downstream use. Return the enriched hints dict.",
    "description": "Monthly rebalance, long-only strategy exploiting 52-week high anchoring bias with FCF quality gate and vol-scaling. Subclasses BaseComposableStrategy, composed from AQM52IndicatorSuite and AQM52SignalModel. min_bars_required=252 reflects the full-year rolling window needed for the 52-week high reference and market state regime. The get_sizing_hints() override ensures market_state_regime flows into candidate.regime for the custom sizer."
  },

  "sizing": {
    "sizer_class": "AQM52PositionSizer",
    "is_custom": true,
    "file": "strategies/development/aqm_52/sizing/policy.py",
    "base_class": "BasePositionSizer",
    "params": {
      "base_equity_pct": 0.04,
      "max_equity_pct": 0.06,
      "top_decile_score_threshold": 90.0,
      "top_decile_boost": 1.3,
      "target_volatility": 0.15,
      "vol_scale_min": 0.10,
      "vol_scale_max": 3.0,
      "market_state_scales": {
        "up": 1.0,
        "down_moderate": 0.60,
        "down_severe": 0.25
      }
    },
    "description": "Custom position sizer combining three adjustments on top of an equal-weight base: (1) Volatility scaling per Barroso & Santa-Clara (2015) — scales allocation by target_volatility / realized_vol, clipped to [vol_scale_min, vol_scale_max]; (2) Top-decile conviction boost — if candidate.score >= top_decile_score_threshold (90.0), multiply by top_decile_boost (1.3x); (3) Market-state multiplier — reads candidate.regime and applies market_state_scales lookup (1.0 / 0.60 / 0.25 for up/down_moderate/down_severe). Final allocation = min(base_equity_pct * vol_scale * conviction_mult * regime_mult, max_equity_pct). Caps at min(target_value, context.cash).",
    "calculation": "def calculate_shares(symbol, price, context, candidate=None):\n  if price <= 0 or candidate is None: return 0.0\n  # Vol scaling\n  vol = candidate.volatility\n  vol_scale = clip(target_volatility / vol, vol_scale_min, vol_scale_max) if vol and vol > 0 else 1.0\n  # Conviction boost\n  conviction_mult = top_decile_boost if candidate.score >= top_decile_score_threshold else 1.0\n  # Regime scaling\n  regime = candidate.regime if candidate.regime else 'up'\n  regime_mult = market_state_scales.get(regime, 1.0)\n  # Final allocation\n  final_pct = min(base_equity_pct * vol_scale * conviction_mult * regime_mult, max_equity_pct)\n  target_value = min(context.equity * final_pct, context.cash)\n  return cost_model.max_units(price, target_value)"
  },

  "risk_controls": [
    {
      "control_class": "StopLossExitControl",
      "is_custom": false,
      "import_path": "prophitai_algo_trading.risk.std_lib",
      "params": {
        "pct": 0.12
      },
      "order": 1,
      "description": "Hard stop-loss exit (E2): force-close any long position that has declined 12% or more from its entry price at the next bar open. Direction-aware — tracks entry price via on_entry lifecycle hook internally. Fires intra-month regardless of rebalance schedule."
    },
    {
      "control_class": "EarningsBlackoutControl",
      "is_custom": false,
      "import_path": "prophitai_algo_trading.risk.std_lib",
      "params": {
        "days": 2
      },
      "order": 2,
      "description": "Earnings buffer (E3): block new entries AND force-exit existing positions when the ticker's next scheduled earnings announcement is within 2 trading days. Eliminates binary event risk that corrupts the price-based anchoring signal. Re-entry is evaluated at the next monthly rebalance bar after the announcement passes if the signal still qualifies. Requires earnings_dates dict to be pre-loaded and passed via the earnings_dates param in wiring.py — the coding agent must integrate the earnings calendar data feed."
    },
    {
      "control_class": "RegimeHaltControl",
      "is_custom": true,
      "file": "strategies/development/aqm_52/risk_controls/custom_control.py",
      "base_class": "AdvancedRiskControlTemplate",
      "params": {
        "regime_column": "market_state_regime",
        "allowed_long_regimes": ["up", "down_moderate"],
        "allowed_directions": ["long"],
        "stop_loss_pct": null,
        "trail_after_profit_pct": null,
        "trailing_stop_pct": null,
        "max_bars_in_trade": null,
        "cooldown_bars_after_exit": 0
      },
      "order": 3,
      "description": "Regime halt control (E5): blocks new long entries when market_state_regime == 'down_severe' (trailing 12-month broad market return < -25%). In 'down_moderate' regime (-15% to -25%), entries are still permitted but the sizer automatically reduces allocation to 60% of base via the market_state_scales['down_moderate']=0.60 parameter. Subclasses AdvancedRiskControlTemplate — the super().should_block_entry() call handles the allowed_long_regimes check against df['market_state_regime'].iloc[-1]. should_force_exit always returns False: exposure reduction in adverse regimes is handled via sizer scaling, not forced liquidation, to avoid momentum crash from simultaneous forced exits.",
      "calculation": "class RegimeHaltControl(AdvancedRiskControlTemplate):\n  def __init__(self):\n    super().__init__(regime_column='market_state_regime', allowed_long_regimes=('up','down_moderate'), allowed_directions=(Direction.LONG,), stop_loss_pct=None, cooldown_bars_after_exit=0)\n  def should_block_entry(self, ticker, price, timestamp, df, portfolio):\n    return super().should_block_entry(ticker, price, timestamp, df, portfolio)\n  def should_force_exit(self, ticker, price, timestamp, df, portfolio):\n    return False"
    },
    {
      "control_class": "QualityDecayExitControl",
      "is_custom": true,
      "file": "strategies/development/aqm_52/risk_controls/custom_control.py",
      "base_class": "RiskControl",
      "params": {
        "fcf_exit_threshold": 0.80,
        "indicator_column": "fcf_conversion_ttm"
      },
      "order": 4,
      "description": "Quality decay exit (E4): forces exit of open long positions when FCF conversion (Op CF TTM / Net Income TTM) drops below 0.80 on any bar when fresh fundamental data is available. This fires intra-month without waiting for the rebalance schedule. Does not block entries (entry qualification is handled in the signal model via fcf_quality_gate). Guards against stale data — only fires when fcf_conversion_ttm is non-NaN.",
      "calculation": "class QualityDecayExitControl(RiskControl):\n  def __init__(self, fcf_exit_threshold=0.80, indicator_column='fcf_conversion_ttm'):\n    self.fcf_exit_threshold = fcf_exit_threshold\n    self.indicator_column = indicator_column\n  def should_block_entry(self, ticker, price, timestamp, df, portfolio):\n    return False\n  def should_force_exit(self, ticker, price, timestamp, df, portfolio):\n    if not self.has_columns(df, self.indicator_column):\n      return False\n    row = self.latest_row(df)\n    val = row[self.indicator_column]\n    if pd.isna(val):\n      return False\n    return float(val) < self.fcf_exit_threshold"
    }
  ],

  "config_defaults": {
    "h52_entry_threshold": 0.80,
    "h52_top_decile_threshold": 0.90,
    "h52_exit_threshold": 0.75,
    "fcf_conversion_min": 1.0,
    "fcf_exit_threshold": 0.80,
    "fcf_staleness_limit_days": 45,
    "rolling_max_window": 252,
    "roc_window": 126,
    "realized_vol_window": 126,
    "sma_trend_window": 200,
    "market_return_window": 252,
    "down_moderate_threshold": -0.15,
    "down_severe_threshold": -0.25,
    "top_decile_score_threshold": 90.0,
    "top_decile_score_boost": 1.3,
    "target_volatility": 0.15,
    "vol_scale_min": 0.10,
    "vol_scale_max": 3.0,
    "base_equity_pct": 0.04,
    "max_equity_pct": 0.06,
    "market_state_scale_up": 1.0,
    "market_state_scale_down_moderate": 0.60,
    "market_state_scale_down_severe": 0.25,
    "stop_loss_pct": 0.12,
    "earnings_blackout_days": 2,
    "max_positions": 25,
    "rebalance_frequency": "monthly",
    "rebalance_offset_trading_days": 2,
    "initial_capital": 10000000.0,
    "cost_ptc": 0.0005,
    "cost_ftc": 0.0,
    "benchmark_ticker": "SPY"
  },

  "implementation_notes": [
    {
      "topic": "cross_sectional_ranking_simplification",
      "severity": "high",
      "original_idea": "Sector-neutral ranking of 52H_Ratio within GICS sectors; entry only for stocks in top quintile (>=80th pctile) and top decile (>=90th pctile) of their specific sector.",
      "simplification": "The per-ticker framework processes each ticker independently — no cross-sectional groupby is available at indicator or signal generation time. Replaced with absolute 52H_Ratio thresholds: h52_entry_threshold=0.80 as a proxy for top-quintile cutoff and h52_top_decile_threshold=0.90 for top-decile. These thresholds assume the cross-sectional distribution of 52H ratios is roughly uniform [0,1] in a typical market; the Research Agent must calibrate them empirically by comparing absolute thresholds to realized sector-neutral percentile ranks in historical data. Additionally, sector exclusions (Financials, Real Estate, Utilities) must be applied at the universe/data-loading layer in wiring.py, not in the signal model."
    },
    {
      "topic": "market_state_indicator_benchmark_injection",
      "severity": "high",
      "original_idea": "Market state based on trailing 12-month BROAD MARKET return (e.g., S&P 500), not individual stock return.",
      "simplification": "In the per-ticker architecture, each ticker's DataFrame contains only that ticker's OHLCV data. The MarketStateIndicator must be fed benchmark close data (SPY or equivalent). The coding agent must implement benchmark data injection: load SPY close series alongside each ticker in load_backtest_data(); pass it as df.attrs['benchmark_close'] before calling suite.calculate(), or pre-join it as a column 'benchmark_close' in each ticker's DataFrame. The indicator suite's calculate() override must handle this injection. Without this, market_state_regime will incorrectly reflect each individual stock's 12-month return rather than the broad market."
    },
    {
      "topic": "fcf_conversion_point_in_time_construction",
      "severity": "high",
      "original_idea": "FCF conversion ratio (Op CF TTM / Net Income TTM) with point-in-time data and 45-day filing lag to prevent look-ahead bias.",
      "simplification": "No change from idea — FcfConversionIndicator fully implements this. However, the coding agent must source point-in-time fundamental data (not as-restated) from a provider that supports historical point-in-time snapshots (e.g., Compustat, FactSet). Using as-reported Bloomberg consensus or quarterly reports without point-in-time versioning will introduce look-ahead bias. The 45-day staleness limit is enforced in the indicator: data reported more than 45 days after fiscal quarter-end is marked NaN. The fundamental data must be passed into the indicator suite at calculate() time via df.attrs['fundamentals']."
    },
    {
      "topic": "sector_exposure_cap_not_implemented",
      "severity": "medium",
      "original_idea": "Sector caps in the range 20-30% of gross exposure as an explicit risk guardrail.",
      "simplification": "Cross-sectional sector exposure tracking requires portfolio-level awareness that is not supported within the per-ticker RiskControl architecture. The per-position cap (max_equity_pct=0.06 = 6% per position) limits individual concentration. For sector-level enforcement, the Research Agent should implement a pre-rebalance portfolio construction step in a custom wiring function that: (1) collects all monthly entry candidates; (2) groups by GICS sector; (3) caps sector allocation at 25% of target gross exposure before passing candidates to the engine. This is a v2 enhancement — initial implementation relies on universe diversification and per-position cap only."
    },
    {
      "topic": "monthly_rebalance_bar_detection",
      "severity": "medium",
      "original_idea": "Monthly rebalance at open, 2 trading days after month-end. Primary entry and scheduled exit mechanism.",
      "simplification": "The EventDrivenBacktestEngine processes all bars sequentially. The signal model must detect rebalance bars and suppress entry/scheduled-exit signals on non-rebalance bars. Implement rebalance detection in the signal model's enrich() method: add a boolean column 'is_rebalance_bar' = True when the bar timestamp is the Nth trading day of a new month (N = rebalance_offset_trading_days = 2). long_entry() conditions must include 'is_rebalance_bar == True'. long_exit() for the scheduled rank-decay condition must also gate on 'is_rebalance_bar'. Intra-month exits (stop loss, earnings, quality decay, regime halt) are handled by risk controls and do not use this gate."
    },
    {
      "topic": "universe_screening_data_loading",
      "severity": "medium",
      "original_idea": "Extensive universe pre-screens: market_cap $2B-$150B, avg_daily_dollar_volume_20d >= $30M, price >= $10, trading_history_days >= 252, short_interest_pct < 20%, earnings_date not within ±5 days, sector exclusions, security type exclusions, net_income_ttm > 0.",
      "simplification": "These are data-loading filters, not per-bar signal conditions. They must be applied in load_backtest_data() in wiring.py before any ticker DataFrame is passed to the strategy. The EarningsBlackoutControl(days=2) handles the ±2 day earnings buffer at execution time. Short interest and security type filters require external data feeds to be integrated in the data-loading layer. The signal model does not re-check these conditions — it assumes the input universe is pre-screened."
    },
    {
      "topic": "vol_scaling_per_position_vs_portfolio_level",
      "severity": "low",
      "original_idea": "Scale monthly GROSS EXPOSURE of the entire momentum portfolio by Target_Vol / Realized_Vol_6M(momentum_portfolio), per Barroso & Santa-Clara (2015).",
      "simplification": "The framework's per-position architecture sizes each ticker independently. AQM52PositionSizer approximates portfolio-level vol-scaling by applying target_volatility / per_ticker_realized_vol to each position's allocation. This is consistent with the mechanism's intent (reduce exposure when individual stock volatility is elevated) but differs from the theoretical implementation (which scales the entire portfolio's gross exposure based on the portfolio's realized return volatility as a whole). The Research Agent should test both implementations and consider implementing a prepare_for_bar() hook in the sizer that computes the portfolio-level momentum portfolio volatility from strategy_data across all tickers and uses that as the vol-scaling denominator."
    }
  ]
}
```