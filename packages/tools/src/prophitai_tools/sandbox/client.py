"""Internal session store and E2B client helpers for sandbox tools.

Manages live sandbox instances in memory and provides helpers for
creating, retrieving, and removing sandbox sessions.
"""

import os

from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

load_dotenv()

# ================================
# --> Helper funcs
# ================================

TEMPLATE_NAME = "prophitai-strategies"
STRATEGIES_REPO = "https://github.com/Prophit-AI/Strategies.git"
REPO_PATH = "/home/user/strategies"

SANDBOX_ENV_KEYS = [
    "GITHUB_TOKEN",
    "MARKET_DATA",
    "FMP_API_KEY",
]

sessions: dict[str, Sandbox] = {}


def build_sandbox_envs() -> dict[str, str]:
    """Collect host env vars to inject into the sandbox.

    Only forwards the keys listed in SANDBOX_ENV_KEYS.
    """
    envs: dict[str, str] = {}

    for key in SANDBOX_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            envs[key] = value

    return envs


print(build_sandbox_envs())
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
