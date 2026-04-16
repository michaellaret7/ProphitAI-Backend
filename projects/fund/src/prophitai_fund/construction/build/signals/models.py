"""Output models for the Signal+Strategy Builder agent.

Defines the structured result that the Signal+Strategy Builder produces after
writing signal model, strategy class, and config files to the sandbox.
Consumed by the Execution Layer Builder to know exact class names, file paths,
required columns, and config fields.
"""

from pydantic import BaseModel, Field


# ================================
# --> Helper models
# ================================


class BuiltSignalModelFile(BaseModel):
    """The signal model file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/signals/model.py')"
    )
    class_name: str = Field(
        description="Signal model class name (e.g. 'OMFM15SignalModel')"
    )
    required_columns: list[str] = Field(
        description="Columns the signal model validates via required_columns tuple"
    )
    enrich_columns: list[str] = Field(
        default_factory=list,
        description="Columns added by the enrich() method",
    )
    primitives_used: list[str] = Field(
        default_factory=list,
        description="Signal primitives imported (e.g. 'cross_above', 'bars_since')",
    )


class BuiltStrategyFile(BaseModel):
    """The strategy class file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/strategy.py')"
    )
    class_name: str = Field(
        description="Strategy class name (e.g. 'OMFM15Strategy')"
    )
    min_bars_required: int = Field(
        description="Warmup bars before signals can fire"
    )
    has_sizing_hints_override: bool = Field(
        description="Whether get_sizing_hints() was overridden"
    )


class BuiltConfigFile(BaseModel):
    """The config dataclass file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/config.py')"
    )
    class_name: str = Field(
        description="Config dataclass name (e.g. 'OMFM15Config')"
    )
    field_names: list[str] = Field(
        description="Names of all config fields for downstream consumption"
    )


class VerificationResult(BaseModel):
    """Result of post-write verification checks."""

    lint_passed: bool = Field(
        description="Whether ruff check passed on all files"
    )
    import_passed: bool = Field(
        description="Whether Python import checks passed"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Any error messages from failed checks",
    )


# ================================
# --> Output model
# ================================


class SignalStrategyBuildResult(BaseModel):
    """Complete output from the Signal+Strategy Builder agent.

    Consumed by the Execution Layer Builder to know exactly what signal,
    strategy, and config classes exist, where they live, and what columns
    and parameters they use.
    """

    strategy_id: str = Field(
        description="Strategy identifier (e.g. 'omfm_15')"
    )
    strategy_name: str = Field(
        description="Human-readable name (e.g. 'OMFM15')"
    )

    signal_model: BuiltSignalModelFile = Field(
        description="Signal model file details"
    )
    strategy: BuiltStrategyFile = Field(
        description="Strategy class file details"
    )
    config: BuiltConfigFile = Field(
        description="Config dataclass file details"
    )

    verification: VerificationResult = Field(
        description="Results of lint and import verification"
    )
