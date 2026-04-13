from prophitai_fund.idea_generation.agent import IdeaGeneratorAgent
from prophitai_fund.research.architect.agent import StrategyArchitectAgent
from prophitai_fund.research.builders.indicators import IndicatorBuilderAgent
from prophitai_fund.research.builders.signals import SignalStrategyBuilderAgent
from prophitai_fund.research.builders.execution import ExecutionLayerBuilderAgent
from prophitai_tools.sandbox.client import create_sandbox
from prophitai_tools.sandbox.lifecycle import close_sandbox

MODEL = "minimax-m2.7"
PROVIDER = "together"

class StrategyBuilder:
    def __init__(self):
        self.idea_generator = IdeaGeneratorAgent(model=MODEL, provider=PROVIDER)

    def run(self):
        sandbox_id, _ = create_sandbox()

        try:
            idea = self.idea_generator.run()

            if not idea.parsed_output:
                raise RuntimeError(f"Idea generation failed: {idea.answer}")

            strategy_architect = StrategyArchitectAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            architect_response = strategy_architect.run(idea.answer)

            manifest = architect_response.parsed_output

            if not manifest:
                raise RuntimeError(f"Strategy architect failed to produce manifest: {architect_response.answer}")

            indicator_builder = IndicatorBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            indicator_response = indicator_builder.run(manifest)

            indicator_result = indicator_response.parsed_output

            if not indicator_result:
                raise RuntimeError(f"Indicator builder failed: {indicator_response.answer}")

            signal_strategy_builder = SignalStrategyBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            signal_response = signal_strategy_builder.run(manifest, indicator_result)

            signal_result = signal_response.parsed_output

            if not signal_result:
                raise RuntimeError(f"Signal+Strategy builder failed: {signal_response.answer}")

            execution_layer_builder = ExecutionLayerBuilderAgent(model=MODEL, provider=PROVIDER, sandbox_id=sandbox_id)
            execution_response = execution_layer_builder.run(manifest, indicator_result, signal_result)

            execution_result = execution_response.parsed_output

            if not execution_result:
                raise RuntimeError(f"Execution layer builder failed: {execution_response.answer}")

            return execution_result

        finally:
            close_sandbox(sandbox_id)


if __name__ == "__main__":
    strategy_builder = StrategyBuilder()
    strategy_builder.run()