"""Entry point — runs the full strategy end-to-end.

Wires up sys.path (so the ``test_strategy`` package is importable as a
package), loads data, builds the algorithm, runs the backtest, grades.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \\
        packages/algo_trading/tests/test_strategy/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Reason: add packages/algo_trading/tests/ to sys.path so
# ``test_strategy`` is importable as a package. Also add the algo
# trading src/ since the file may be invoked from the repo root.
_TESTS_ROOT = Path(__file__).resolve().parents[1]
_PKG_SRC = _TESTS_ROOT.parent / "src"

for path in (_PKG_SRC, _TESTS_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from prophitai_algo_trading import Backtest, CostModel

from test_strategy.algorithm import build_algorithm
from test_strategy.grading import grade
from test_strategy.universe import INITIAL_CAPITAL, SECTOR_PAIRS, load_data


#     ================================
# --> Main
#     ================================

def test_strategy_end_to_end() -> None:
    print("\n=== Multi-factor 150-ticker strategy ===")

    data = load_data()
    algo = build_algorithm()

    print(f"\n  {len(algo.alphas)} alphas: {[a.name for a in algo.alphas]}")
    print(f"  max_lookback (warmup bars): {algo.max_lookback}")
    print(f"  pair alpha trading: {len(SECTOR_PAIRS)} cointegration pairs")

    engine = Backtest(
        algo,
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(ptc=0.0001, ftc=1.0),
    )

    result = engine.run(data)

    grade(result)


def main() -> None:
    test_strategy_end_to_end()
    print("\nStrategy backtest completed.")


if __name__ == "__main__":
    main()
