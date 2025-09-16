from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cio_agent_prompts import cio_system_prompt, cio_user_prompt
from .tool_registry import register_cio_tools
from backend.src.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory

class CIOAgent(BaseAgent):
    def __init__(self):
        super().__init__(cio_system_prompt, cio_user_prompt, max_iterations=250, plan_first=True, save_messages=True, model="gpt-5", verbose=True, memory_refresh_interval=10)
        
        register_cio_tools(self)

    def _initialize_semantic_memory(self):
        """Initialize CIO-specific semantic memories for portfolio construction."""
        # Initialize semantic memory for CRO agent
        self.semantic_memory = SemanticMemory(agent_type='cio', save_memory=True, verbose=self.verbose)
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.semantic_memory.memories.values())
            if total_memories == 0:
                print("⚠️ No CIO memories found - agent will have no portfolio construction knowledge!")
            else:
                print(f"🧠 CIO Agent loaded with {total_memories} portfolio construction memories")

    def run(self):
        result = super().run()

        final_text = (result.get("final_text") or "").strip()
        if not final_text:
            return result

        if final_text.startswith("Final Answer:"):
            final_text = final_text[len("Final Answer:"):].strip()

        return result["final_text"]


if __name__ == "__main__":
    agent = CIOAgent()
    result = agent.run()
    print("="*100)
    print("CIO Agent Result:")
    print("="*100)
    print(result)





   






    

