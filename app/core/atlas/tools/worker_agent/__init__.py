"""Worker agent tool - delegates focused tasks to a WorkerAgent."""

from app.core.atlas.tools.worker_agent.worker import deploy_worker_agent
from app.core.atlas.tools.worker_agent.setup import (
    DEPLOY_WORKER_TOOL,
    DEPLOY_WORKER_DESCRIPTION,
    DEPLOY_WORKER_PARAMETERS,
    AVAILABLE_TOOLS,
)

__all__ = [
    "deploy_worker_agent",
    "DEPLOY_WORKER_TOOL",
    "DEPLOY_WORKER_DESCRIPTION",
    "DEPLOY_WORKER_PARAMETERS",
    "AVAILABLE_TOOLS",
]
