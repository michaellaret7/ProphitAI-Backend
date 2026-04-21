"""Scan a constructed strategy directory for template-scaffold leakage.

Four pipeline-level failures produced the RAMD / LSDA / CIM / VCLR backtest
results: each ran to completion but executed template code — generic
EMA/RSI crossover — instead of the strategy's own logic, because the
construction agent left ``wiring.py`` / ``MANIFEST.json`` referencing the
template while only the indicator/signal files were customized. The
backtest engine cannot detect this; the validator cannot detect it either
until after the run finishes.

This module walks a strategy's development directory and returns a
structured list of violations. Run it BEFORE the backtest — any non-empty
result means the strategy would execute the wrong code and the run is a
guaranteed waste.

CLI usage::

    python -m prophitai_algo_trading.integrity.scaffold_check <strategy_id> \\
        [--root /home/user/strategies]

Exit code 1 + stdout lists violations when dirty; exit 0 + silent when clean.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


# ================================
# --> Helper funcs
# ================================


_BANNED_IMPORT_FRAGMENTS = (
    "strategies.template.",
    "from strategies.template ",
)

_BANNED_CLASS_NAMES = (
    "TemplateStrategy",
    "TemplateSignalModel",
    "TemplateIndicatorSuite",
    "TemplatePositionSizer",
    "TemplateStrategyConfig",
    "TemplateBacktestConfig",
    "TemplateSizingConfig",
    "TemplateRiskControlConfig",
)

_SKIP_PATH_FRAGMENTS = ("__pycache__", ".venv", "/tests/")


def _line_is_comment_or_docstring(line: str) -> bool:
    """Return True when the line is a comment — lets docs mention the name."""
    stripped = line.strip()

    return stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''")


def _scan_file_for_template_refs(py_file: Path) -> list[str]:
    """Return a list of violation messages found in ``py_file``."""
    violations: list[str] = []

    content = py_file.read_text(encoding="utf-8", errors="replace")

    for line_no, line in enumerate(content.splitlines(), start=1):
        if _line_is_comment_or_docstring(line):
            continue

        for fragment in _BANNED_IMPORT_FRAGMENTS:
            if fragment in line:
                violations.append(
                    f"{py_file.name}:{line_no} imports from template scaffold "
                    f"(contains {fragment!r})"
                )

        for class_name in _BANNED_CLASS_NAMES:
            marker = f" {class_name}"

            if marker in line or line.startswith(class_name) or f"({class_name}" in line:
                violations.append(
                    f"{py_file.name}:{line_no} references template class "
                    f"{class_name!r}"
                )

                break

    return violations


def _check_manifest(strategy_dir: Path, strategy_id: str) -> list[str]:
    """Return violations from the MANIFEST.json — missing or mismatched id."""
    violations: list[str] = []

    manifest_path = strategy_dir / "MANIFEST.json"

    if not manifest_path.exists():
        return [f"MANIFEST.json missing at {manifest_path}"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"MANIFEST.json is not valid JSON: {exc}"]

    manifest_id = manifest.get("strategy_id")

    if manifest_id is None:
        violations.append("MANIFEST.json missing 'strategy_id' field")
    elif manifest_id != strategy_id:
        violations.append(
            f"MANIFEST.json 'strategy_id' mismatch: "
            f"manifest has {manifest_id!r}, expected {strategy_id!r} "
            f"(this is the RAMD/VCLR failure mode — manifest was copied from a prior strategy)"
        )

    return violations


# ================================
# --> Public API
# ================================


@dataclass(frozen=True)
class IntegrityViolation:
    """One detected integrity problem. Attach path + message for logging."""

    path: str
    message: str


def check_scaffold_integrity(
    strategy_dir: Path | str,
    strategy_id: str,
) -> list[IntegrityViolation]:
    """Return all template-leakage violations for the given strategy directory.

    An empty list means the directory is clean and the strategy is safe
    to run. A non-empty list means the construction pipeline produced a
    strategy that would execute wrong code — refuse to run the backtest.

    Args:
        strategy_dir: Absolute path to the strategy directory
            (``strategies/development/<strategy_id>/``).
        strategy_id: The expected strategy id — used to verify the
            MANIFEST.json belongs to this strategy.
    """
    strategy_dir = Path(strategy_dir)

    if not strategy_dir.is_dir():
        return [IntegrityViolation(str(strategy_dir), "strategy directory does not exist")]

    violations: list[IntegrityViolation] = []

    for message in _check_manifest(strategy_dir, strategy_id):
        violations.append(IntegrityViolation(str(strategy_dir / "MANIFEST.json"), message))

    for py_file in strategy_dir.rglob("*.py"):
        if any(fragment in str(py_file) for fragment in _SKIP_PATH_FRAGMENTS):
            continue

        for message in _scan_file_for_template_refs(py_file):
            violations.append(IntegrityViolation(str(py_file.relative_to(strategy_dir)), message))

    return violations


def main(argv: list[str] | None = None) -> int:
    """CLI entry — exit 1 on any violation, 0 when clean."""
    parser = argparse.ArgumentParser(
        description="Scan a strategy directory for template-scaffold leakage."
    )

    parser.add_argument("strategy_id", help="Strategy id — matched against MANIFEST.strategy_id")
    parser.add_argument(
        "--root",
        default="/home/user/strategies",
        help="Repo root containing strategies/development/ (default: /home/user/strategies)",
    )

    args = parser.parse_args(argv)

    strategy_dir = Path(args.root) / "strategies" / "development" / args.strategy_id

    violations = check_scaffold_integrity(strategy_dir, args.strategy_id)

    if not violations:
        print(f"[scaffold_check] OK — {args.strategy_id} is clean")
        return 0

    print(f"[scaffold_check] FAILED — {len(violations)} violation(s) in {args.strategy_id}:", file=sys.stderr)

    for v in violations:
        print(f"  {v.path}: {v.message}", file=sys.stderr)

    return 1
