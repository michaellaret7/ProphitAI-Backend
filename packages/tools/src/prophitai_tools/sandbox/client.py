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
    "FMP_API_KEY",
    "DB_HOST",
    "DB_PORT",
]

# Reason: Database names needed to build read-only connection strings for the sandbox
DATABASE_NAMES = ["market_data", "user_data", "prophit_alts", "macro_data"]
DATABASE_ENV_MAP = {
    "market_data": "MARKET_DATA",
    "user_data": "USER_DATA",
    "prophit_alts": "PROPHIT_ALTS",
    "macro_data": "MACRO_DATA",
}

sessions: dict[str, Sandbox] = {}

def build_sandbox_envs() -> dict[str, str]:
    """Collect host env vars to inject into the sandbox.

    Forwards non-DB keys directly, then overrides DB credentials
    with the read-only user so the sandbox cannot write to any database.
    """
    envs: dict[str, str] = {}

    for key in SANDBOX_ENV_KEYS:
        value = os.environ.get(key)

        if value:
            envs[key] = value

    # Reason: Sandbox must use the read-only DB user to prevent writes/deletes
    readonly_user = os.environ.get("DB_READONLY_USER", "")
    readonly_password = os.environ.get("DB_READONLY_PASSWORD", "")
    db_host = os.environ.get("DB_HOST", "")
    db_port = os.environ.get("DB_PORT", "5432")

    envs["DB_USER"] = readonly_user
    envs["DB_PASSWORD"] = readonly_password

    for db_name, env_key in DATABASE_ENV_MAP.items():
        envs[env_key] = (
            f"postgresql://{readonly_user}:{readonly_password}"
            f"@{db_host}:{db_port}/{db_name}"
        )

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
