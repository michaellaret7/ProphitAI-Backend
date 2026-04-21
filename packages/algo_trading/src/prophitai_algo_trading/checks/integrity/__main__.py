"""CLI entry — ``python -m prophitai_algo_trading.checks.integrity <strategy_id>``."""

import sys

from prophitai_algo_trading.checks.integrity.scaffold_check import main

sys.exit(main())
