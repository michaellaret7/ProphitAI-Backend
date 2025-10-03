"""Path utility functions for agent output management."""

from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Get the ProphitAI project root directory.

    Returns the absolute path to the project root by navigating up from
    the base_agent directory structure.

    Directory structure:
        base_agent/ -> agentic_framework/ -> core/ -> app/ -> ProphitAI/

    Returns:
        Path: Absolute path to ProphitAI project root
    """
    # Get path to this utils module
    # From path_utils.py: utils/ -> base_agent/ -> agentic_framework/ -> core/ -> app/ -> ProphitAI/
    utils_dir = Path(__file__).resolve().parent
    base_agent_dir = utils_dir.parent
    agentic_framework_dir = base_agent_dir.parent
    core_dir = agentic_framework_dir.parent
    app_dir = core_dir.parent
    project_root = app_dir.parent

    return project_root


def create_agent_output_dir(agent_name: str) -> Path:
    """Create and return agent-specific timestamped output directory.

    Creates directory structure: agent_output/{YYYY-MM-DD}/{AgentName}_{HHMMSS}/

    Args:
        agent_name: Name of the agent (e.g., 'CIOAgent', 'BaseAgent')

    Returns:
        Path: Absolute path to the created agent output directory

    Example:
        >>> output_dir = create_agent_output_dir("CIOAgent")
        >>> # Returns: .../ProphitAI/agent_output/2025-10-03/CIOAgent_143052/
    """
    project_root = get_project_root()

    current_datetime = datetime.now()
    date_folder = current_datetime.strftime("%Y-%m-%d")
    time_str = current_datetime.strftime("%H%M%S")  # Short time format (HHMMSS)
    agent_folder = f"{agent_name}_{time_str}"

    output_dir = project_root / "agent_output" / date_folder / agent_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir