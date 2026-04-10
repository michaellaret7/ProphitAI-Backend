"""Test the full builder pipeline end-to-end: Indicators → Signals → Execution.

Spins up a real E2B sandbox, bootstraps the repo, constructs the AQM-52
StrategyManifest, then runs all three builder agents sequentially. Each
agent's output feeds into the next. At the end, commits and pushes the
complete strategy code to the strategy branch for human review.
"""

from prophitai_atlas.models.callbacks import NoOpChatCallback

from prophitai_tools.sandbox.client import create_sandbox, remove_sandbox, get_sandbox
from prophitai_tools.sandbox.lifecycle import setup_repo
from prophitai_tools.sandbox.scaffolding import scaffold_strategy

from prophitai_fund.research.builders.indicators import IndicatorBuilderAgent, IndicatorBuildResult
from prophitai_fund.research.builders.signals import SignalStrategyBuilderAgent, SignalStrategyBuildResult
from prophitai_fund.research.builders.execution import ExecutionLayerBuilderAgent, ExecutionLayerBuildResult
from prophitai_fund.research.architect.models import (
    StrategyManifest,
    IndicatorEntry,
    DerivedFeature,
    SignalCondition,
    SignalSpec,
    SizerEntry,
    SizingSpec,
    RiskControlEntry,
    StrategyClassSpec,
    ConfigParam,
    ConfigDefaults,
    ImplementationNote,
)


# ================================
# --> Helper funcs
# ================================


def _cp(key: str, val) -> ConfigParam:
    """Shorthand ConfigParam builder from a key and a native Python value."""

    if isinstance(val, bool):
        return ConfigParam(key=key, value_bool=val)

    if isinstance(val, (int, float)):
        return ConfigParam(key=key, value_num=val)

    if isinstance(val, str):
        return ConfigParam(key=key, value_str=val)

    if isinstance(val, list):
        return ConfigParam(key=key, value_list=val)

    if isinstance(val, dict):
        return ConfigParam(key=key, value_map=[_cp(k, v) for k, v in val.items()])

    return ConfigParam(key=key, value_str=str(val))


