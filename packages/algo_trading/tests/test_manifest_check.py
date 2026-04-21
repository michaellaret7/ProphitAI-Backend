"""Smoke tests for the manifest_check validator.

Builds synthetic strategy directories that trigger each rule (M001-M009),
runs the checker, and asserts the expected error codes surface. Also
verifies a deliberately-clean manifest produces zero violations.

Run: ``python packages/algo_trading/tests/test_manifest_check.py``
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prophitai_algo_trading.checks.manifest import (
    ManifestViolation,
    check_manifest_compatibility,
)


# ================================
# --> Helper funcs
# ================================


def _write_strategy(root: Path, manifest: dict, files: dict[str, str]) -> Path:
    """Materialize a strategy directory with MANIFEST.json + source files."""
    strategy_dir = root / "strategy"
    strategy_dir.mkdir(parents=True, exist_ok=True)

    (strategy_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

    for rel_path, source in files.items():
        target = strategy_dir / rel_path

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)

    return strategy_dir


def _codes(violations: list[ManifestViolation]) -> list[str]:
    return [v.code for v in violations]


def _assert_has(violations: list[ManifestViolation], code: str) -> None:
    assert code in _codes(violations), (
        f"expected {code} in violations, got {_codes(violations)}:\n"
        + "\n".join(f"  {v.code}: {v.message}" for v in violations)
    )


def _assert_none(violations: list[ManifestViolation]) -> None:
    errors = [v for v in violations if v.severity == "error"]
    assert not errors, (
        "expected no error violations, got:\n"
        + "\n".join(f"  {v.code}: {v.message}" for v in errors)
    )


# ================================
# --> Fixtures
# ================================


_MINIMAL_CLEAN_MANIFEST: dict = {
    "strategy_id": "clean_rsi_mr",
    "strategy_name": "Clean RSI MR",
    "indicators": [
        {
            "registry_key": "rsi",
            "class_name": "RSI",
            "is_custom": False,
            "file": None,
            "params": [{"key": "window", "value_num": 14}],
            "input_columns": ["close"],
            "output_columns": ["rsi", "rsi_avg_gain", "rsi_avg_loss"],
            "scope": "shared",
            "data_requirements": [],
        },
    ],
    "derived_features": [],
    "signals": {
        "class_name": "RsiMrSignalModel",
        "required_columns": ["rsi", "close"],
        "enrich_columns": [],
        "long_entry": {"conditions": ["rsi < 30"], "primitives_used": []},
        "long_exit": {"conditions": ["rsi > 50"], "primitives_used": []},
        "short_entry": {"conditions": [], "primitives_used": []},
        "short_exit": {"conditions": [], "primitives_used": []},
        "scoring_method": "abs(rsi - 30)",
    },
    "config_defaults": {
        "strategy": [],
        "sizing": [],
        "risk": [],
        "backtest": [{"key": "ftc", "value_num": 0}],
        "live": [],
    },
}

_CLEAN_WIRING_PY = (
    "from prophitai_algo_trading.sizing.std_lib.wrappers.gross_exposure import GrossExposureSizer\n"
    "from prophitai_algo_trading.sizing.std_lib.equity import PercentOfEquitySizer\n\n"
    "def build_sizer():\n"
    "    base = PercentOfEquitySizer(pct=0.05)\n"
    "    return GrossExposureSizer(base_sizer=base, target_gross_pct=1.0, max_name_pct=0.1)\n"
)


# ================================
# --> Tests
# ================================


def test_clean_manifest_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            _MINIMAL_CLEAN_MANIFEST,
            {
                "wiring.py": _CLEAN_WIRING_PY,
                "run_vectorized_backtest.py": "# runner placeholder\n",
            },
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_none(violations)
    print(f"  clean manifest: {len(violations)} violations (expected 0)")


def test_m001_unknown_data_kind() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"][0]["data_requirements"] = [
        {
            "kind": "options_chain",
            "attrs_key": "chain",
            "scope": "per_ticker",
            "params": [],
            "min_coverage": 0.8,
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {"wiring.py": _CLEAN_WIRING_PY},
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M001_UNKNOWN_DATA_KIND")
    print(f"  M001 detected: options_chain kind rejected")


def test_m002_missing_required_params() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"][0]["data_requirements"] = [
        {
            "kind": "commodity",
            "attrs_key": "vix",
            "scope": "shared",
            "params": [],
            "min_coverage": 1.0,
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {"wiring.py": _CLEAN_WIRING_PY},
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M002_MISSING_REQUIRED_PARAMS")
    print(f"  M002 detected: commodity without symbol rejected")


def test_m003_symbol_kind_mismatch() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"][0]["data_requirements"] = [
        {
            "kind": "commodity",
            "attrs_key": "spy",
            "scope": "shared",
            "params": [{"key": "symbol", "value_str": "SPY"}],
            "min_coverage": 1.0,
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {"wiring.py": _CLEAN_WIRING_PY},
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M003_SYMBOL_KIND_MISMATCH")
    print(f"  M003 detected: SPY under commodity rejected")


def test_m004_column_unproduced() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["signals"]["required_columns"] = ["rsi", "does_not_exist", "close"]

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {"wiring.py": _CLEAN_WIRING_PY},
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M004_COLUMN_UNPRODUCED")
    print(f"  M004 detected: orphaned column rejected")


def test_m005_broadcast_unused() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"][0]["data_requirements"] = [
        {
            "kind": "equity_price",
            "attrs_key": "spy",
            "scope": "shared",
            "params": [{"key": "symbol", "value_str": "SPY"}],
            "min_coverage": 1.0,
            "broadcast_as": "spy_close_unused",
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {"wiring.py": _CLEAN_WIRING_PY},
        )

        violations = check_manifest_compatibility(strategy_dir)

    codes = [v.code for v in violations]
    assert "M005_BROADCAST_UNUSED" in codes, f"expected M005 warning, got {codes}"
    # severity should be warning, not error
    m005 = next(v for v in violations if v.code == "M005_BROADCAST_UNUSED")
    assert m005.severity == "warning", f"M005 should be warning, got {m005.severity}"
    print(f"  M005 detected: unused broadcast flagged as warning")


def test_m006_universe_returns_misuse() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"].append({
        "registry_key": None,
        "class_name": "CrossSectionalRank",
        "is_custom": True,
        "file": "indicators/cross_sectional_rank.py",
        "params": [],
        "input_columns": [],
        "output_columns": ["cs_rank"],
        "scope": "shared",
        "data_requirements": [],
    })

    custom_source = (
        "import pandas as pd\n"
        "from prophitai_algo_trading.indicators import BaseIndicator\n\n"
        "class CrossSectionalRank(BaseIndicator):\n"
        "    def calculate(self):\n"
        "        # Bug: groupby on per-ticker frame collapses to single-row groups\n"
        "        self.df['cs_rank'] = self.df.groupby(['date', 'sector']).rank(pct=True)\n"
        "        return self.df\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {
                "wiring.py": _CLEAN_WIRING_PY,
                "indicators/cross_sectional_rank.py": custom_source,
                "indicators/__init__.py": "",
            },
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M006_UNIVERSE_RETURNS_MISUSE")
    print(f"  M006 detected: groupby without universe_returns rejected")


def test_m006_universe_returns_declared_passes() -> None:
    # Same groupby pattern but WITH universe_returns declared → no M006
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"].append({
        "registry_key": None,
        "class_name": "UniverseRank",
        "is_custom": True,
        "file": "indicators/universe_rank.py",
        "params": [],
        "input_columns": [],
        "output_columns": ["univ_rank"],
        "scope": "shared",
        "data_requirements": [
            {
                "kind": "universe_returns",
                "attrs_key": "universe_returns",
                "scope": "shared",
                "params": [],
                "min_coverage": 1.0,
            }
        ],
    })

    custom_source = (
        "import pandas as pd\n"
        "from prophitai_algo_trading.indicators import BaseIndicator\n\n"
        "class UniverseRank(BaseIndicator):\n"
        "    def calculate(self):\n"
        "        panel = self.df.attrs['universe_returns']\n"
        "        # Using groupby on the shared panel is allowed because we DECLARED universe_returns\n"
        "        ranks = panel.groupby(['date']).mean()\n"
        "        self.df['univ_rank'] = ranks.reindex(self.df.index)\n"
        "        return self.df\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {
                "wiring.py": _CLEAN_WIRING_PY,
                "indicators/universe_rank.py": custom_source,
                "indicators/__init__.py": "",
            },
        )

        violations = check_manifest_compatibility(strategy_dir)

    codes = [v.code for v in violations]
    assert "M006_UNIVERSE_RETURNS_MISUSE" not in codes, (
        f"M006 should NOT fire when universe_returns is declared. Got: {codes}"
    )
    print(f"  M006 not triggered when universe_returns is properly declared")


def test_m007_ftc_vectorized() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["config_defaults"]["backtest"] = [{"key": "ftc", "value_num": 1.5}]

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {
                "wiring.py": _CLEAN_WIRING_PY,
                "run_vectorized_backtest.py": "# present\n",
            },
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M007_FTC_VECTORIZED")
    print(f"  M007 detected: ftc=1.5 with vectorized runner rejected")


def test_m008_missing_gross_exposure_wrap() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))

    bad_wiring = (
        "from prophitai_algo_trading.sizing.std_lib.equity import PercentOfEquitySizer\n\n"
        "def build_sizer():\n"
        "    return PercentOfEquitySizer(pct=0.05)\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {"wiring.py": bad_wiring},
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M008_MISSING_GROSS_EXPOSURE_WRAP")
    print(f"  M008 detected: wiring without GrossExposureSizer rejected")


def test_m009_attrs_wipe_before_read() -> None:
    manifest = json.loads(json.dumps(_MINIMAL_CLEAN_MANIFEST))
    manifest["indicators"].append({
        "registry_key": None,
        "class_name": "AttrsWiper",
        "is_custom": True,
        "file": "indicators/attrs_wiper.py",
        "params": [],
        "input_columns": [],
        "output_columns": ["wiped"],
        "scope": "shared",
        "data_requirements": [],
    })

    custom_source = (
        "import pandas as pd\n"
        "from prophitai_algo_trading.indicators import BaseIndicator\n\n"
        "class AttrsWiper(BaseIndicator):\n"
        "    def calculate(self):\n"
        "        attrs = dict(self.df.attrs)\n"
        "        self.df.attrs = {}\n"
        "        # This read sees an empty dict because of the wipe above\n"
        "        meta = self.df.attrs.get('ticker_meta')\n"
        "        self.df['wiped'] = 1.0\n"
        "        return self.df\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        strategy_dir = _write_strategy(
            Path(tmp),
            manifest,
            {
                "wiring.py": _CLEAN_WIRING_PY,
                "indicators/attrs_wiper.py": custom_source,
                "indicators/__init__.py": "",
            },
        )

        violations = check_manifest_compatibility(strategy_dir)

    _assert_has(violations, "M009_ATTRS_WIPE_BEFORE_READ")
    print(f"  M009 detected: attrs wipe before read rejected")


# ================================
# --> Runner
# ================================


def main() -> int:
    tests = [
        test_clean_manifest_passes,
        test_m001_unknown_data_kind,
        test_m002_missing_required_params,
        test_m003_symbol_kind_mismatch,
        test_m004_column_unproduced,
        test_m005_broadcast_unused,
        test_m006_universe_returns_misuse,
        test_m006_universe_returns_declared_passes,
        test_m007_ftc_vectorized,
        test_m008_missing_gross_exposure_wrap,
        test_m009_attrs_wipe_before_read,
    ]

    failed = 0

    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"[PASS] {name}")

        except AssertionError as exc:
            print(f"[FAIL] {name}: {exc}")
            failed += 1

        except Exception as exc:
            print(f"[ERROR] {name}: {type(exc).__name__}: {exc}")
            failed += 1

    total = len(tests)

    print(f"\n{total - failed}/{total} passed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
