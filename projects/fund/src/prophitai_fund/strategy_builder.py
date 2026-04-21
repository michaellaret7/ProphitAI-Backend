import re
import shutil
from pathlib import Path

from prophitai_fund.idea_generation.agent import IdeaGeneratorAgent
from prophitai_fund.construction.architect.agent import StrategyArchitectAgent
from prophitai_fund.construction.architect.models import StrategyManifest
from prophitai_fund.construction.build.indicators import IndicatorBuilderAgent
from prophitai_fund.construction.build.indicators.models import IndicatorBuildResult
from prophitai_fund.construction.build.signals import SignalStrategyBuilderAgent
from prophitai_fund.construction.build.signals.models import SignalStrategyBuildResult
from prophitai_fund.construction.build.execution import ExecutionLayerBuilderAgent
from prophitai_fund.validation.agent import ValidatorAgent
from prophitai_tools.sandbox.client import create_sandbox, get_sandbox, REPO_PATH
from prophitai_tools.sandbox.lifecycle import close_sandbox, setup_repo
from prophitai_tools.sandbox.scaffolding import scaffold_strategy

MODEL = "gpt-5.4"
PROVIDER = "openai"

CHECKPOINT_DIR = Path(__file__).parent / "_checkpoint"

# ================================
# --> Helper funcs
# ================================


def _save_checkpoint(stage: str, data: str) -> None:
    """Write a stage's output to a checkpoint file."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    (CHECKPOINT_DIR / f"{stage}.md").write_text(data, encoding="utf-8")


def _load_checkpoint(stage: str) -> str | None:
    """Read a stage's checkpoint file if it exists."""
    path = CHECKPOINT_DIR / f"{stage}.md"

    if path.exists():
        return path.read_text(encoding="utf-8")

    return None


def _clear_checkpoints() -> None:
    """Remove the entire checkpoint directory."""
    if CHECKPOINT_DIR.exists():
        shutil.rmtree(CHECKPOINT_DIR)


def _checkpoint_strategy_id() -> str | None:
    """Return the strategy_id this checkpoint dir is stamped with, if any."""
    path = CHECKPOINT_DIR / ".strategy_id"

    if path.exists():
        return path.read_text(encoding="utf-8").strip()

    return None


