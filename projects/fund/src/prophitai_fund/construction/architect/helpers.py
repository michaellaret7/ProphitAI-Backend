"""Helpers for reading and parsing the Strategy Manifest from the sandbox."""

from prophitai_atlas.utils.gpt_parser import parse_with_gpt
from prophitai_tools.sandbox.client import get_sandbox, REPO_PATH

from prophitai_fund.construction.architect.models import StrategyManifest


# ================================
# --> Helper funcs
# ================================


def find_manifest_path(sandbox_id: str) -> str | None:
    """Locate MANIFEST.json in the sandbox development directory.

    Args:
        sandbox_id: Active sandbox ID.

    Returns:
        Absolute path to MANIFEST.json, or None if not found.
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return None

    dev_dir = f"{REPO_PATH}/strategies/development"

    try:
        result = sandbox.commands.run(f"find {dev_dir} -maxdepth 2 -name MANIFEST.json", timeout=10)
        paths = result.stdout.strip().splitlines()

        if paths:
            return paths[0]

    except Exception:
        pass

    return None


def read_manifest_from_sandbox(sandbox_id: str) -> StrategyManifest | None:
    """Read and parse MANIFEST.json from the sandbox.

    Tries direct Pydantic validation first. If the agent used slightly
    wrong field names, falls back to parse_with_gpt which can fix
    schema mismatches from well-structured JSON.

    Args:
        sandbox_id: Active sandbox ID.

    Returns:
        Parsed StrategyManifest, or None if not found or invalid.
    """
    manifest_path = find_manifest_path(sandbox_id)

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
