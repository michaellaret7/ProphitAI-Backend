"""Structural-compatibility checks for a constructed strategy package.

Runs after the architect writes ``MANIFEST.json`` and before the build
handoff. Rejects designs the engine cannot execute — unknown
``DataRequirement`` kinds, orphaned signal columns, cross-sectional code
written against a per-ticker frame, missing ``GrossExposureSizer`` wrap,
``ftc`` configured for a vectorized runner, and attrs-wipe bugs of the
kind that produced today's zero-trade sector-rotation strategy.

Each rule emits a ``ManifestViolation`` with a stable error code. The
framework reference doc (``documentation/framework_reference.md (Strategies repo)``)
documents the full error-code index alongside the fixes.

Entry points:
    ``check_manifest_compatibility(strategy_dir) -> list[ManifestViolation]``
    ``python -m prophitai_algo_trading.checks.manifest <strategy_id>``
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from prophitai_algo_trading.checks.manifest.violations import ManifestViolation


# ================================
# --> Helper funcs
# ================================


OHLCV_COLUMNS: frozenset[str] = frozenset({"open", "high", "low", "close", "volume"})

# Reason: pulled from DataRequirement.__post_init__ whitelist so both the
# dataclass and the manifest validator reject the same symbols. Keep in
# sync with data_requirements.py.
_EQUITY_SYMBOLS_BLOCKED_UNDER_COMMODITY: frozenset[str] = frozenset({
    "SPY", "VOO", "IVV", "QQQ", "QQQM", "DIA", "IWM", "IWB", "RSP", "VTI",
    "XLC", "XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLRE", "XLK", "XLU",
    "MTUM", "QUAL", "VLUE", "SIZE", "USMV", "SPLV",
    "EFA", "EEM", "VEA", "VWO", "AGG", "BND", "TLT", "IEF", "SHY", "HYG", "LQD",
})

# kind -> list of required param keys
_KIND_REQUIRED_PARAMS: dict[str, tuple[str, ...]] = {
    "commodity": ("symbol",),
    "equity_price": ("symbol",),
    "economic_indicator": ("indicator",),
    "government_bond_rates": ("country",),
    "economic_calendar": ("country",),
}

# Reason: fallback when importing build_default_resolver fails (e.g. in a
# test environment without the data package installed). Kept narrow so
# drift from the live registry still surfaces — M001 uses the live list
# when available and this as a safety net.
_FALLBACK_KNOWN_KINDS: frozenset[str] = frozenset({
    "ticker_meta", "fundamentals", "financial_ratios_ttm", "financial_ratios",
    "commodity", "equity_price", "universe_returns", "economic_indicator",
    "government_bond_rates", "economic_calendar", "earnings_calendar",
})

# Reason: naive cross-sectional patterns that only work when given a
# multi-ticker panel. The per-ticker engine hands the indicator one
# ticker, so these collapse silently. Match the three most common forms.
_CROSS_SECTIONAL_GROUPBY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"""\.groupby\(\s*\[\s*['"]date['"]\s*,"""),
    re.compile(r"""\.groupby\(\s*\[\s*['"]date['"]\s*\]"""),
    re.compile(r"""\.groupby\(\s*['"]date['"]\s*\)"""),
)

_ATTRS_WIPE_PATTERN: re.Pattern[str] = re.compile(
    r"""self\.df\.attrs\s*=\s*\{\s*\}|self\.df\.attrs\.clear\(\s*\)"""
)

_ATTRS_READ_PATTERN: re.Pattern[str] = re.compile(
    r"""self\.df\.attrs\.get\(|self\.df\.attrs\["""
)


def _param_value(param: dict[str, Any]) -> Any:
    """Extract the single non-null value from a ConfigParam-shaped dict."""
    for key in ("value_str", "value_num", "value_bool", "value_list", "value_map"):
        if param.get(key) is not None:
            return param[key]
    return None


def _params_as_mapping(params: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Flatten a ConfigParam list into a simple ``{key: value}`` dict."""
    if not params:
        return {}
    return {p.get("key"): _param_value(p) for p in params if p.get("key")}


def _known_data_kinds() -> frozenset[str]:
    """Return the live resolver registry's kinds, falling back when unavailable."""
    try:
        from prophitai_algo_trading.data.resolver import build_default_resolver

        resolver = build_default_resolver()
        # Reason: DataResolver exposes providers via its internal dict; fall
        # back to the snapshot if the attribute name ever changes.
        registry = getattr(resolver, "_providers", None)

        if isinstance(registry, dict) and registry:
            return frozenset(registry.keys())

    except Exception:
        pass

    return _FALLBACK_KNOWN_KINDS


def _load_manifest(strategy_dir: Path) -> tuple[dict[str, Any] | None, list[ManifestViolation]]:
    """Load MANIFEST.json. Returns (manifest, violations-for-load-failure)."""
    manifest_path = strategy_dir / "MANIFEST.json"

    if not manifest_path.exists():
        return None, [ManifestViolation(
            code="M000_MISSING_MANIFEST",
            severity="error",
            path="MANIFEST.json",
            message=f"MANIFEST.json not found at {manifest_path}. Architect must write it before validator runs.",
        )]

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8")), []

    except json.JSONDecodeError as exc:
        return None, [ManifestViolation(
            code="M000_MALFORMED_MANIFEST",
            severity="error",
            path="MANIFEST.json",
            message=f"MANIFEST.json is not valid JSON: {exc}",
        )]


def _iter_data_requirements(manifest: dict[str, Any]) -> Iterable[tuple[int, dict[str, Any]]]:
    """Yield (indicator_index, data_requirement) pairs from every indicator."""
    for idx, indicator in enumerate(manifest.get("indicators", []) or []):
        for req in indicator.get("data_requirements", []) or []:
            yield idx, req


def _collect_produced_columns(manifest: dict[str, Any]) -> set[str]:
    """Every column the framework will produce at runtime."""
    produced: set[str] = set(OHLCV_COLUMNS)

    for indicator in manifest.get("indicators", []) or []:
        for col in indicator.get("output_columns", []) or []:
            produced.add(col)

    for feature in manifest.get("derived_features", []) or []:
        name = feature.get("column_name")

        if name:
            produced.add(name)

    for _, req in _iter_data_requirements(manifest):
        broadcast_as = req.get("broadcast_as")

        if broadcast_as:
            produced.add(broadcast_as)

    signals = manifest.get("signals") or {}

    for col in signals.get("enrich_columns", []) or []:
        produced.add(col)

    return produced


def _signal_column_references(manifest: dict[str, Any]) -> set[str]:
    """Every column the signal model declares as a required input."""
    signals = manifest.get("signals") or {}
    return set(signals.get("required_columns", []) or [])


def _scan_custom_indicator_files(
    strategy_dir: Path, manifest: dict[str, Any]
) -> list[tuple[str, Path, str, list[str]]]:
    """Return (class_name, path, source, declared_data_kinds) for each custom indicator."""
    hits: list[tuple[str, Path, str, list[str]]] = []

    for indicator in manifest.get("indicators", []) or []:
        if not indicator.get("is_custom"):
            continue

        rel_file = indicator.get("file")

        if not rel_file:
            continue

        path = (strategy_dir / rel_file).resolve()

        if not path.exists():
            continue

        source = path.read_text(encoding="utf-8", errors="replace")
        declared_kinds = [
            req.get("kind", "")
            for req in indicator.get("data_requirements", []) or []
        ]

        hits.append((indicator.get("class_name", path.name), path, source, declared_kinds))

    return hits


# ================================
# --> Individual checks
# ================================


def _check_m001_unknown_kind(
    manifest: dict[str, Any], known_kinds: frozenset[str]
) -> list[ManifestViolation]:
    violations: list[ManifestViolation] = []

    for idx, req in _iter_data_requirements(manifest):
        kind = req.get("kind")

        if kind not in known_kinds:
            violations.append(ManifestViolation(
                code="M001_UNKNOWN_DATA_KIND",
                severity="error",
                path="MANIFEST.json",
                message=(
                    f"indicators[{idx}].data_requirements references unknown kind={kind!r}. "
                    f"Registered kinds: {sorted(known_kinds)}. "
                    f"Drop the requirement, pick an existing kind, or register a provider."
                ),
            ))

    return violations


def _check_m002_missing_required_params(
    manifest: dict[str, Any],
) -> list[ManifestViolation]:
    violations: list[ManifestViolation] = []

    for idx, req in _iter_data_requirements(manifest):
        kind = req.get("kind")
        required = _KIND_REQUIRED_PARAMS.get(kind, ())

        if not required:
            continue

        params = _params_as_mapping(req.get("params"))
        missing = [key for key in required if not params.get(key)]

        if missing:
            violations.append(ManifestViolation(
                code="M002_MISSING_REQUIRED_PARAMS",
                severity="error",
                path="MANIFEST.json",
                message=(
                    f"indicators[{idx}].data_requirements kind={kind!r} missing required "
                    f"param(s): {missing}. See the data catalog in "
                    f"documentation/framework_reference.md (Strategies repo)."
                ),
            ))

    return violations


def _check_m003_symbol_kind_mismatch(
    manifest: dict[str, Any],
) -> list[ManifestViolation]:
    violations: list[ManifestViolation] = []

    for idx, req in _iter_data_requirements(manifest):
        if req.get("kind") != "commodity":
            continue

        params = _params_as_mapping(req.get("params"))
        symbol = str(params.get("symbol", "")).upper()

        if symbol in _EQUITY_SYMBOLS_BLOCKED_UNDER_COMMODITY:
            violations.append(ManifestViolation(
                code="M003_SYMBOL_KIND_MISMATCH",
                severity="error",
                path="MANIFEST.json",
                message=(
                    f"indicators[{idx}].data_requirements declares kind='commodity' "
                    f"with symbol={symbol!r} — equities/ETFs must use kind='equity_price'. "
                    f"The commodity provider silently returns no data for equity symbols."
                ),
            ))

    return violations


def _check_m004_column_unproduced(
    manifest: dict[str, Any],
) -> list[ManifestViolation]:
    produced = _collect_produced_columns(manifest)
    referenced = _signal_column_references(manifest)
    orphans = sorted(referenced - produced)

    if not orphans:
        return []

    return [ManifestViolation(
        code="M004_COLUMN_UNPRODUCED",
        severity="error",
        path="MANIFEST.json",
        message=(
            f"signals.required_columns references column(s) with no producer: {orphans}. "
            f"Every column must come from an indicator output_columns, a derived feature, "
            f"a broadcast_as on a DataRequirement, or standard OHLCV."
        ),
    )]


def _check_m005_broadcast_unused(
    manifest: dict[str, Any],
) -> list[ManifestViolation]:
    violations: list[ManifestViolation] = []

    # Reason: a broadcast is "used" if the column name appears in required_columns,
    # any derived_feature.depends_on, any indicator.input_columns, or any signal condition.
    used: set[str] = set()
    signals = manifest.get("signals") or {}
    used.update(signals.get("required_columns", []) or [])

    for feature in manifest.get("derived_features", []) or []:
        used.update(feature.get("depends_on", []) or [])

    for indicator in manifest.get("indicators", []) or []:
        used.update(indicator.get("input_columns", []) or [])

    for cond_key in ("long_entry", "long_exit", "short_entry", "short_exit"):
        cond = signals.get(cond_key) or {}

        for expr in cond.get("conditions", []) or []:
            # naive token sweep is fine — condition strings are short.
            used.update(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", str(expr)))

    for idx, req in _iter_data_requirements(manifest):
        broadcast_as = req.get("broadcast_as")

        if not broadcast_as:
            continue

        if broadcast_as not in used:
            violations.append(ManifestViolation(
                code="M005_BROADCAST_UNUSED",
                severity="warning",
                path="MANIFEST.json",
                message=(
                    f"indicators[{idx}].data_requirements declares broadcast_as={broadcast_as!r} "
                    f"but no signal / derived feature / indicator reads that column. "
                    f"Likely a rename that was forgotten — remove the broadcast or wire the read."
                ),
            ))

    return violations


def _check_m006_universe_returns_misuse(
    strategy_dir: Path, manifest: dict[str, Any]
) -> list[ManifestViolation]:
    violations: list[ManifestViolation] = []

    for class_name, path, source, declared_kinds in _scan_custom_indicator_files(
        strategy_dir, manifest
    ):
        has_groupby = any(pat.search(source) for pat in _CROSS_SECTIONAL_GROUPBY_PATTERNS)

        if not has_groupby:
            continue

        if "universe_returns" in declared_kinds:
            continue

        rel = path.relative_to(strategy_dir) if path.is_relative_to(strategy_dir) else path

        violations.append(ManifestViolation(
            code="M006_UNIVERSE_RETURNS_MISUSE",
            severity="error",
            path=str(rel),
            message=(
                f"{class_name} uses groupby(['date', ...]) on the per-ticker DataFrame. "
                f"That frame holds one ticker, so groups collapse and signals die silently. "
                f"To compute universe-aware features, declare "
                f"DataRequirement(kind='universe_returns', scope='shared') and read the panel "
                f"from df.attrs — see the worked example in "
                f"documentation/framework_reference.md (Strategies repo)."
            ),
        ))

    return violations


def _check_m007_ftc_vectorized(
    strategy_dir: Path, manifest: dict[str, Any]
) -> list[ManifestViolation]:
    config_defaults = manifest.get("config_defaults") or {}
    backtest_params = _params_as_mapping(config_defaults.get("backtest"))

    # Reason: architect may use either "ftc" or "cost_ftc"; accept both.
    ftc_value: Any = backtest_params.get("ftc")

    if ftc_value in (None, 0, 0.0):
        ftc_value = backtest_params.get("cost_ftc")

    if ftc_value in (None, 0, 0.0):
        return []

    try:
        ftc_float = float(ftc_value)
    except (TypeError, ValueError):
        return []

    if ftc_float == 0.0:
        return []

    if not (strategy_dir / "run_vectorized_backtest.py").exists():
        return []

    return [ManifestViolation(
        code="M007_FTC_VECTORIZED",
        severity="error",
        path="MANIFEST.json",
        message=(
            f"config_defaults.backtest sets ftc={ftc_float} but run_vectorized_backtest.py "
            f"is present. VectorizedBacktestEngine rejects ftc != 0 at engine init. "
            f"Use event-driven for fixed costs or set ftc=0 for vectorized runs."
        ),
    )]


def _check_m008_missing_gross_exposure_wrap(
    strategy_dir: Path,
) -> list[ManifestViolation]:
    wiring_path = strategy_dir / "wiring.py"

    if not wiring_path.exists():
        return []

    source = wiring_path.read_text(encoding="utf-8", errors="replace")

    if "GrossExposureSizer(" not in source:
        return [ManifestViolation(
            code="M008_MISSING_GROSS_EXPOSURE_WRAP",
            severity="error",
            path="wiring.py",
            message=(
                "GrossExposureSizer is not constructed in wiring.py. Every strategy — "
                "long-only included — must wrap its sizer chain in GrossExposureSizer as "
                "the outermost layer, or capital chronically under-deploys."
            ),
        )]

    return []


def _check_m009_attrs_wipe_before_read(
    strategy_dir: Path, manifest: dict[str, Any]
) -> list[ManifestViolation]:
    violations: list[ManifestViolation] = []

    for class_name, path, source, _kinds in _scan_custom_indicator_files(
        strategy_dir, manifest
    ):
        # Reason: we fire only when wipe appears BEFORE a read. A read before
        # the wipe is safe; a read after is the today's-bug pattern.
        wipe_match = _ATTRS_WIPE_PATTERN.search(source)

        if not wipe_match:
            continue

        read_match = _ATTRS_READ_PATTERN.search(source, pos=wipe_match.end())

        if not read_match:
            continue

        rel = path.relative_to(strategy_dir) if path.is_relative_to(strategy_dir) else path

        violations.append(ManifestViolation(
            code="M009_ATTRS_WIPE_BEFORE_READ",
            severity="error",
            path=str(rel),
            message=(
                f"{class_name} clears self.df.attrs and a later helper reads from attrs. "
                f"The reads see an empty dict and return NaN silently. Restore attrs before "
                f"attrs-dependent code runs, or stash the dict in a local and pass it "
                f"explicitly to helpers."
            ),
        ))

    return violations


# ================================
# --> Public API
# ================================


def check_manifest_compatibility(
    strategy_dir: Path | str,
) -> list[ManifestViolation]:
    """Run every manifest-check rule against a constructed strategy directory.

    Args:
        strategy_dir: Absolute path to the strategy directory that contains
            ``MANIFEST.json``, the indicator / signal / wiring files, and
            the runner scripts — the sandbox layout produced by the
            construction agents.

    Returns:
        A list of ``ManifestViolation`` records. An empty list means the
        strategy passed every check. A non-empty list with any
        ``severity == "error"`` record means the build should not proceed.
    """
    strategy_dir = Path(strategy_dir)

    if not strategy_dir.is_dir():
        return [ManifestViolation(
            code="M000_MISSING_STRATEGY_DIR",
            severity="error",
            path=str(strategy_dir),
            message=f"Strategy directory does not exist: {strategy_dir}",
        )]

    manifest, load_violations = _load_manifest(strategy_dir)

    if manifest is None:
        return load_violations

    known_kinds = _known_data_kinds()

    violations: list[ManifestViolation] = []
    violations.extend(_check_m001_unknown_kind(manifest, known_kinds))
    violations.extend(_check_m002_missing_required_params(manifest))
    violations.extend(_check_m003_symbol_kind_mismatch(manifest))
    violations.extend(_check_m004_column_unproduced(manifest))
    violations.extend(_check_m005_broadcast_unused(manifest))
    violations.extend(_check_m006_universe_returns_misuse(strategy_dir, manifest))
    violations.extend(_check_m007_ftc_vectorized(strategy_dir, manifest))
    violations.extend(_check_m008_missing_gross_exposure_wrap(strategy_dir))
    violations.extend(_check_m009_attrs_wipe_before_read(strategy_dir, manifest))

    return violations
