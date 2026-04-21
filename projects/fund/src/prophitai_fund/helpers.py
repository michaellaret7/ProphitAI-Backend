import re
import shutil
from pathlib import Path

from e2b_code_interpreter import Sandbox

from prophitai_fund.construction.architect.models import StrategyManifest
from prophitai_tools.sandbox.client import REPO_PATH, create_sandbox, get_sandbox
from prophitai_tools.sandbox.lifecycle import setup_repo

CHECKPOINT_DIR = Path(__file__).parent / "_checkpoint"


def bootstrap_sandbox(strategy_id: str, timeout: int = 3600) -> tuple[str, Sandbox]:
    """Create a fresh sandbox and clone+checkout the strategy branch.

    Wraps create_sandbox + setup_repo so each pipeline stage gets a
    clean VM with the latest pushed state on strategy/{strategy_id}.
    """
    sandbox_id, sandbox = create_sandbox(timeout=timeout)

    setup_repo(sandbox, strategy_id)

    return sandbox_id, sandbox


def commit_and_push(sandbox_id: str, strategy_id: str, message: str) -> None:
    """Commit pending changes in the strategy repo and push to origin.

    Fails loudly on push failure — if state isn't pushed, the next
    stage's fresh clone will be missing this stage's work.
    """
    sandbox = get_sandbox(sandbox_id)

    if sandbox is None:
        raise RuntimeError(f"commit_and_push: no live sandbox '{sandbox_id}'")

    branch = f"strategy/{strategy_id}"
    safe_message = message.replace("'", "'\\''")

    # Reason: use an explicit if/else so push failures surface via exit_code;
    # chained && || expressions mask the final failing command's exit code.
    script = (
        f"set -e\n"
        f"cd {REPO_PATH}\n"
        f"git add -A\n"
        f"if git diff --cached --quiet; then\n"
        f"  echo 'NOTHING_TO_COMMIT'\n"
        f"  exit 0\n"
        f"fi\n"
        f"git commit -m '{safe_message}'\n"
        f"git push origin {branch}\n"
    )

    result = sandbox.commands.run(script)

    if result.exit_code != 0:
        raise RuntimeError(
            f"commit_and_push failed for '{strategy_id}' "
            f"(stage: {message}): {result.stderr or result.stdout}"
        )


def save_checkpoint(stage: str, data: str) -> None:
    """Write a stage's output to a checkpoint file."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    (CHECKPOINT_DIR / f"{stage}.md").write_text(data, encoding="utf-8")


def load_checkpoint(stage: str) -> str | None:
    """Read a stage's checkpoint file if it exists."""
    path = CHECKPOINT_DIR / f"{stage}.md"

    if path.exists():
        return path.read_text(encoding="utf-8")

    return None


def clear_checkpoints() -> None:
    """Remove the entire checkpoint directory."""
    if CHECKPOINT_DIR.exists():
        shutil.rmtree(CHECKPOINT_DIR)


def checkpoint_strategy_id() -> str | None:
    """Return the strategy_id this checkpoint dir is stamped with, if any."""
    path = CHECKPOINT_DIR / ".strategy_id"

    if path.exists():
        return path.read_text(encoding="utf-8").strip()

    return None


def stamp_checkpoint(strategy_id: str) -> None:
    """Bind the checkpoint dir to a strategy_id so stale state can be detected."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    (CHECKPOINT_DIR / ".strategy_id").write_text(strategy_id, encoding="utf-8")


def validate_manifest(manifest: StrategyManifest, expected_strategy_id: str) -> None:
    """Verify the manifest has real content, not empty defaults from a failed parse."""
    errors = []

    if not manifest.strategy_id:
        errors.append("strategy_id is empty")

    if not manifest.strategy_name:
        errors.append("strategy_name is empty")

    if not manifest.indicators:
        errors.append("indicators list is empty")

    if not manifest.signals.class_name:
        errors.append("signals.class_name is empty")

    # Reason: defense in depth — Change 1 overwrites manifest.strategy_id with the
    # host value, so this assertion only fires if that override is removed later.
    if manifest.strategy_id != expected_strategy_id:
        errors.append(
            f"manifest.strategy_id '{manifest.strategy_id}' does not match "
            f"host strategy_id '{expected_strategy_id}'"
        )

    # Reason: indicator file paths are embedded in the manifest and consumed
    # verbatim by the builder agents. If the architect produced content for a
    # different strategy (e.g. via stale sandbox state), the paths will point
    # at the wrong development directory. strategy_id override does NOT rewrite
    # these paths, so the builders silently write to the wrong strategy's dir.
    expected_dir = f"strategies/development/{expected_strategy_id}/"

    for indicator in manifest.indicators:
        if indicator.file and "strategies/development/" in indicator.file:
            if expected_dir not in indicator.file:
                errors.append(
                    f"indicator '{indicator.class_name}' file path "
                    f"'{indicator.file}' does not reference expected "
                    f"strategy directory '{expected_dir}'"
                )

    if errors:
        raise RuntimeError(f"Manifest validation failed: {', '.join(errors)}")


def extract_strategy_id(idea_text: str) -> str:
    """Parse the strategy name from the idea output and slugify it to a strategy_id.

    Accepts '## Strategy Name\\n<name>' (spec) or a leading '# <name>' H1 title
    (common LLM rendering where the strategy name becomes the document title).
    """
    match = re.search(r"##\s*Strategy\s+Name\s*\n+(.+)", idea_text)

    if not match:
        # Reason: fall back to first H1 heading when the agent renders the
        # name as a document title instead of under '## Strategy Name'.
        match = re.search(r"^#\s+(.+)$", idea_text, re.MULTILINE)

    if not match:
        raise RuntimeError("Idea output missing strategy name heading")

    name = match.group(1).strip()

    # Reason: take the main name before any colon or parenthetical subtitle
    name = re.split(r"[:\(]", name)[0].strip()

    # Reason: strip non-alphanumeric chars, collapse whitespace, lowercase → snake_case
    strategy_id = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    strategy_id = re.sub(r"\s+", "_", strategy_id).strip("_").lower()

    # Reason: empty strategy_id creates path like 'strategies/development//MANIFEST.json'
    # and every downstream helper silently operates on the development/ dir itself,
    # re-opening the same leakage class the manifest fix just closed. Fail loudly.
    if not strategy_id:
        raise RuntimeError(
            f"Extracted strategy_id is empty from heading: '{name}'. "
            f"Idea generator must emit a strategy name with at least one alphanumeric character."
        )

    return strategy_id
