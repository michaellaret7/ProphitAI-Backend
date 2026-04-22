from prophitai_fund.helpers import (
    CHECKPOINT_DIR,
    bootstrap_sandbox,
    checkpoint_strategy_id,
    clear_checkpoints,
    commit_and_push,
    extract_strategy_id,
    load_checkpoint,
    save_checkpoint,
    stamp_checkpoint,
    validate_manifest,
)
from prophitai_fund.idea_generation.agent import IdeaGeneratorAgent
from prophitai_fund.construction.architect.agent import StrategyArchitectAgent
from prophitai_fund.construction.architect.models import StrategyManifest
from prophitai_fund.construction.build.indicators import IndicatorBuilderAgent
from prophitai_fund.construction.build.indicators.models import IndicatorBuildResult
from prophitai_fund.construction.build.signals import SignalStrategyBuilderAgent
from prophitai_fund.construction.build.signals.models import SignalStrategyBuildResult
from prophitai_fund.construction.build.execution import ExecutionLayerBuilderAgent
from prophitai_fund.validation.agent import ValidatorAgent
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox
from prophitai_tools.sandbox.lifecycle import close_sandbox
from prophitai_tools.sandbox.scaffolding import scaffold_strategy

MODEL = "claude-sonnet-4-6"
PROVIDER = "anthropic"


