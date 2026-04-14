"""Test that parse_with_gpt can handle StrategyManifest — the largest
Pydantic model in the pipeline.

Feeds a realistic, fully-populated manifest as raw text and asks the
parser to extract it into a validated StrategyManifest instance.
"""

from prophitai_atlas.utils.gpt_parser import parse_with_gpt
from prophitai_fund.research.architect.models import StrategyManifest

SAMPLE_MANIFEST_TEXT = """
Here is the complete Strategy Manifest for the Order-Flow Momentum strategy on 15-minute bars:

Strategy Name: OMFM15
Strategy ID: omfm_15
Category: momentum
Timeframe: 15min
Direction: long_short
Holding Period: intraday
Expected Holding Bars: 12
Description: A high-frequency momentum strategy that uses order-flow imbalance proxied by volume-weighted price momentum to capture short-term directional moves on 15-minute bars. The strategy enters when OFI z-scores exceed thresholds and exits on mean reversion or stop-loss triggers.

Core Edge: Order-flow imbalance measured via volume-weighted close-to-close returns reveals institutional activity before price fully adjusts. The 15-minute bar aggregation smooths microstructure noise while preserving the signal.
Mechanism: Behavioral — large participants split orders across bars, creating persistent price impact that lasts 2-4 bars beyond initial detection.
Favorable Regimes: trending markets, high volume sessions, post-FOMC drift, earnings season
Unfavorable Regimes: low-volume holiday sessions, choppy range-bound days, flash-crash dislocations

Input Columns: open, high, low, close, volume
Lookback Bars: 120

Indicators:
1. EMA (std_lib, registry_key=ema, class=EMAIndicator, params: window=20, source_column=close, output_columns: [ema_20])
2. ATR (std_lib, registry_key=atr, class=ATRIndicator, params: window=14, output_columns: [atr_14])
3. RSI (std_lib, registry_key=rsi, class=RSIIndicator, params: window=14, source_column=close, output_columns: [rsi_14])
4. VWAP (std_lib, registry_key=vwap, class=VWAPIndicator, params: reset_period=1D, output_columns: [vwap])
5. OFI Proxy (custom, class=OFIProxyIndicator, file=indicators/ofi_proxy.py, params: window=20, volume_scale=true, input_columns: [close, volume], output_columns: [ofi_raw, ofi_zscore], calculation: Compute volume-weighted close-to-close log returns, then z-score over a rolling window.)
6. Bollinger Bands (std_lib, registry_key=bollinger, class=BollingerBandsIndicator, params: window=20, num_std=2.0, source_column=close, output_columns: [bb_upper, bb_lower, bb_mid, bb_pct_b])

Derived Features:
- ofi_momentum: depends on [ofi_zscore, ema_20], logic: Rate of change of ofi_zscore over 3 bars multiplied by sign of (close - ema_20) for trend alignment.
- vol_regime: depends on [atr_14], logic: Rolling percentile rank of ATR over 50 bars — above 0.7 is high-vol regime, below 0.3 is low-vol.

Signal Model:
Class: OMFM15SignalModel
Required Columns: ofi_zscore, ofi_momentum, rsi_14, ema_20, atr_14, bb_pct_b, vol_regime, vwap, close
Enrich Columns: ofi_accel, trend_strength
Enrich Logic: ofi_accel = diff(ofi_zscore, 1), trend_strength = abs(close - ema_20) / atr_14
Long Entry Conditions: ofi_zscore > 1.5 AND ofi_momentum > 0.3 AND rsi_14 < 75 AND close > vwap
  Primitives: cross_above, threshold_check
Long Exit Conditions: ofi_zscore < 0.5 OR rsi_14 > 80 OR bars_since_entry >= 12
  Primitives: cross_below, bars_since
Short Entry Conditions: ofi_zscore < -1.5 AND ofi_momentum < -0.3 AND rsi_14 > 25 AND close < vwap
  Primitives: cross_below, threshold_check
Short Exit Conditions: ofi_zscore > -0.5 OR rsi_14 < 20 OR bars_since_entry >= 12
  Primitives: cross_above, bars_since
Scoring Method: abs(ofi_zscore) * (1 + abs(ofi_momentum))

Sizing:
Chain: VIXScaledSizer -> ATRRiskSizer
Base Sizer: ATRRiskSizer (not custom, params: risk_per_trade=0.01, atr_column=atr_14, atr_multiplier=2.0)
Wrapper: VIXScaledSizer (custom, params: max_scale=1.5, min_scale=0.3, vix_baseline=20.0, description: Scales position size inversely with VIX relative to baseline)

Risk Controls:
1. StopLossExitControl (not custom, params: stop_type=atr, atr_multiplier=2.5, rationale: Limits per-trade loss to 2.5x ATR to contain tail risk)
2. TrailingStopControl (not custom, params: trail_type=atr, atr_multiplier=1.5, activation_profit_atr=1.0, rationale: Locks in profit after 1 ATR move with 1.5 ATR trailing distance)
3. MaxDailyLossControl (custom, params: max_daily_loss_pct=0.03, rationale: Hard circuit breaker — stops trading for the day after 3% portfolio drawdown)

Strategy Class:
Class Name: OMFM15Strategy
Min Bars Required: 120
Min Bars Rationale: Longest indicator lookback is OFI z-score (20 bars) + derived vol_regime percentile (50 bars) + buffer = 120 bars
Sizing Hints: base_risk_per_trade=0.01, max_position_pct=0.05, max_correlated_exposure=0.15

Config Defaults:
Strategy: ofi_zscore_entry_long=1.5, ofi_zscore_entry_short=-1.5, ofi_momentum_threshold=0.3, rsi_long_cap=75, rsi_short_floor=25, max_holding_bars=12
Sizing: risk_per_trade=0.01, atr_multiplier=2.0, vix_baseline=20.0, max_vix_scale=1.5, min_vix_scale=0.3
Risk: stop_atr_multiplier=2.5, trail_atr_multiplier=1.5, trail_activation_atr=1.0, max_daily_loss_pct=0.03
Backtest: initial_capital=100000, commission_per_share=0.005, slippage_bps=2

Implementation Notes:
- OFI Proxy Simplification: Using volume-weighted close returns as an OFI proxy rather than true Level 2 order flow data. Phase 2 could integrate tick-level OFI.
- VIX Data Source: VIXScaledSizer assumes a vix_close column is available in the DataFrame. The runner must inject this from an external source before bar processing.
- Regime Filter Deferral: No explicit regime filter on entry — vol_regime is available for manual analysis but not wired into signals. Can be added in Phase 2.
"""


