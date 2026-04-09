"""Config contract tests.

Validates that a strategy's config class is a frozen dataclass with
sensible defaults.  All tests skip when ``manifest.config_class`` is None.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from prophitai_algo_trading.testing.manifest import StrategyTestManifest


class ConfigContract:
    """Mixin — inherit and set ``manifest`` to get config contract tests."""

    manifest: StrategyTestManifest

    def test_defaults_instantiate(self) -> None:
        """Config class instantiates with default values (no args)."""
        if self.manifest.config_class is None:
            pytest.skip("No config_class declared in manifest")

        config = self.manifest.config_class()

        assert config is not None

    def test_frozen(self) -> None:
        """Config is a frozen dataclass — mutation raises an error."""
        if self.manifest.config_class is None:
            pytest.skip("No config_class declared in manifest")

        config = self.manifest.config_class()

        assert dataclasses.is_dataclass(config), (
            f"{self.manifest.config_class.__name__} is not a dataclass"
        )
        assert config.__dataclass_params__.frozen, (  # type: ignore[union-attr]
            f"{self.manifest.config_class.__name__} is not frozen"
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            config._test_mutation = True  # type: ignore[attr-defined]

    def test_numeric_period_params_positive(self) -> None:
        """Numeric fields with 'period' in the name have positive defaults."""
        if self.manifest.config_class is None:
            pytest.skip("No config_class declared in manifest")

        config = self.manifest.config_class()

        for field in dataclasses.fields(config):
            val = getattr(config, field.name)

            if not isinstance(val, (int, float)):
                continue

            if "period" not in field.name.lower():
                continue

            assert val > 0, (
                f"Config field '{field.name}' = {val} should be positive"
            )
