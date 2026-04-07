from prophitai_fund.idea_generator.agent import IdeaGeneratorAgent
from prophitai_fund.researcher.architect.agent import StrategyArchitectAgent
from prophitai_tools.sandbox.client import create_sandbox                                                                                                                                                

class Fund:
    def __init__(self, name: str):
        self.name = name
        self.idea_generator = IdeaGeneratorAgent()
        self.strategy_architect = StrategyArchitectAgent()

    def run(self):
        idea = self.idea_generator.run()

        sandbox_id = create_sandbox()
        strategy = self.strategy_architect.run(idea, sandbox_id)

        return strategy