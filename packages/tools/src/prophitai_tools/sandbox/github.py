"""GitHub tools for creating pull requests from strategy branches."""

import os

import requests

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response

GITHUB_API = "https://api.github.com"
STRATEGIES_REPO = "Prophit-AI/Strategies"


# ================================
# --> Helper funcs
# ================================


def get_github_token() -> str | None:
    """Get the sandbox GitHub token from environment."""
    return os.getenv("SANDBOX_GITHUB_TOKEN")


def github_request(method: str, endpoint: str, token: str, json: dict | None = None) -> requests.Response:
    """Make an authenticated request to the GitHub API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{GITHUB_API}{endpoint}"
    return requests.request(method, url, headers=headers, json=json, timeout=30)


# ================================
# --> Tools
# ================================


@agent_tool(name="create_pull_request", category="sandbox")
def create_pull_request(
    branch: str,
    title: str,
    body: str,
    base: str = "main",
) -> str:
    """Create a pull request on the Strategies repo.

    Use this after pushing a strategy branch to open a PR for human review.

    Args:
        branch: The source branch name (e.g. strategy/rsi_mean_reversion).
        title: PR title.
        body: PR description with strategy details and backtest results.
        base: Target branch to merge into. Defaults to main.
    """
    token = get_github_token()
    
    if not token:
        return error_response("SANDBOX_GITHUB_TOKEN not set in environment.")
    try:
        response = github_request(
            "POST",
            f"/repos/{STRATEGIES_REPO}/pulls",
            token=token,
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": base,
            },
        )
        if response.status_code == 201:
            pr = response.json()
            return success_response({
                "pr_number": pr["number"],
                "pr_url": pr["html_url"],
                "state": pr["state"],
                "title": pr["title"],
            })
        return error_response(f"GitHub API error ({response.status_code}): {response.json().get('message', response.text)}")
    except Exception as e:
        return error_response(f"Failed to create pull request: {e}")
