"""Internal session store and E2B client helpers for sandbox tools.

Manages live sandbox instances in memory and provides helpers for
creating, retrieving, and removing sandbox sessions.
"""

import os

from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

# Reason: .env contains SANDBOX_* vars that aren't always in the shell environment
load_dotenv()

# ================================
# --> Helper funcs
# ================================

TEMPLATE_NAME = "prophitai-strategies"
SANDBOX_ENV_PREFIX = "SANDBOX_"
STRATEGIES_REPO = "https://github.com/Prophit-AI/Strategies.git"
REPO_PATH = "/home/user/strategies"

sessions: dict[str, Sandbox] = {}


def build_sandbox_envs() -> dict[str, str]:
    """Read SANDBOX_* env vars from host and strip the prefix for injection.

    For example, SANDBOX_DATABASE_URL=x becomes DATABASE_URL=x inside the sandbox.
    """
    envs: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith(SANDBOX_ENV_PREFIX) and key != "SANDBOX_":
            sandbox_key = key[len(SANDBOX_ENV_PREFIX):]
            envs[sandbox_key] = value
    return envs


def create_sandbox(timeout: int = 3600) -> tuple[str, Sandbox]:
    """Create a new E2B sandbox and store it in the session registry.

    Args:
        timeout: Sandbox lifetime in seconds.

    Returns:
        Tuple of (sandbox_id, sandbox_instance).
    """
    envs = build_sandbox_envs()
    sandbox = Sandbox.create(
        template=TEMPLATE_NAME,
        timeout=timeout,
        envs=envs,
    )
    sandbox_id = sandbox.sandbox_id
    sessions[sandbox_id] = sandbox
    return sandbox_id, sandbox


def get_sandbox(sandbox_id: str) -> Sandbox | None:
    """Look up a live sandbox by ID."""
    return sessions.get(sandbox_id)


def remove_sandbox(sandbox_id: str) -> None:
    """Remove a sandbox from the session registry."""
    sessions.pop(sandbox_id, None)
