from typing import Optional, Any
from pydantic import BaseModel, Field

# ================================
# --> Manifest output models
# ================================

class IndicatorEntry(BaseModel):
    """A single indicator in the manifest — either std_lib or custom."""
    registry_key: Optional[str] = Field(None, description="Std_lib registry key (e.g. 'atr', 'ema'). Null for custom indicators.")
    class_name: str = Field(description="Class name (e.g. 'ATRIndicator' or 'OFIProxyIndicator')")
    is_custom: bool = Field(default=False, description="True if this requires a new BaseIndicator subclass")
    file: Optional[str] = Field(None, description="Relative file path for custom indicator (e.g. 'indicators/ofi_proxy.py')")
    params: dict[str, Any] = Field(default_factory=dict, description="Constructor kwargs")
    input_columns: list[str] = Field(default_factory=list, description="Columns this indicator reads from the DataFrame")
    output_columns: list[str] = Field(description="Columns this indicator adds to the DataFrame")
    calculation: Optional[str] = Field(None, description="Natural-language calculation description for custom indicators")
    scope: str = Field(default="shared", description="'shared' or 'strategy'")
    description: Optional[str] = Field(None, description="One-line purpose")


class DerivedFeature(BaseModel):
    """A post-indicator computed column."""
    column_name: str = Field(description="Output column name")
    depends_on: list[str] = Field(description="Indicator output columns this feature reads")
    logic: str = Field(description="Natural-language description of the calculation")


class SignalCondition(BaseModel):
    """A single entry/exit signal with its conditions."""
    conditions: list[str] = Field(description="List of conditions (AND logic within, described precisely)")
    primitives_used: list[str] = Field(default_factory=list, description="Signal primitives used (e.g. 'cross_above', 'bars_since')")


class SignalSpec(BaseModel):
    """Signal model specification."""
    class_name: str = Field(description="Signal model class name (e.g. 'OMFM15SignalModel')")
    required_columns: list[str] = Field(description="All columns the signal model needs from indicators + derived features")
    enrich_columns: list[str] = Field(default_factory=list, description="Columns added during enrich() step")
    enrich_logic: Optional[str] = Field(None, description="Description of enrich() computation")
    long_entry: SignalCondition
    long_exit: SignalCondition
    short_entry: SignalCondition
    short_exit: SignalCondition
    scoring_method: str = Field(description="How score_entries() computes conviction (e.g. 'abs(ofi_zscore)')")


class SizerEntry(BaseModel):
    """A single sizer in the sizing chain."""
    class_name: str = Field(description="Sizer class name")
    is_custom: bool = Field(default=False)
    params: dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class SizingSpec(BaseModel):
    """Full sizing chain specification."""
    chain_description: str = Field(description="Human-readable chain (e.g. 'VIXScaledSizer -> DrawdownScaledSizer -> ATRRiskSizer')")
    base_sizer: SizerEntry
    wrapper: Optional[SizerEntry] = None
    custom_outer: Optional[SizerEntry] = None


class RiskControlEntry(BaseModel):
    """A single risk control."""
    class_name: str = Field(description="Risk control class name (e.g. 'StopLossExitControl')")
    is_custom: bool = Field(default=False)
    params: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(description="Why this control is included")


class StrategyClassSpec(BaseModel):
    """Strategy class configuration."""
    class_name: str = Field(description="Strategy class name (e.g. 'OMFM15Strategy')")
    min_bars_required: int = Field(description="Warmup bars needed before signals can fire")
    min_bars_rationale: str = Field(description="How min_bars_required was derived")
    sizing_hints: dict[str, Any] = Field(default_factory=dict, description="Overrides for get_sizing_hints()")


class ConfigDefaults(BaseModel):
    """All tunable parameter defaults grouped by concern."""
    strategy: dict[str, Any] = Field(default_factory=dict)
    sizing: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    backtest: dict[str, Any] = Field(default_factory=dict)
    live: dict[str, Any] = Field(default_factory=dict)


class ImplementationNote(BaseModel):
    """A design decision, simplification, or Phase 2 deferral."""
    topic: str
    description: str


class StrategyManifest(BaseModel):
    """Complete implementation spec for a trading strategy.

    Produced by the Strategy Architect from an idea generator output.
    Consumed by the Indicator Builder, Signal+Strategy Builder, and
    Execution Layer Builder agents to produce working code.
    """

    # Metadata
    strategy_name: str = Field(description="Human-readable name (e.g. 'OMFM15')")
    strategy_id: str = Field(description="Snake_case identifier for filenames (e.g. 'omfm_15')")
    category: str = Field(description="Strategy category (e.g. 'momentum', 'mean_reversion', 'stat_arb')")
    timeframe: str = Field(description="Bar granularity (e.g. '1min', '15min', '1h', '1d')")
    direction: str = Field(description="'long_only', 'short_only', or 'long_short'")
    holding_period: str = Field(description="'intraday', 'overnight', 'multi_day', 'weekly'")
    expected_holding_bars: int = Field(description="Typical number of bars a position is held")
    description: str = Field(description="2-3 sentence strategy summary")

    # Thesis
    core_edge: str = Field(description="What anomaly/pattern this strategy exploits")
    mechanism: str = Field(description="Why the edge persists (behavioral/structural/risk-based)")
    regime_favorable: list[str] = Field(default_factory=list, description="Macro conditions where this works")
    regime_unfavorable: list[str] = Field(default_factory=list, description="Macro conditions where this breaks")

    # Data
    input_columns: list[str] = Field(default_factory=lambda: ["open", "high", "low", "close", "volume"])
    lookback_bars: int = Field(description="Total history needed for warmup")

    # Components
    indicators: list[IndicatorEntry] = Field(description="Ordered list of indicators (std_lib + custom)")
    derived_features: list[DerivedFeature] = Field(default_factory=list, description="Post-indicator computed columns")
    signals: SignalSpec
    sizing: SizingSpec
    risk_controls: list[RiskControlEntry]
    strategy_class: StrategyClassSpec
    config_defaults: ConfigDefaults

    # Implementation notes
    implementation_notes: list[ImplementationNote] = Field(default_factory=list)

