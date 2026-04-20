"""Helpers for reading and parsing the Strategy Manifest from the sandbox."""

from prophitai_atlas.utils.gpt_parser import parse_with_gpt
from prophitai_tools.sandbox.client import get_sandbox, REPO_PATH

from prophitai_fund.construction.architect.models import StrategyManifest


# ================================
# --> Helper funcs
# ================================


def find_manifest_path(sandbox_id: str, strategy_id: str) -> str | None:
    """Locate MANIFEST.json for a specific strategy in the sandbox.

    Reason: `find` across the whole development dir returns ALL MANIFEST.json
    files in the cloned repo (including prior successfully-built strategies)
    and `paths[0]` picks whichever filesystem order gave it — causing stale
    manifests from unrelated strategies to leak downstream. Always read the
    manifest at the deterministic path for the current strategy_id.

    Args:
        sandbox_id: Active sandbox ID.
        strategy_id: Current strategy_id owned by the orchestrator.

    Returns:
        Absolute path to MANIFEST.json for this strategy, or None if the
        sandbox is gone or the file does not exist.
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return None

    manifest_path = f"{REPO_PATH}/strategies/development/{strategy_id}/MANIFEST.json"

    try:
        result = sandbox.commands.run(f"test -f {manifest_path}", timeout=10)

        if result.exit_code == 0:
            return manifest_path

    except Exception:
        pass

    return None


def read_manifest_from_sandbox(sandbox_id: str, strategy_id: str) -> StrategyManifest | None:
    """Read and parse MANIFEST.json for a specific strategy from the sandbox.

    Tries direct Pydantic validation first. If the agent used slightly
    wrong field names, falls back to parse_with_gpt which can fix
    schema mismatches from well-structured JSON.

    Args:
        sandbox_id: Active sandbox ID.
        strategy_id: Current strategy_id — manifest is read from
            ``strategies/development/{strategy_id}/MANIFEST.json``.

    Returns:
        Parsed StrategyManifest, or None if not found or invalid.
    """
    manifest_path = find_manifest_path(sandbox_id, strategy_id)

    if not manifest_path:
        return None

    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return None

    content = sandbox.files.read(manifest_path)

    # Reason: try direct validation first — fastest and cheapest path
    try:
        return StrategyManifest.model_validate_json(content)
    except Exception:
        pass

    # Reason: the agent wrote valid JSON but with slightly wrong field names
    # (e.g. "name" instead of "class_name"). parse_with_gpt can fix schema
    # mismatches from well-structured JSON without regenerating content.
    try:
        print("[Architect] Direct parse failed, using LLM to fix schema mismatches...")
        return parse_with_gpt(query=content, target_model=StrategyManifest)

    except Exception as e:
        print(f"[Architect] Failed to parse MANIFEST.json: {e}")
        return None
