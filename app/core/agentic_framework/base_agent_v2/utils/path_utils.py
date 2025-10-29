"""Path utilities for BaseAgent v2.

Creates per-run output directories consistent with base agent behavior but
using UTC time per CLAUDE.md guidelines.
"""

from pathlib import Path
from app.utils.time_utils import get_current_utc_time
from app.core.agentic_framework.base_agent.utils.path_utils import get_project_root


def create_agent_output_dir(agent_name: str) -> Path:
    """Create and return a UTC-timestamped agent output directory.

    Structure: agent_output/{YYYY-MM-DD}/{AgentName}_{HHMMSS}/

    Args:
        agent_name: Logical name of the agent (class name is fine)

    Returns:
        Path: Created output directory path
    """
    project_root = get_project_root()

    now = get_current_utc_time()
    date_folder = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    agent_folder = f"{agent_name}_{time_str}"

    output_dir = project_root / "agent_output" / date_folder / agent_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

