"""Output models for the Execution Layer Builder agent.

Defines the structured result that the Execution Layer Builder produces after
writing sizing, risk control, wiring, and runner files to the sandbox.
This is the final builder output — consumed by the orchestrator to confirm
the strategy is fully built and runnable.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ================================
# --> Helper models
# ================================


class BuiltSizerFile(BaseModel):
    """A sizing file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/sizing/policy.py')"
    )
    class_name: Optional[str] = Field(
        None,
        description="Custom sizer class name (None for __init__.py or non-class files)",
    )
    is_custom: bool = Field(
        description="True if this contains a custom BasePositionSizer subclass"
    )


class BuiltRiskControlFile(BaseModel):
    """A risk control file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/risk_controls/defaults.py')"
    )
    class_name: Optional[str] = Field(
        None,
        description="Custom risk control class name (None for defaults.py or __init__.py)",
    )
    is_custom: bool = Field(
        description="True if this contains a custom RiskControl subclass"
    )


class BuiltWiringFile(BaseModel):
    """The engine wiring file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/wiring.py')"
    )
    build_function_name: str = Field(
        description="Name of the engine-building function (e.g. 'build_omfm_15_engine')"
    )


class BuiltRunnerFile(BaseModel):
    """A runner script written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/run_event_backtest.py')"
    )
    runner_type: str = Field(
        description="Runner type: 'event_backtest', 'vectorized_backtest', or 'live'"
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


class ExecutionLayerBuildResult(BaseModel):
    """Complete output from the Execution Layer Builder agent.

    This is the final builder output in the pipeline. It confirms that
    sizing, risk controls, engine wiring, and runner scripts are written
    and verified, making the strategy fully runnable.
    """

    strategy_id: str = Field(
        description="Strategy identifier (e.g. 'omfm_15')"
    )
    strategy_name: str = Field(
        description="Human-readable name (e.g. 'OMFM15')"
    )

    sizing_files: list[BuiltSizerFile] = Field(
        description="All sizing files written (policy.py if custom, __init__.py)"
    )
    risk_control_files: list[BuiltRiskControlFile] = Field(
        description="All risk control files written (defaults.py, custom controls, __init__.py)"
    )
    wiring_file: BuiltWiringFile = Field(
        description="Engine wiring file details"
    )
    runner_files: list[BuiltRunnerFile] = Field(
        description="Runner script files (event backtest, vectorized backtest, live)"
    )

    sizer_chain_description: str = Field(
        description="Human-readable sizer chain (e.g. 'DrawdownScaledSizer -> ATRRiskSizer')"
    )
    risk_controls_used: list[str] = Field(
        description="Class names of all risk controls instantiated in defaults.py"
    )

    verification: VerificationResult = Field(
        description="Results of lint and import verification"
    )