def _build_manifest() -> StrategyManifest:
    """Construct the AQM-52 StrategyManifest from the spec."""

    indicators = [
        IndicatorEntry(
            class_name="RollingMaxIndicator",
            is_custom=True,
            file="indicators/rolling_max.py",
            params=[
                _cp("window", 252),
                _cp("source_column", "close"),
                _cp("output_column", "rolling_max_252"),
            ],
            input_columns=["close"],
            output_columns=["rolling_max_252"],
            calculation=(
                "Compute the rolling maximum of the close price series over the past "
                "`window` bars: df['rolling_max_252'] = df['close'].rolling(window=252, "
                "min_periods=252).max(). Returns NaN until exactly 252 bars of close data "
                "are available."
            ),
            scope="shared",
            description="52-week rolling high of close price",
        ),
        IndicatorEntry(
            registry_key="roc",
            class_name="RateOfChangeIndicator",
            is_custom=False,
            params=[
                _cp("window", 126),
                _cp("skip_recent", 0),
                _cp("source_column", "close"),
                _cp("output_column", "roc_126"),
            ],
            input_columns=["close"],
            output_columns=["roc_126"],
            scope="shared",
            description="6-month cumulative return for momentum confirmation",
        ),
        IndicatorEntry(
            class_name="RealizedVolIndicator",
            is_custom=True,
            file="indicators/realized_vol.py",
            params=[
                _cp("window", 126),
                _cp("source_column", "close"),
                _cp("output_column", "realized_vol"),
                _cp("annualize", True),
                _cp("trading_days_per_year", 252),
            ],
            input_columns=["close"],
            output_columns=["realized_vol"],
            calculation=(
                "Compute annualized 6-month realized volatility: "
                "df['realized_vol'] = df['close'].pct_change().rolling(window=126, "
                "min_periods=126).std() * (252 ** 0.5). Output column MUST be named "
                "exactly 'realized_vol' so get_sizing_hints() auto-populates "
                "candidate.volatility."
            ),
            scope="shared",
            description="Annualized 6-month realized volatility for vol-scaling",
        ),
        IndicatorEntry(
            class_name="FcfConversionIndicator",
            is_custom=True,
            file="indicators/fcf_conversion.py",
            params=[
                _cp("output_column", "fcf_conversion_ttm"),
                _cp("staleness_limit_days", 45),
            ],
            input_columns=[],
            output_columns=["fcf_conversion_ttm"],
            calculation=(
                "Join point-in-time quarterly fundamental data into the OHLCV DataFrame. "
                "fcf_conversion_ttm = operating_cash_flow_ttm / net_income_ttm. "
                "For each calendar date, use only the most recently reported quarterly data "
                "whose fiscal quarter-end date is at least 45 calendar days in the past. "
                "Forward-fill until next qualifying filing or staleness exceeded. "
                "When net_income_ttm <= 0, output NaN. "
                "Fundamental data passed via df.attrs['fundamentals'] as a DataFrame with "
                "columns ['date', 'operating_cash_flow_ttm', 'net_income_ttm']."
            ),
            scope="shared",
            description="FCF conversion ratio from point-in-time fundamental data",
        ),
        IndicatorEntry(
            class_name="MarketStateIndicator",
            is_custom=True,
            file="indicators/market_state.py",
            params=[
                _cp("window", 252),
                _cp("return_output_column", "market_return_252"),
                _cp("regime_output_column", "market_state_regime"),
                _cp("down_moderate_threshold", -0.15),
                _cp("down_severe_threshold", -0.25),
            ],
            input_columns=["benchmark_close"],
            output_columns=["market_return_252", "market_state_regime"],
            calculation=(
                "Compute trailing 252-bar return from benchmark close and classify into "
                "three regime strings. market_return_252 = benchmark_close.pct_change(252). "
                "Regime: 'up' when >= 0; 'down_moderate' when < 0 and >= -0.25; "
                "'down_severe' when < -0.25. Benchmark close passed via "
                "df.attrs['benchmark_close'] or pre-joined as 'benchmark_close' column."
            ),
            scope="shared",
            description="Broad market regime classification from benchmark return",
        ),
        IndicatorEntry(
            registry_key="sma",
            class_name="SimpleMovingAverageIndicator",
            is_custom=False,
            params=[
                _cp("window", 200),
                _cp("source_column", "close"),
                _cp("output_column", "sma_200"),
            ],
            input_columns=["close"],
            output_columns=["sma_200"],
            scope="shared",
            description="200-day SMA trend alignment filter",
        ),
    ]

    derived_features = [
        DerivedFeature(
            column_name="h52_ratio",
            depends_on=["close", "rolling_max_252"],
            logic=(
                "h52_ratio = np.clip(close / rolling_max_252, 0.0, 1.0). "
                "Guard: NaN when rolling_max_252 is NaN or <= 0."
            ),
        ),
        DerivedFeature(
            column_name="h52_quintile_entry",
            depends_on=["h52_ratio"],
            logic=(
                "h52_quintile_entry = h52_ratio >= 0.80. "
                "False when h52_ratio is NaN."
            ),
        ),
        DerivedFeature(
            column_name="h52_top_decile",
            depends_on=["h52_ratio"],
            logic=(
                "h52_top_decile = h52_ratio >= 0.90. "
                "False when h52_ratio is NaN."
            ),
        ),
        DerivedFeature(
            column_name="fcf_quality_gate",
            depends_on=["fcf_conversion_ttm"],
            logic=(
                "fcf_quality_gate = (fcf_conversion_ttm > 1.0) & ~pd.isna(fcf_conversion_ttm). "
                "False when fundamental data is stale or unavailable."
            ),
        ),
        DerivedFeature(
            column_name="momentum_confirmation",
            depends_on=["roc_126"],
            logic=(
                "momentum_confirmation = (roc_126 > 0.0) & ~pd.isna(roc_126). "
                "True = positive 6-month return."
            ),
        ),
        DerivedFeature(
            column_name="score_h52",
            depends_on=["h52_ratio", "h52_top_decile"],
            logic=(
                "Base score = h52_ratio * 100.0. "
                "When h52_top_decile is True, score_h52 = h52_ratio * 100.0 * 1.3. "
                "Otherwise score_h52 = h52_ratio * 100.0. "
                "Set to 0.0 when h52_ratio is NaN."
            ),
        ),
    ]

    signals = SignalSpec(
        class_name="AQM52SignalModel",
        required_columns=[
            "h52_ratio", "h52_quintile_entry", "h52_top_decile",
            "fcf_quality_gate", "momentum_confirmation", "fcf_conversion_ttm",
            "market_state_regime", "score_h52", "sma_200", "close",
        ],
        enrich_columns=["is_rebalance_bar"],
        enrich_logic=(
            "Add is_rebalance_bar = True on the 2nd trading day of each new month."
        ),
        long_entry=SignalCondition(
            conditions=[
                "h52_quintile_entry == True",
                "fcf_quality_gate == True",
                "momentum_confirmation == True",
                "close > sma_200",
                "is_rebalance_bar == True",
            ],
            primitives_used=[],
        ),
        long_exit=SignalCondition(
            conditions=[
                "h52_ratio < 0.75",
                "fcf_quality_gate == False",
            ],
            primitives_used=[],
        ),
        short_entry=SignalCondition(conditions=["False"], primitives_used=[]),
        short_exit=SignalCondition(conditions=["False"], primitives_used=[]),
        scoring_method="score_h52",
    )

    sizing = SizingSpec(
        chain_description="AQM52PositionSizer (vol-scaled + conviction boost + regime multiplier)",
        base_sizer=SizerEntry(
            class_name="AQM52PositionSizer",
            is_custom=True,
            params=[
                _cp("base_equity_pct", 0.04),
                _cp("max_equity_pct", 0.06),
                _cp("target_volatility", 0.15),
                _cp("vol_scale_min", 0.10),
                _cp("vol_scale_max", 3.0),
                _cp("top_decile_score_threshold", 90.0),
                _cp("top_decile_boost", 1.3),
                _cp("market_state_scales", {"up": 1.0, "down_moderate": 0.60, "down_severe": 0.25}),
            ],
            description="Custom vol-scaled sizer with conviction and regime adjustments",
        ),
    )

    risk_controls = [
        RiskControlEntry(
            class_name="StopLossExitControl",
            is_custom=False,
            params=[_cp("pct", 0.12)],
            rationale="Hard 12% stop-loss from entry price",
        ),
        RiskControlEntry(
            class_name="EarningsBlackoutControl",
            is_custom=False,
            params=[_cp("days", 2)],
            rationale="Block entries and force exits within 2 days of earnings",
        ),
        RiskControlEntry(
            class_name="RegimeHaltControl",
            is_custom=True,
            params=[
                _cp("regime_column", "market_state_regime"),
                _cp("allowed_long_regimes", ["up", "down_moderate"]),
            ],
            rationale="Block long entries in down_severe market regime",
        ),
        RiskControlEntry(
            class_name="QualityDecayExitControl",
            is_custom=True,
            params=[
                _cp("fcf_exit_threshold", 0.80),
                _cp("indicator_column", "fcf_conversion_ttm"),
            ],
            rationale="Force exit when FCF conversion drops below 0.80",
        ),
    ]

    strategy_class = StrategyClassSpec(
        class_name="AQM52Strategy",
        min_bars_required=252,
        min_bars_rationale="252-bar rolling max + market state window both need 252 bars of warmup",
        sizing_hints=[
            _cp("realized_vol", "realized_vol"),
            _cp("market_state_regime", "market_state_regime"),
            _cp("score_h52", "score_h52"),
        ],
    )

    config_defaults = ConfigDefaults(
        strategy=[
            _cp("h52_entry_threshold", 0.80),
            _cp("h52_top_decile_threshold", 0.90),
            _cp("h52_exit_threshold", 0.75),
            _cp("fcf_conversion_min", 1.0),
            _cp("top_decile_score_boost", 1.3),
            _cp("rebalance_frequency", "monthly"),
            _cp("rebalance_offset_trading_days", 2),
            _cp("max_positions", 25),
            _cp("benchmark_ticker", "SPY"),
        ],
        sizing=[
            _cp("base_equity_pct", 0.04),
            _cp("max_equity_pct", 0.06),
            _cp("target_volatility", 0.15),
            _cp("vol_scale_min", 0.10),
            _cp("vol_scale_max", 3.0),
            _cp("top_decile_score_threshold", 90.0),
            _cp("top_decile_boost", 1.3),
            _cp("market_state_scale_up", 1.0),
            _cp("market_state_scale_down_moderate", 0.60),
            _cp("market_state_scale_down_severe", 0.25),
        ],
        risk=[
            _cp("stop_loss_pct", 0.12),
            _cp("earnings_blackout_days", 2),
            _cp("fcf_exit_threshold", 0.80),
            _cp("fcf_staleness_limit_days", 45),
            _cp("down_moderate_threshold", -0.15),
            _cp("down_severe_threshold", -0.25),
        ],
        backtest=[
            _cp("initial_capital", 10000000.0),
            _cp("cost_ptc", 0.0005),
            _cp("cost_ftc", 0.0),
        ],
    )

    implementation_notes = [
        ImplementationNote(
            topic="cross_sectional_ranking_simplification",
            description=(
                "Replaced sector-neutral ranking with absolute thresholds: "
                "h52_entry_threshold=0.80, h52_top_decile_threshold=0.90"
            ),
        ),
        ImplementationNote(
            topic="market_state_benchmark_injection",
            description=(
                "MarketStateIndicator needs benchmark close data (SPY) injected via "
                "df.attrs['benchmark_close'] or pre-joined column"
            ),
        ),
        ImplementationNote(
            topic="fcf_conversion_point_in_time",
            description=(
                "FcfConversionIndicator needs point-in-time fundamental data "
                "passed via df.attrs['fundamentals']"
            ),
        ),
    ]

    return StrategyManifest(
        strategy_name="AQM52",
        strategy_id="aqm_52",
        category="momentum",
        timeframe="1d",
        direction="long_only",
        holding_period="monthly",
        expected_holding_bars=21,
        description=(
            "Exploits the 52-week high anchoring bias (George & Hwang 2004): stocks "
            "with high proximity to their annual high exhibit predictable price drift. "
            "FCF conversion gate removes distressed names. Vol-scaling targets constant "
            "portfolio variance. Long-only, monthly rebalance, US mid/large-cap equity."
        ),
        core_edge="52-week high anchoring bias — behavioral resistance to new highs creates predictable drift",
        mechanism="Behavioral: investors anchor to round-number reference points and underreact to proximity signals",
        regime_favorable=["trending bull markets", "low-volatility regimes"],
        regime_unfavorable=["severe bear markets (trailing 12mo < -25%)", "momentum crash regimes"],
        lookback_bars=252,
        indicators=indicators,
        derived_features=derived_features,
        signals=signals,
        sizing=sizing,
        risk_controls=risk_controls,
        strategy_class=strategy_class,
        config_defaults=config_defaults,
        implementation_notes=implementation_notes,
    )