class StrategyBuilder:
    def __init__(self):
        self.idea_generator = IdeaGeneratorAgent()

    def run(self):
        # Stage 1: Idea Generation — runs on the host, no sandbox needed.
        # Reason: spinning up the sandbox before idea gen burns its timeout budget
        # while the idea agent does web research.
        cached_idea = load_checkpoint("idea")

        if cached_idea:
            idea_text = cached_idea
            print(f"Loading cached idea from {cached_idea[:100]}...")
        else:
            idea = self.idea_generator.run()

            if not idea.answer:
                raise RuntimeError("Idea generation failed: agent returned no output")

            idea_text = idea.answer

            save_checkpoint("idea", idea_text)

        strategy_id = extract_strategy_id(idea_text)

        # Reason: checkpoints from a prior run of a *different* strategy will silently
        # pair a new idea with a stale manifest/indicator/signal result — clear and
        # restart if the stamp doesn't match this run's strategy. An unstamped dir
        # with downstream checkpoints present is pre-fix stale state; clear that too.
        stamped = checkpoint_strategy_id()

        unstamped_stale = stamped is None and any(
            (CHECKPOINT_DIR / f"{stage}.md").exists() for stage in ("manifest", "indicators", "signals")
        )

        if (stamped is not None and stamped != strategy_id) or unstamped_stale:
            reason = f"stamp '{stamped}' != '{strategy_id}'" if stamped else "unstamped checkpoint from prior run"
            print(f"Clearing checkpoints: {reason}.")
            clear_checkpoints()
            save_checkpoint("idea", idea_text)

        stamp_checkpoint(strategy_id)

        # Stage 2: Strategy Architect — fresh sandbox, scaffold + IDEA.md + MANIFEST.json, push.
        cached_manifest = load_checkpoint("manifest")

        if cached_manifest:
            print(f"Loading cached manifest from {cached_manifest[:100]}...")
            manifest = StrategyManifest.model_validate_json(cached_manifest)
        else:
            manifest = self._run_architect_stage(strategy_id, idea_text)

        # Stage 3: Indicator Builder — fresh sandbox, writes indicator code, push.
        cached_indicators = load_checkpoint("indicators")

        if cached_indicators:
            indicator_result = IndicatorBuildResult.model_validate_json(cached_indicators)
        else:
            indicator_result = self._run_indicator_stage(strategy_id, manifest)

        # Stage 4: Signal + Strategy Builder — fresh sandbox, writes signal code, push.
        cached_signals = load_checkpoint("signals")

        if cached_signals:
            signal_result = SignalStrategyBuildResult.model_validate_json(cached_signals)
        else:
            signal_result = self._run_signal_stage(strategy_id, manifest, indicator_result)

        # Stage 5: Execution Layer Builder — fresh sandbox, writes execution code, push.
        self._run_execution_stage(strategy_id, manifest, indicator_result, signal_result)

        # Stage 6: Validator — fresh sandbox, read-only backtests, no push.
        verdict = self._run_validator_stage(strategy_id)

        # Pipeline complete — clean up checkpoints
        clear_checkpoints()

        return verdict

    # ================================
    # --> Stage runners
    # ================================

    def _run_architect_stage(self, strategy_id: str, idea_text: str) -> StrategyManifest:
        sandbox_id, _ = bootstrap_sandbox(strategy_id)
        print(f"[stage 2: architect] sandbox {sandbox_id} started")

        try:
            # Reason: a prior aborted run can push the scaffolded folder to the remote
            # strategy branch; setup_repo's clone brings it back. When the checkpoint
            # is stamped with this strategy_id, treat the existing folder as resume
            # state and skip scaffolding. Without a matching stamp, an existing folder
            # means strategy_id collided with a previously-built strategy — fail loudly.
            strategy_dir = f"{REPO_PATH}/strategies/development/{strategy_id}"

            dir_check = get_sandbox(sandbox_id).commands.run(
                f"test -d {strategy_dir} && echo exists || echo missing"
            )
            folder_exists = "exists" in dir_check.stdout

            if folder_exists and checkpoint_strategy_id() == strategy_id:
                print(f"Resuming — strategy folder present at {strategy_dir}, skipping scaffold.")
            elif folder_exists:
                raise RuntimeError(
                    f"Strategy folder '{strategy_id}' already exists on remote branch "
                    f"'strategy/{strategy_id}' without a matching checkpoint stamp. "
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

            idea_path = f"{REPO_PATH}/strategies/development/{strategy_id}/IDEA.md"
            get_sandbox(sandbox_id).files.write(idea_path, idea_text)

            strategy_architect = StrategyArchitectAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            architect_response = strategy_architect.run(idea_text, strategy_id=strategy_id)

            manifest = architect_response.parsed_output

            if not manifest:
                raise RuntimeError(f"Strategy architect failed to produce manifest: {architect_response.answer}")

            # Reason: host owns strategy_id; the architect's value is advisory. Override
            # before validation and caching so every downstream consumer (builders,
            # validator, checkpoint) sees a single source of truth.
            manifest = manifest.model_copy(update={"strategy_id": strategy_id})

            validate_manifest(manifest, expected_strategy_id=strategy_id)
            save_checkpoint("manifest", manifest.model_dump_json())

            manifest_path = f"{REPO_PATH}/strategies/development/{strategy_id}/MANIFEST.json"
            get_sandbox(sandbox_id).files.write(manifest_path, manifest.model_dump_json(indent=2))

            commit_and_push(sandbox_id, strategy_id, "architect: scaffold + IDEA + MANIFEST")

            return manifest

        finally:
            close_sandbox(sandbox_id)

    def _run_indicator_stage(self, strategy_id: str, manifest: StrategyManifest) -> IndicatorBuildResult:
        sandbox_id, _ = bootstrap_sandbox(strategy_id)
        print(f"[stage 3: indicators] sandbox {sandbox_id} started")

        try:
            indicator_builder = IndicatorBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            indicator_response = indicator_builder.run(manifest)

            indicator_result = indicator_response.parsed_output

            if not indicator_result:
                raise RuntimeError(f"Indicator builder failed: {indicator_response.answer}")

            save_checkpoint("indicators", indicator_result.model_dump_json())

            commit_and_push(sandbox_id, strategy_id, "indicators: build")

            return indicator_result

        finally:
            close_sandbox(sandbox_id)

    def _run_signal_stage(
        self,
        strategy_id: str,
        manifest: StrategyManifest,
        indicator_result: IndicatorBuildResult,
    ) -> SignalStrategyBuildResult:
        sandbox_id, _ = bootstrap_sandbox(strategy_id)
        print(f"[stage 4: signals] sandbox {sandbox_id} started")

        try:
            signal_strategy_builder = SignalStrategyBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            signal_response = signal_strategy_builder.run(manifest, indicator_result)

            signal_result = signal_response.parsed_output

            if not signal_result:
                raise RuntimeError(f"Signal+Strategy builder failed: {signal_response.answer}")

            save_checkpoint("signals", signal_result.model_dump_json())

            commit_and_push(sandbox_id, strategy_id, "signals: build")

            return signal_result

        finally:
            close_sandbox(sandbox_id)

    def _run_execution_stage(
        self,
        strategy_id: str,
        manifest: StrategyManifest,
        indicator_result: IndicatorBuildResult,
        signal_result: SignalStrategyBuildResult,
    ) -> None:
        sandbox_id, _ = bootstrap_sandbox(strategy_id)
        print(f"[stage 5: execution] sandbox {sandbox_id} started")

        try:
            execution_layer_builder = ExecutionLayerBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            execution_response = execution_layer_builder.run(manifest, indicator_result, signal_result)

            if not execution_response.parsed_output:
                raise RuntimeError(f"Execution layer builder failed: {execution_response.answer}")

            commit_and_push(sandbox_id, strategy_id, "execution: build")

        finally:
            close_sandbox(sandbox_id)

    def _run_validator_stage(self, strategy_id: str):
        sandbox_id, _ = bootstrap_sandbox(strategy_id)
        print(f"[stage 6: validator] sandbox {sandbox_id} started")

        try:
            validator = ValidatorAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            validation_response = validator.run(strategy_id=strategy_id)

            verdict = validation_response.parsed_output

            if not verdict:
                raise RuntimeError(f"Validator failed to produce verdict: {validation_response.answer}")

            commit_and_push(sandbox_id, strategy_id, "validator: ticker_universe + RESULTS")

            return verdict

        finally:
            close_sandbox(sandbox_id)


if __name__ == "__main__":
    strategy_builder = StrategyBuilder()
    strategy_builder.run()
