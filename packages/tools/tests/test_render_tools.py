"""Smoke test — runs an Agent with Render tools against the real Render API.

Scoped to the fund environment:
  - RENDER_FUND_PROJECT_ID
  - RENDER_FUND_ENVIRONMENT_ID
  - RENDER_OWNER_ID
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_tools.render.deploys import (
    list_deploys, get_deploy, trigger_deploy, cancel_deploy, rollback_deploy,
)
from prophitai_tools.render.services import (
    create_render_service, list_render_services, get_render_service,
    list_instances, restart_service, suspend_service, resume_service,
)
from prophitai_tools.render.env_vars import list_env_vars, set_env_var, delete_env_var
from prophitai_tools.render.logs import get_render_logs, get_render_log_labels


RENDER_TOOLS = [
    # deploys
    list_deploys, get_deploy, trigger_deploy, cancel_deploy, rollback_deploy,
    # services
    create_render_service, list_render_services, get_render_service,
    list_instances, restart_service, suspend_service, resume_service,
    # env vars
    list_env_vars, set_env_var, delete_env_var,
    # logs
    get_render_logs, get_render_log_labels,
]


# ================================
# --> Helper funcs
# ================================


def _print_result(title: str, result) -> None:
    """Pretty-print an AgentResponse."""
    print("\n" + "=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)
    print(f"Answer:\n{result.answer}")
    print(f"\nIterations: {result.iterations}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Tool calls: {result.tool_calls_made}")
    print(f"Stop reason: {result.stop_reason}")


def _make_agent() -> Agent:
    """Create an Agent loaded with all Render tools."""
    return Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.PRODUCTION,
        tools=RENDER_TOOLS,
    )


# ================================
# --> Tests
# ================================


def test_list_fund_services():
    """List all services in the fund environment."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then:\n"
            "1. List all Render services in the fund environment.\n"
            "2. For each service report: name, ID, type, suspended status, and dashboard URL.\n"
            "3. If no services exist, say so."
        ),
        max_iterations=10,
    )
    _print_result("List fund services", result)


def test_create_service():
    """Create a new web service in the fund environment."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then:\n"
            "1. Create a new Docker-backed web_service named 'fund-test-api'.\n"
            "   - repo: https://github.com/render-examples/express-hello-world\n"
            "   - branch: main\n"
            "   - plan: starter\n"
            "   - region: oregon\n"
            "   - health_check_path: /\n"
            "   - num_instances: 1\n"
            "2. After creation, report the service ID and status.\n"
            "3. Then list deploys for it to confirm the initial deploy was triggered."
        ),
        max_iterations=15,
    )
    _print_result("Create service", result)


def test_deploy_status():
    """Check latest deploy status for all fund services."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then:\n"
            "1. List all Render services.\n"
            "2. For each service, get the most recent deploy (limit=1).\n"
            "3. Report the status of the latest deploy for each service — "
            "is it live, failed, or in progress?\n"
            "4. If any deploy failed, get the logs for that service to diagnose."
        ),
        max_iterations=25,
    )
    _print_result("Deploy status check", result)


def test_env_vars():
    """List env var keys for a fund service."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then:\n"
            "1. List all Render services.\n"
            "2. Pick the first service and list its environment variables.\n"
            "3. Tell me how many env vars are configured and list their keys "
            "(DO NOT show the values for security)."
        ),
        max_iterations=15,
    )
    _print_result("Env vars listing", result)


def test_logs():
    """Fetch recent logs for a fund service."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then:\n"
            "1. List all Render services.\n"
            "2. Pick the first service and fetch its last 30 log entries.\n"
            "3. Summarize what you see — any errors? Is the service healthy?"
        ),
        max_iterations=15,
    )
    _print_result("Logs check", result)


def test_full_lifecycle():
    """End-to-end: create a service, wait for deploy, check logs, then suspend it."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then do the full lifecycle:\n"
            "1. Create a Docker-backed web_service named 'fund-lifecycle-test'.\n"
            "   - repo: https://github.com/render-examples/express-hello-world\n"
            "   - branch: main\n"
            "   - plan: starter\n"
            "   - region: oregon\n"
            "   - health_check_path: /\n"
            "2. After creation, list its deploys to confirm the first deploy started.\n"
            "3. Get the deploy details and report its status.\n"
            "4. Fetch the last 20 logs for the service.\n"
            "5. List its instances.\n"
            "6. Finally, suspend the service so we don't get billed.\n"
            "7. Summarize the full lifecycle."
        ),
        max_iterations=30,
    )
    _print_result("Full lifecycle", result)


def test_diagnose_failed_deploy():
    """Find the failed deploy on fund-test-api and pull its logs."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "Use register_tools to load the render category. Then:\n"
            "1. List all Render services in the fund environment.\n"
            "2. Find the service named 'fund-test-api'.\n"
            "3. List its deploys and find the failed one.\n"
            "4. Get the deploy details for the failed deploy.\n"
            "5. Pull the logs for that service — get at least 100 entries.\n"
            "6. Analyze the logs and tell me exactly why the deploy failed.\n"
            "7. Recommend what needs to change to fix it."
        ),
        max_iterations=20,
    )
    _print_result("Diagnose failed deploy", result)


if __name__ == "__main__":
    print("Running Render tools smoke tests...\n")
    print("All tests scoped to fund environment.\n")

    test_diagnose_failed_deploy()