def _print_result(title: str, content: str) -> None:
    """Pretty-print a labeled section."""

    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(content)


def _print_indicator_result(result: IndicatorBuildResult) -> None:
    """Print a summary of the indicator build result."""

    _print_result(
        "Indicator Build Result",
        f"Suite: {result.suite_class_name} @ {result.suite_file}\n"
        f"Custom file: {result.custom_file}\n"
        f"Derived features fn: {result.derived_features_function}\n"
        f"Indicator files: {len(result.indicator_files)}\n"
        f"All output columns: {result.all_output_columns}\n"
        f"Lint passed: {result.verification.lint_passed}\n"
        f"Import passed: {result.verification.import_passed}\n"
        f"Errors: {result.verification.errors}",
    )


def _print_signal_strategy_result(result: SignalStrategyBuildResult) -> None:
    """Print a summary of the signal+strategy build result."""

    _print_result(
        "Signal+Strategy Build Result",
        f"Signal model: {result.signal_model.class_name} @ {result.signal_model.file_path}\n"
        f"Strategy: {result.strategy.class_name} @ {result.strategy.file_path}\n"
        f"Config: {result.config.class_name} @ {result.config.file_path}\n"
        f"Min bars required: {result.strategy.min_bars_required}\n"
        f"Has sizing hints override: {result.strategy.has_sizing_hints_override}\n"
        f"Required columns: {result.signal_model.required_columns}\n"
        f"Lint passed: {result.verification.lint_passed}\n"
        f"Import passed: {result.verification.import_passed}\n"
        f"Errors: {result.verification.errors}",
    )


