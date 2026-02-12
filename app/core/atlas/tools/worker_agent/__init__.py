"""Worker agent tool - delegates focused tasks to a WorkerAgent."""

from app.core.atlas.tools.worker_agent.setup import (
    DEPLOY_WORKER_TOOL,
    DEPLOY_WORKER_DESCRIPTION,
    DEPLOY_WORKER_PARAMETERS,
    AVAILABLE_TOOLS,
    _resolve_and_deploy,
)

__all__ = [
    "DEPLOY_WORKER_TOOL",
    "DEPLOY_WORKER_DESCRIPTION",
    "DEPLOY_WORKER_PARAMETERS",
    "AVAILABLE_TOOLS",
    "_resolve_and_deploy",
]
