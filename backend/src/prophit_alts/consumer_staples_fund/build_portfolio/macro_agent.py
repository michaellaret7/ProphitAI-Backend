from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.macro_agent_prompts import macro_analyst_system_prompt, macro_analyst_user_prompt
import re
import json
import sys
from io import StringIO
from contextlib import redirect_stdout

class MacroAnalyst(BaseAgent):
    def __init__(self):
        super().__init__(macro_analyst_system_prompt, macro_analyst_user_prompt)

    def run(self):
        return super().run()

    def get_final_recommendation(self):
        """
        Get clean JSON recommendation without ReAct formatting.
        Returns the JSON output extracted from <output></output> tags.
        Suppresses all print output when used as a tool.
        """
        # Capture and suppress all print output
        f = StringIO()
        try:
            with redirect_stdout(f):
                # Temporarily disable verbose output
                original_verbose = self.verbose
                self.verbose = False
                
                full_output = self.run()
                
                # Restore original verbose setting
                self.verbose = original_verbose
            
            # Extract JSON from <output></output> tags
            output_match = re.search(r'<output>(.*?)</output>', full_output, re.DOTALL)
            if output_match:
                json_str = output_match.group(1).strip()
                try:
                    # Parse and return the JSON to ensure it's valid
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the raw content
                    return json_str
            
            # Fallback: return full output if no <output> tags found
            return full_output
            
        except Exception as e:
            # If anything goes wrong, restore verbose and re-raise
            self.verbose = True
            raise e

if __name__ == "__main__":
    macro_agent = MacroAnalyst()
    macro_agent.run()