def _print_execution_result(result: ExecutionLayerBuildResult) -> None:
    """Print a summary of the execution layer build result."""

    sizing_summary = ", ".join(
        f.class_name or f.file_path.split("/")[-1]
        for f in result.sizing_files
    )

    risk_summary = ", ".join(result.risk_controls_used)

    runner_summary = ", ".join(r.runner_type for r in result.runner_files)

    _print_result(
        "Execution Layer Build Result",
        f"Sizing files: {sizing_summary}\n"
        f"Sizer chain: {result.sizer_chain_description}\n"
        f"Risk controls: {risk_summary}\n"
        f"Wiring: {result.wiring_file.build_function_name} @ {result.wiring_file.file_path}\n"
        f"Runners: {runner_summary}\n"
        f"Lint passed: {result.verification.lint_passed}\n"
        f"Import passed: {result.verification.import_passed}\n"
        f"Errors: {result.verification.errors}",
    )


# ================================
# --> Tests
# ================================


def test_builder_pipeline() -> None:
    """Run all three builder agents sequentially on the AQM-52 manifest."""

    sandbox_id = None
    strategy_name = "aqm_52"

    # Reason: Using sonnet for speed — switch to opus for higher quality builds.
    provider = "anthropic"
    model = "claude-sonnet-4-6"

    try:
        # ---- Step 1: Spin up sandbox and bootstrap repo ----

        print("Creating sandbox...")
        sandbox_id, sandbox = create_sandbox(timeout=3600)
        print(f"Sandbox created: {sandbox_id}")

        print("Bootstrapping repo...")
        repo_info = setup_repo(sandbox, strategy_name)
        print(f"Repo bootstrapped: {repo_info}")

        # ---- Step 2: Build the manifest ----

        print("Building StrategyManifest...")
        manifest = _build_manifest()

        _print_result(
            "Manifest Summary",
            f"Strategy: {manifest.strategy_name} ({manifest.strategy_id})\n"
            f"Category: {manifest.category} | Timeframe: {manifest.timeframe}\n"
            f"Direction: {manifest.direction} | Holding: {manifest.holding_period}\n"
            f"Indicators: {len(manifest.indicators)} "
            f"({sum(1 for i in manifest.indicators if i.is_custom)} custom)\n"
            f"Derived features: {len(manifest.derived_features)}\n"
            f"Risk controls: {len(manifest.risk_controls)} "
            f"({sum(1 for r in manifest.risk_controls if r.is_custom)} custom)\n"
            f"Sizing: {manifest.sizing.chain_description}",
        )

        callback = NoOpChatCallback()

        # ---- Step 2b: Scaffold the strategy directory ----

        print("Scaffolding strategy directory...")
        scaffold_result = scaffold_strategy(sandbox_id, strategy_name)
        print(f"Scaffold result: {scaffold_result}")

        # ---- Step 3: Run the Indicator Builder ----

        print("\n" + "=" * 60)
        print("  PHASE 1: Indicator Builder")
        print("=" * 60)

        indicator_agent = IndicatorBuilderAgent(
            sandbox_id=sandbox_id,
            chat_callback=callback,
            provider=provider,
            model=model,
        )

        indicator_response = indicator_agent.run(manifest)
        indicator_result: IndicatorBuildResult = indicator_response.parsed_output

        _print_indicator_result(indicator_result)

        if not indicator_result.verification.lint_passed:
            print("WARNING: Indicator build had lint failures — proceeding anyway")

        # ---- Step 4: Run the Signal+Strategy Builder ----

        print("\n" + "=" * 60)
        print("  PHASE 2: Signal+Strategy Builder")
        print("=" * 60)

        signal_agent = SignalStrategyBuilderAgent(
            sandbox_id=sandbox_id,
            chat_callback=callback,
            provider=provider,
            model=model,
        )

        signal_response = signal_agent.run(manifest, indicator_result)
        signal_result: SignalStrategyBuildResult = signal_response.parsed_output

        _print_signal_strategy_result(signal_result)

        if not signal_result.verification.lint_passed:
            print("WARNING: Signal+Strategy build had lint failures — proceeding anyway")

        # ---- Step 5: Run the Execution Layer Builder ----

        print("\n" + "=" * 60)
        print("  PHASE 3: Execution Layer Builder")
        print("=" * 60)

        execution_agent = ExecutionLayerBuilderAgent(
            sandbox_id=sandbox_id,
            chat_callback=callback,
            provider=provider,
            model=model,
        )

        execution_response = execution_agent.run(manifest, indicator_result, signal_result)
        execution_result: ExecutionLayerBuildResult = execution_response.parsed_output

        _print_execution_result(execution_result)

        # ---- Step 6: Final summary ----

        print("\n" + "=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)

        all_passed = (
            indicator_result.verification.lint_passed
            and indicator_result.verification.import_passed
            and signal_result.verification.lint_passed
            and signal_result.verification.import_passed
            and execution_result.verification.lint_passed
            and execution_result.verification.import_passed
        )

        print(f"All verifications passed: {all_passed}")
        print(f"Indicator files: {len(indicator_result.indicator_files)}")
        print(f"Signal model: {signal_result.signal_model.class_name}")
        print(f"Strategy class: {signal_result.strategy.class_name}")
        print(f"Sizer chain: {execution_result.sizer_chain_description}")
        print(f"Risk controls: {len(execution_result.risk_controls_used)}")
        print(f"Runner scripts: {len(execution_result.runner_files)}")

        # ---- Step 7: Commit and push ----

        print("\nCommitting and pushing all changes...")

        from prophitai_tools.sandbox.execution import sandbox_bash

        commit_result = sandbox_bash(
            sandbox_id,
            (
                "cd /home/user/strategies && "
                "git add -A && "
                "git diff --cached --stat && "
                'git commit -m "feat(aqm_52): full strategy build from manifest\n\n'
                "- Indicators: custom RollingMax, RealizedVol, FcfConversion, MarketState + std_lib ROC, SMA\n"
                "- Signal model: AQM52SignalModel with rebalance enrichment\n"
                "- Strategy: AQM52Strategy (BaseComposableStrategy)\n"
                "- Sizing: AQM52PositionSizer (vol-scaled + conviction + regime)\n"
                "- Risk controls: StopLoss, EarningsBlackout, RegimeHalt, QualityDecayExit\n"
                "- Engine wiring + 3 runner scripts (event backtest, vectorized, live)\n"
                '\nBuilt by full builder pipeline test" && '
                f"git push origin strategy/{strategy_name}"
            ),
        )

        _print_result("Git Push Result", commit_result)
        print(f"\nBranch pushed: strategy/{strategy_name}")
        print(f"Review at: https://github.com/Prophit-AI/Strategies/tree/strategy/{strategy_name}")

    finally:
        if sandbox_id:
            print(f"\nCleaning up sandbox {sandbox_id}...")

            try:
                sb = get_sandbox(sandbox_id)

                if sb:
                    sb.kill()
            except Exception:
                pass

            remove_sandbox(sandbox_id)
            print("Sandbox closed.")


if __name__ == "__main__":
    test_builder_pipeline()
