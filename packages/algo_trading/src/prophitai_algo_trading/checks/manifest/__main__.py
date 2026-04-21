"""CLI entry point: ``python -m prophitai_algo_trading.checks.manifest <strategy_id>``.

Exit 0 + silent when clean. Exit 1 + JSON violations on stdout when dirty.
Use as a pre-flight in the validator and as a self-check after the
architect writes ``MANIFEST.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prophitai_algo_trading.checks.manifest.checker import (
    check_manifest_compatibility,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check a constructed strategy directory for structural "
            "incompatibilities with the algo_trading framework."
        )
    )

    parser.add_argument(
        "strategy_id",
        help="Strategy id — resolves to strategies/development/<strategy_id>/",
    )
    parser.add_argument(
        "--root",
        default="/home/user/strategies",
        help="Repo root containing strategies/development/ (default: /home/user/strategies)",
    )

    args = parser.parse_args(argv)

    strategy_dir = Path(args.root) / "strategies" / "development" / args.strategy_id

    violations = check_manifest_compatibility(strategy_dir)

    if not violations:
        print(f"[manifest_check] OK — {args.strategy_id} passed every rule")
        return 0

    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    payload = {
        "strategy_id": args.strategy_id,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "violations": [v.as_dict() for v in violations],
    }

    print(json.dumps(payload, indent=2))

    if errors:
        print(
            f"[manifest_check] FAILED — {len(errors)} error(s), {len(warnings)} warning(s)",
            file=sys.stderr,
        )

        return 1

    print(
        f"[manifest_check] OK with warnings — {len(warnings)} warning(s), no errors",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
