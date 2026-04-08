"""Worker registry — maps worker type names to WorkerSpec definitions.

Projects register their scoped worker specs at import time:

    from prophitai_atlas.models.worker_registry import WORKER_REGISTRY
    from prophitai_atlas.models.worker_spec import WorkerSpec

    WORKER_REGISTRY["equity_researcher"] = WorkerSpec(
        name="equity_researcher",
        system_prompt="You are a senior equity analyst...",
        tools=frozenset({"ticker_performance", "ticker_risk", "get_ticker_info"}),
    )
"""

from typing import Dict

from prophitai_atlas.models.worker_spec import WorkerSpec

WORKER_REGISTRY: Dict[str, WorkerSpec] = {}
