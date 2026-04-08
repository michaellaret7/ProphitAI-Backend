from prophitai_fund.idea_generator.agent import IdeaGeneratorAgent
from prophitai_fund.researcher.architect.agent import StrategyArchitectAgent
from prophitai_tools.sandbox.client import create_sandbox
from prophitai_tools.sandbox.lifecycle import bootstrap_repo, close_sandbox

class Fund:
    def __init__(self, name: str):
        self.name = name
        self.idea_generator = IdeaGeneratorAgent()

    def run(self):
        idea = self.idea_generator.run()

        # Try to create the sandbox, if it fails, return the error and stop the pipeline
        try:
            sandbox_id, sandbox = create_sandbox()
            bootstrap_repo(sandbox, "fund_research") # this sets up the env for the virtual machine

        except Exception as e:
            print(f"Error creating sandbox: {e}")
            return None

        # Try to run the strategy architect, if it fails, return the error and stop the pipeline
        try:
            architect = StrategyArchitectAgent(sandbox_id=sandbox_id)
            manifest = architect.run(idea.answer)
            print(manifest.parsed_output)

        except Exception as e:
            print(f"Error running strategy architect: {e}")
            return None

        finally:
            close_sandbox(sandbox_id)
            print("Sandbox closed")

        return manifest


if __name__ == "__main__":
    fund = Fund("ProphitAI Fund")
    manifest = fund.run()
    print(manifest)