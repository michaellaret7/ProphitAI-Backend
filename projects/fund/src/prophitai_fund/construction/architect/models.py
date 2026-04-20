from typing import Optional
from pydantic import BaseModel, Field

# ================================
# --> Helper models
# ================================

class MapEntry(BaseModel):
    """A single key-value pair within a value_map. Values are stored as strings
    and parsed by consumers (e.g. '1.0' for floats, 'true' for booleans)."""

    key: str = Field(description="Sub-parameter name (e.g. 'up', 'down_moderate')")
    value: str = Field(description="Sub-parameter value as string (e.g. '1.0', 'true', 'close')")


class ConfigParam(BaseModel):
    """A single key-value parameter. Use value_str for strings, value_num for numbers,
    value_bool for booleans, value_list for lists, and value_map for nested key-value maps.
    Exactly one value field should be populated."""

    key: str = Field(description="Parameter name (e.g. 'window', 'source_column')")
    value_str: Optional[str] = Field(None, description="String value")
    value_num: Optional[float] = Field(None, description="Numeric value (int or float)")
    value_bool: Optional[bool] = Field(None, description="Boolean value")
    value_list: Optional[list[str]] = Field(None, description="List of string values")
    value_map: Optional[list[MapEntry]] = Field(None, description="Nested key-value pairs for sub-objects")

    @property
    def resolved_value(self) -> str | float | bool | list[str] | dict | None:
        """Return the populated value, resolved to its native Python type."""

        if self.value_map is not None:
            return {entry.key: entry.value for entry in self.value_map}

        if self.value_list is not None:
            return self.value_list

        if self.value_bool is not None:
            return self.value_bool

        if self.value_num is not None:
            return self.value_num

        return self.value_str


def params_to_dict(params: list["ConfigParam"]) -> dict:
    """Convert a list of ConfigParam into a plain dict."""
    return {p.key: p.resolved_value for p in params}

# ================================
# --> Manifest output models
# ================================

class DataRequirementEntry(BaseModel):
    """A supplementary data dependency for an indicator that reads from df.attrs."""
    kind: str = Field(description="Data source kind: 'fundamentals', 'financial_ratios', 'commodity', 'equity_price', 'universe_returns', 'economic_indicator', 'government_bond_rates', 'economic_calendar', 'ticker_meta'")
    attrs_key: str = Field(description="Key in df.attrs where data is attached (e.g. 'fundamentals', 'vix', 'claims', 'spy')")
    scope: str = Field(default="per_ticker", description="'per_ticker' when data varies by ticker, 'shared' when same for all")
    params: list[ConfigParam] = Field(default_factory=list, description="Provider-specific params (e.g. symbol='VIXUSD' for commodity, symbol='SPY' for equity_price, indicator='initialClaims' for economic_indicator)")
    min_coverage: float = Field(default=0.8, description="Fraction (0.0-1.0) of the universe that must have this data populated after resolve. Preflight raises DataCoverageError if coverage is below threshold. Set 1.0 for hard requirements (SPY broadcast, ticker_meta), 0.6-0.8 for fundamentals on noisy universes.")
    broadcast_as: Optional[str] = Field(default=None, description="Column name to broadcast a scope='shared' Series/DataFrame onto every ticker's DataFrame. REQUIRED when the signal model reads the data as a per-ticker column (e.g. df['spy_close']). Only valid when scope='shared'. Example: DataRequirement for SPY equity_price with broadcast_as='spy_close' makes df['spy_close'] available to signal code.")


class IndicatorEntry(BaseModel):
    """A single indicator in the manifest — either std_lib or custom."""
    registry_key: Optional[str] = Field(None, description="Std_lib registry key (e.g. 'atr', 'ema'). Null for custom indicators.")
    class_name: str = Field(description="Class name (e.g. 'ATRIndicator' or 'OFIProxyIndicator')")
    is_custom: bool = Field(default=False, description="True if this requires a new BaseIndicator subclass")
    file: Optional[str] = Field(None, description="Relative file path for custom indicator (e.g. 'indicators/ofi_proxy.py')")
    params: list[ConfigParam] = Field(default_factory=list, description="Constructor kwargs as key-value pairs")
    input_columns: list[str] = Field(default_factory=list, description="Columns this indicator reads from the DataFrame")
    output_columns: list[str] = Field(description="Columns this indicator adds to the DataFrame")
    calculation: Optional[str] = Field(None, description="Natural-language calculation description for custom indicators")
    scope: str = Field(default="shared", description="'shared' or 'strategy'")
    description: Optional[str] = Field(None, description="One-line purpose")
    data_requirements: list[DataRequirementEntry] = Field(default_factory=list, description="Supplementary data this indicator reads from df.attrs. Only needed for indicators that access df.attrs.")


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
    params: list[ConfigParam] = Field(default_factory=list, description="Constructor kwargs as key-value pairs")
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
    params: list[ConfigParam] = Field(default_factory=list, description="Constructor kwargs as key-value pairs")
    rationale: str = Field(description="Why this control is included")


class StrategyClassSpec(BaseModel):
    """Strategy class configuration."""
    class_name: str = Field(description="Strategy class name (e.g. 'OMFM15Strategy')")
    min_bars_required: int = Field(description="Warmup bars needed before signals can fire")
    min_bars_rationale: str = Field(description="How min_bars_required was derived")
    sizing_hints: list[ConfigParam] = Field(default_factory=list, description="Overrides for get_sizing_hints() as key-value pairs")


class ConfigDefaults(BaseModel):
    """All tunable parameter defaults grouped by concern."""
    strategy: list[ConfigParam] = Field(default_factory=list, description="Strategy config params")
    sizing: list[ConfigParam] = Field(default_factory=list, description="Sizing config params")
    risk: list[ConfigParam] = Field(default_factory=list, description="Risk config params")
    backtest: list[ConfigParam] = Field(default_factory=list, description="Backtest config params")
    live: list[ConfigParam] = Field(default_factory=list, description="Live trading config params")


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