def _stamp_checkpoint(strategy_id: str) -> None:
    """Bind the checkpoint dir to a strategy_id so stale state can be detected."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    (CHECKPOINT_DIR / ".strategy_id").write_text(strategy_id, encoding="utf-8")


def _validate_manifest(manifest: StrategyManifest, expected_strategy_id: str) -> None:
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


def _extract_strategy_id(idea_text: str) -> str:
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


class StrategyBuilder:
    def __init__(self):
        self.idea_generator = IdeaGeneratorAgent()

    def run(self):
        # Stage 1: Idea Generation — runs on the host, no sandbox needed.
        # Reason: spinning up the sandbox before idea gen burns its timeout budget
        # while the idea agent does web research.
        cached_idea = _load_checkpoint("idea")

        if cached_idea:
            idea_text = cached_idea
            print(f"Loading cached idea from {cached_idea[:100]}...")
        else:
            idea = self.idea_generator.run()

            if not idea.answer:
                raise RuntimeError("Idea generation failed: agent returned no output")

            idea_text = idea.answer

            _save_checkpoint("idea", idea_text)

        strategy_id = _extract_strategy_id(idea_text)

        # Reason: checkpoints from a prior run of a *different* strategy will silently
        # pair a new idea with a stale manifest/indicator/signal result — clear and
        # restart if the stamp doesn't match this run's strategy. An unstamped dir
        # with downstream checkpoints present is pre-fix stale state; clear that too.
        stamped = _checkpoint_strategy_id()
        
        unstamped_stale = stamped is None and any(
            (CHECKPOINT_DIR / f"{stage}.md").exists() for stage in ("manifest", "indicators", "signals")
        )

        if (stamped is not None and stamped != strategy_id) or unstamped_stale:
            reason = f"stamp '{stamped}' != '{strategy_id}'" if stamped else "unstamped checkpoint from prior run"
            print(f"Clearing checkpoints: {reason}.")
            _clear_checkpoints()
            _save_checkpoint("idea", idea_text)

        _stamp_checkpoint(strategy_id)

        # Sandbox needed from here on — spin it up now that we have a strategy_id.
        sandbox_id, sandbox = create_sandbox(timeout=3600)

        try:
            # Stage 1b: Bootstrap repo and scaffold strategy directory
            setup_repo(sandbox, strategy_id)

            # Reason: a prior run can push the scaffolded folder to the remote
            # strategy branch; re-cloning and checking that branch out brings the
            # folder back into the fresh sandbox. When this run is resuming from
            # a cached idea (same strategy_id), treat the existing folder as
            # expected state and skip scaffolding. When there is no resume
            # checkpoint, an existing folder means strategy_id collided with a
            # previously-built strategy — fail loudly rather than overwrite it.
            strategy_dir = f"{REPO_PATH}/strategies/development/{strategy_id}"
            
            dir_check = get_sandbox(sandbox_id).commands.run(
                f"test -d {strategy_dir} && echo exists || echo missing"
            )
            folder_exists = "exists" in dir_check.stdout

            if folder_exists and cached_idea:
                print(f"Resuming — strategy folder present at {strategy_dir}, skipping scaffold.")
            elif folder_exists:
                raise RuntimeError(
                    f"Strategy folder '{strategy_id}' already exists on remote branch "
                    f"'strategy/{strategy_id}' without a local resume checkpoint. "
                    f"Rename the strategy or delete the remote branch before rerunning."
                )
            else:
                # Reason: scaffold_strategy is an @agent_tool that returns an error
                # STRING (not an exception) on failure. Inspect the response and raise.
                scaffold_result = scaffold_strategy(sandbox_id, strategy_id)

                if "success: false" in scaffold_result or "error:" in scaffold_result:
                    raise RuntimeError(
                        f"scaffold_strategy failed for '{strategy_id}': {scaffold_result}"
                    )

            # Stage 1c: Write the original idea to the strategy root
            idea_path = f"{REPO_PATH}/strategies/development/{strategy_id}/IDEA.md"
            get_sandbox(sandbox_id).files.write(idea_path, idea_text)

            # Stage 2: Strategy Architect
            cached_manifest = _load_checkpoint("manifest")

            if cached_manifest:
                print(f"Loading cached manifest from {cached_manifest[:100]}...")
                manifest = StrategyManifest.model_validate_json(cached_manifest)
            else:
                strategy_architect = StrategyArchitectAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
                architect_response = strategy_architect.run(idea_text, strategy_id=strategy_id)

                manifest = architect_response.parsed_output

                if not manifest:
                    raise RuntimeError(f"Strategy architect failed to produce manifest: {architect_response.answer}")

                # Reason: host owns strategy_id; the architect's value is advisory. Override
                # before validation and caching so every downstream consumer (builders,
                # validator, checkpoint) sees a single source of truth.
                manifest = manifest.model_copy(update={"strategy_id": strategy_id})

                _validate_manifest(manifest, expected_strategy_id=strategy_id)
                _save_checkpoint("manifest", manifest.model_dump_json())

            # Stage 2b: Write the manifest to the strategy root
            manifest_path = f"{REPO_PATH}/strategies/development/{strategy_id}/MANIFEST.json"
            get_sandbox(sandbox_id).files.write(manifest_path, manifest.model_dump_json(indent=2))

            # Stage 3: Indicator Builder
            cached_indicators = _load_checkpoint("indicators")

            if cached_indicators:
                indicator_result = IndicatorBuildResult.model_validate_json(cached_indicators)
            else:
                indicator_builder = IndicatorBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
                indicator_response = indicator_builder.run(manifest)

                indicator_result = indicator_response.parsed_output

                if not indicator_result:
                    raise RuntimeError(f"Indicator builder failed: {indicator_response.answer}")

                _save_checkpoint("indicators", indicator_result.model_dump_json())

            # Stage 4: Signal + Strategy Builder
            cached_signals = _load_checkpoint("signals")

            if cached_signals:
                signal_result = SignalStrategyBuildResult.model_validate_json(cached_signals)
            else:
                signal_strategy_builder = SignalStrategyBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
                signal_response = signal_strategy_builder.run(manifest, indicator_result)

                signal_result = signal_response.parsed_output

                if not signal_result:
                    raise RuntimeError(f"Signal+Strategy builder failed: {signal_response.answer}")

                _save_checkpoint("signals", signal_result.model_dump_json())

            # Stage 5: Execution Layer Builder
            execution_layer_builder = ExecutionLayerBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            execution_response = execution_layer_builder.run(manifest, indicator_result, signal_result)

            if not execution_response.parsed_output:
                raise RuntimeError(f"Execution layer builder failed: {execution_response.answer}")

            # Stage 6: Validator
            validator = ValidatorAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            validation_response = validator.run(strategy_id=strategy_id)

            verdict = validation_response.parsed_output

            if not verdict:
                raise RuntimeError(f"Validator failed to produce verdict: {validation_response.answer}")

            # Pipeline complete — clean up checkpoints
            _clear_checkpoints()

            return verdict

        finally:
            close_sandbox(sandbox_id)


if __name__ == "__main__":
    strategy_builder = StrategyBuilder()
    strategy_builder.run()