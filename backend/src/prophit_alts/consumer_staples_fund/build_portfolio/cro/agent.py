from backend.src.agentic_framework.base_agent.agent import BaseAgent
from backend.src.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.cro.tool_registry import register_cro_tools
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cro_agent_prompts import cro_system_prompt, cro_user_prompt
from pydantic import BaseModel
from typing import List, Literal
import json

print(f"""
╔═══════════════════════════════════════════════╗                                             
║  ╔═╗╦═╗╔═╗╔═╗╦ ╦╦╔╦╗╔═╗╦                      ║
║  ╠═╝╠╦╝║ ║╠═╝╠═╣║ ║ ╠═╣║                      ║
║  ╩  ╩╚═╚═╝╩  ╩ ╩╩ ╩ ╩ ╩╩                      ║
║  Agent: CRO Agent                             ║
║  Fund: Consumer Staples Fund                  ║
╚═══════════════════════════════════════════════╝
""")

class CROPortfolioItem(BaseModel):
	ticker: str
	position: Literal["long", "short"]
	weight: float
	reason: str

class ActionableSuggestion(BaseModel):
	ticker: str
	action: Literal["increase allocation", "decrease allocation", "drop position"]
	amount: float = None  
	reason: str

class FinalPortfolio(BaseModel):
	portfolio: List[CROPortfolioItem]

class PortfolioWithSuggestions(BaseModel):
	portfolio: List[CROPortfolioItem]
	suggestions: List[ActionableSuggestion]

class CROAgent(BaseAgent):
    def __init__(self, system_prompt: str = cro_system_prompt, user_prompt: str = cro_user_prompt):
        super().__init__(system_prompt, user_prompt, max_iterations=75, save_messages=True, model="gpt-4.1", verbose=True, memory_refresh_interval=10)
        
        register_cro_tools(self)
    
    def _initialize_semantic_memory(self):
        """Initialize CRO-specific semantic memories for risk management."""
        # Initialize semantic memory for CRO agent
        self.semantic_memory = SemanticMemory(agent_type='cro', save_memory=True, verbose=self.verbose)
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.semantic_memory.memories.values())
            if total_memories == 0:
                print("⚠️ No CRO memories found - agent will have no risk management knowledge!")
            else:
                print(f"🧠 CRO Agent loaded with {total_memories} risk management memories")

    def run(self):
        result = super().run() # Run main BaseAgent workflow

        final_text = (result.get("final_text") or "").strip()
        
        if not final_text:
            return result
        
        # Strip "Final Answer:" prefix if present
        if final_text.startswith("Final Answer:"):
            final_text = final_text[len("Final Answer:"):].strip()
        
        try:
            # First try to parse as PortfolioWithSuggestions (new format)
            # Use OpenAI to parse final output and return a PortfolioWithSuggestions Pydantic Object
            final_comp = self.client.chat.completions.parse(
                model=self.llm,
                messages=[
                    {"role": "system", "content": "Convert the output to match the PortfolioWithSuggestions schema format with both 'portfolio' and 'suggestions' keys. If no suggestions are provided, use an empty suggestions array."},
                    {"role": "user", "content": final_text},
                ],
                response_format=PortfolioWithSuggestions,
            )
            parsed: PortfolioWithSuggestions = final_comp.choices[0].message.parsed
            
            # Format output to include both portfolio and suggestions
            output_data = {
                "portfolio": [item.model_dump() for item in parsed.portfolio],
                "suggestions": [item.model_dump() for item in parsed.suggestions]
            }
            result["final_text"] = json.dumps(output_data)
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ PortfolioWithSuggestions parse failed, trying FinalPortfolio fallback: {e}")
            
            # Fallback to original FinalPortfolio parsing for backward compatibility
            try:
                final_comp = self.client.chat.completions.parse(
                    model=self.llm,
                    messages=[
                        {"role": "system", "content": "Convert the JSON array to match the schema format with a 'portfolio' key."},
                        {"role": "user", "content": final_text},
                    ],
                    response_format=FinalPortfolio,
                )
                parsed: FinalPortfolio = final_comp.choices[0].message.parsed
                
                # Format as portfolio-only output (empty suggestions)
                output_data = {
                    "portfolio": [item.model_dump() for item in parsed.portfolio],
                    "suggestions": []
                }
                result["final_text"] = json.dumps(output_data)
                
            except Exception as e2:
                if self.verbose:
                    print(f"⚠️ All parsing failed, keeping original: {e2}")
                pass
        
        return result["final_text"]

if __name__ == "__main__":
    agent = CROAgent()
    result = agent.run()

    print("="*100)
    print("CRO Agent Result:")
    print("="*100)
    print(result)



