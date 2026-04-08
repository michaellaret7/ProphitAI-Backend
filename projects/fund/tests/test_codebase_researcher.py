"""Test the codebase_researcher scoped worker through deploy_scoped_worker.

Spins up a real E2B sandbox, bootstraps the repo, then deploys
a codebase_researcher worker via the scoped deploy function.
The worker explores the sandbox codebase and returns structured findings.
"""

from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.models.callbacks import NoOpChatCallback

from prophitai_tools.sandbox.client import create_sandbox, remove_sandbox
from prophitai_tools.sandbox.lifecycle import bootstrap_repo

from prophitai_atlas.tools.base.worker_agent.deploy_scoped import deploy_scoped_worker
from prophitai_fund.researcher.workers import RESEARCHER_WORKERS


# ================================
# --> Helper funcs
# ================================


def _print_result(title: str, result: str) -> None:
    """Pretty-print the deploy_scoped_worker YAML response."""

    print("\n" + "=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)
    print(result)


# ================================
# --> Tests
# ================================


def test_codebase_researcher() -> None:
    """Deploy a codebase_researcher worker to explore the strategies repo."""

    sandbox_id = None

    try:
        # --- Step 1: Spin up sandbox VM ---
        print("Creating sandbox...")
        sandbox_id, sandbox = create_sandbox(timeout=600)
        print(f"Sandbox created: {sandbox_id}")

        # --- Step 2: Bootstrap the repo inside the sandbox ---
        print("Bootstrapping repo...")
        repo_info = bootstrap_repo(sandbox, "test_researcher")
        print(f"Repo bootstrapped: {repo_info}")

        # --- Step 3: Deploy the codebase_researcher worker ---
        notebook = Notebook()
        callback = NoOpChatCallback()

        result = deploy_scoped_worker(
            notebook=notebook,
            chat_callback=callback,
            user_id=None,
            registry=RESEARCHER_WORKERS,
            worker_type="codebase_researcher",
            task=(
                "ROLE: You are a codebase researcher exploring a strategies repository.\n\n"
                "TASK: Explore the strategies repo and report its structure.\n"
                f"The sandbox_id is: {sandbox_id}\n"
                f"The repo is cloned at: {repo_info['repo_path']}\n\n"
                "Specifically:\n"
                "1. Glob the top-level directory structure of the repo\n"
                "2. Find the strategy template directory and list its files\n"
                "3. Read the base strategy class to understand the interface\n"
                "4. Search for any existing strategy implementations\n\n"
                "SUCCESS CRITERIA:\n"
                "- Mapped the full directory structure\n"
                "- Found and read the base strategy class signature\n"
                "- Identified the template strategy pattern\n\n"
                "RULES:\n"
                "- Read-only. Do not suggest changes.\n"
                "- Be precise with file paths and line numbers.\n"
                f"- Use sandbox_id '{sandbox_id}' for every tool call.\n\n"
                "OUTPUT FORMAT:\n"
                "Return structured findings with: File Structure, Key Components, "
                "Patterns & Conventions, Dependencies & Contracts."
            ),
            plan_task_id="test-1",
            context="",
        )

        _print_result("Codebase Researcher Worker", result)

    finally:
        # --- Step 4: Clean up ---
        if sandbox_id:
            print(f"\nCleaning up sandbox {sandbox_id}...")

            sandbox = None

            try:
                from prophitai_tools.sandbox.client import get_sandbox
                sandbox = get_sandbox(sandbox_id)
            except Exception:
                pass

            if sandbox:
                sandbox.kill()

            remove_sandbox(sandbox_id)
            print("Sandbox closed.")


if __name__ == "__main__":
    test_codebase_researcher()