def test_parse_strategy_manifest():
    print("Parsing StrategyManifest from realistic text...")
    print(f"Input length: {len(SAMPLE_MANIFEST_TEXT)} chars\n")

    result = parse_with_gpt(
        query=SAMPLE_MANIFEST_TEXT,
        target_model=StrategyManifest,
    )

    # Validate top-level fields
    assert result.strategy_name == "OMFM15", f"Expected OMFM15, got {result.strategy_name}"
    assert result.strategy_id == "omfm_15", f"Expected omfm_15, got {result.strategy_id}"
    assert result.category == "momentum"
    assert result.timeframe == "15min"
    assert result.direction == "long_short"

    # Validate nested indicators
    assert len(result.indicators) >= 5, f"Expected at least 5 indicators, got {len(result.indicators)}"

    custom_indicators = [i for i in result.indicators if i.is_custom]
    assert len(custom_indicators) >= 1, "Expected at least 1 custom indicator (OFI Proxy)"

    # Validate derived features
    assert len(result.derived_features) >= 2, f"Expected at least 2 derived features, got {len(result.derived_features)}"

    # Validate signal spec (deeply nested)
    assert result.signals.class_name == "OMFM15SignalModel"
    assert len(result.signals.long_entry.conditions) >= 1
    assert len(result.signals.short_entry.conditions) >= 1

    # Validate sizing chain
    assert result.sizing.base_sizer.class_name == "ATRRiskSizer"
    assert result.sizing.wrapper is not None

    # Validate risk controls
    assert len(result.risk_controls) >= 3, f"Expected at least 3 risk controls, got {len(result.risk_controls)}"

    # Validate config defaults (the union-heavy part)
    assert len(result.config_defaults.strategy) >= 1
    assert len(result.config_defaults.sizing) >= 1
    assert len(result.config_defaults.risk) >= 1

    # Validate ConfigParam resolved values work
    for param in result.config_defaults.strategy:
        val = param.resolved_value
        assert val is not None, f"ConfigParam '{param.key}' resolved to None"

    print("=== PASS ===")
    print(f"Strategy: {result.strategy_name} ({result.strategy_id})")
    print(f"Indicators: {len(result.indicators)} ({len(custom_indicators)} custom)")
    print(f"Derived features: {len(result.derived_features)}")
    print(f"Signal model: {result.signals.class_name}")
    print(f"Risk controls: {len(result.risk_controls)}")
    print(f"Config params: strategy={len(result.config_defaults.strategy)}, "
          f"sizing={len(result.config_defaults.sizing)}, "
          f"risk={len(result.config_defaults.risk)}, "
          f"backtest={len(result.config_defaults.backtest)}")


if __name__ == "__main__":
    test_parse_strategy_manifest()
