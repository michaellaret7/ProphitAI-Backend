import re
import shutil
from pathlib import Path

from prophitai_fund.idea_generation.agent import IdeaGeneratorAgent
from prophitai_fund.research.architect.agent import StrategyArchitectAgent
from prophitai_fund.research.architect.models import StrategyManifest
from prophitai_fund.research.builders.indicators import IndicatorBuilderAgent
from prophitai_fund.research.builders.indicators.models import IndicatorBuildResult
from prophitai_fund.research.builders.signals import SignalStrategyBuilderAgent
from prophitai_fund.research.builders.signals.models import SignalStrategyBuildResult
from prophitai_fund.research.builders.execution import ExecutionLayerBuilderAgent
from prophitai_tools.sandbox.client import create_sandbox, get_sandbox, REPO_PATH
from prophitai_tools.sandbox.lifecycle import close_sandbox, setup_repo
from prophitai_tools.sandbox.scaffolding import scaffold_strategy

MODEL = "claude-sonnet-4-6"
PROVIDER = "anthropic"

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


def _validate_manifest(manifest: StrategyManifest) -> None:
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

    if errors:
        raise RuntimeError(f"Manifest validation failed: {', '.join(errors)}")


def _extract_strategy_id(idea_text: str) -> str:
    """Parse '## Strategy Name' from the idea output and slugify it to a strategy_id."""
    match = re.search(r"##\s*Strategy\s+Name\s*\n+(.+)", idea_text)

    if not match:
        raise RuntimeError("Idea output missing '## Strategy Name' section")

    name = match.group(1).strip()

    # Reason: take the main name before any colon or parenthetical subtitle
    name = re.split(r"[:\(]", name)[0].strip()

    # Reason: strip non-alphanumeric chars, collapse whitespace, lowercase → snake_case
    strategy_id = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    strategy_id = re.sub(r"\s+", "_", strategy_id).lower()

    return strategy_id


class StrategyBuilder:
    def __init__(self):
        self.idea_generator = IdeaGeneratorAgent(model=MODEL, provider=PROVIDER)

    def run(self):
        sandbox_id, sandbox = create_sandbox(timeout=3600)

        try:
            # Stage 1: Idea Generation
            cached_idea = _load_checkpoint("idea")

            if cached_idea:
                idea_text = cached_idea
                print(f"Loading cached idea from {cached_idea}")
            else:
                idea = self.idea_generator.run()

                if not idea.answer:
                    raise RuntimeError("Idea generation failed: agent returned no output")

                idea_text = idea.answer
                _save_checkpoint("idea", idea_text)

            # Stage 1b: Bootstrap repo and scaffold strategy directory
            strategy_id = _extract_strategy_id(idea_text)
            
            setup_repo(sandbox, strategy_id)
            scaffold_strategy(sandbox_id, strategy_id)

            # Stage 1c: Write the original idea to the strategy root
            idea_path = f"{REPO_PATH}/strategies/development/{strategy_id}/IDEA.md"
            get_sandbox(sandbox_id).files.write(idea_path, idea_text)

            # Stage 2: Strategy Architect
            cached_manifest = _load_checkpoint("manifest")

            if cached_manifest:
                print(f"Loading cached manifest from {cached_manifest}")
                manifest = StrategyManifest.model_validate_json(cached_manifest)
            else:
                strategy_architect = StrategyArchitectAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
                architect_response = strategy_architect.run(idea_text)

                manifest = architect_response.parsed_output

                if not manifest:
                    raise RuntimeError(f"Strategy architect failed to produce manifest: {architect_response.answer}")

                _validate_manifest(manifest)
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

            execution_result = execution_response.parsed_output

            if not execution_result:
                raise RuntimeError(f"Execution layer builder failed: {execution_response.answer}")

            # Pipeline complete — clean up checkpoints
            _clear_checkpoints()

            return execution_result

        finally:
            close_sandbox(sandbox_id)


if __name__ == "__main__":
    strategy_builder = StrategyBuilder()
    strategy_builder.run()