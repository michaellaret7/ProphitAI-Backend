"""Output models for the Indicator Builder agent.

Defines the structured result that the Indicator Builder produces after
writing indicator code files to the sandbox. Consumed by the Signal+Strategy
Builder to know exact class names, file paths, and output columns.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ================================
# --> Helper models
# ================================


class BuiltIndicatorFile(BaseModel):
    """A single indicator file written by the builder."""

    file_path: str = Field(
        description="Relative path within the sandbox repo "
        "(e.g. 'strategies/development/omfm_15/indicators/ofi_proxy.py')"
    )
    class_name: str = Field(
        description="Primary class defined in the file (e.g. 'OFIProxyIndicator')"
    )
    registry_key: Optional[str] = Field(
        None,
        description="Registry key if registered in IndicatorRegistry (e.g. 'ofi_proxy')",
    )
    output_columns: list[str] = Field(
        description="Columns this indicator adds to the DataFrame"
    )
    is_custom: bool = Field(
        description="True if this is a custom BaseIndicator subclass"
    )


class BuiltDerivedFeature(BaseModel):
    """A derived feature column produced by the custom.py function."""

    column_name: str = Field(description="Output column name")
    depends_on: list[str] = Field(
        description="Indicator output columns this feature reads"
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


class IndicatorBuildResult(BaseModel):
    """Complete output from the Indicator Builder agent.

    Consumed by the Signal+Strategy Builder to know exactly what
    indicator classes exist, where they live, and what columns they produce.
    """

    strategy_id: str = Field(
        description="Strategy identifier (e.g. 'omfm_15')"
    )
    strategy_name: str = Field(
        description="Human-readable name (e.g. 'OMFM15')"
    )

    suite_file: str = Field(description="Path to the suite.py file")
    suite_class_name: str = Field(
        description="Name of the BaseIndicatorSuite subclass"
    )

    custom_file: str = Field(
        description="Path to the custom.py derived features file"
    )
    derived_features_function: str = Field(
        description="Name of the derived features function "
        "(e.g. 'add_omfm15_indicator_features')"
    )

    init_file: str = Field(description="Path to the __init__.py exports file")

    indicator_files: list[BuiltIndicatorFile] = Field(
        description="All indicator files written (std_lib specs + custom implementations)"
    )
    derived_features: list[BuiltDerivedFeature] = Field(
        default_factory=list,
        description="Derived feature columns produced by custom.py",
    )

    all_output_columns: list[str] = Field(
        description="Complete list of all columns available after the indicator "
        "pipeline runs (indicators + derived features)"
    )

    verification: VerificationResult = Field(
        description="Results of lint and import verification"
    )
