import openai
import json
import os
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from openai import OpenAI

class ReactAgent:
    def __init__(self, llm: str, api_key: Optional[str] = None, max_iterations: int = 10):
        self.llm = llm
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.tools = []
        self.tool_functions = {}
        self.max_iterations = max_iterations
        self.system_prompt = """
Role: You are a Senior Portfolio Risk-Analyst, specializing in portfolio stress testing and risk management.

Follow the Thought → Action → Observation loop internally:
1. Thought: brief reasoning.
2. Action: call ONE tool exactly like  
   Action: tool_name(param=value, …)
3. Observation: reflect on the tool result.

Available tools
• get_tickers() --> returns list of tickers
• calculate_stock_metrics(start_date_str:string, end_date_str:string) --> returns {"ticker": {max_drawdown: %, annualized_volatility: %, ...}} (for all tickers in the specified date range)
• get_stock_data(ticker:string, start_date_str:string, end_date_str:string) --> returns full hourly price history for deeper analysis

After analysing every ticker, output:

Final Answer: {
  "weakest_ticker": "string",
  "drivers": ["string", …]        # short bullet explanations
}
"""

    def add_tool(self, name: str, description: str, parameters: Dict, function: Callable):
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self.tools.append(tool_def)
        self.tool_functions[name] = function
    
    def execute_tool(self, function_name: str, arguments: Dict) -> str:
        if function_name not in self.tool_functions:
            return f"Error: Tool '{function_name}' not found"
        
        return self.tool_functions[function_name](**arguments)
    
    def parse_action(self, action_text: str) -> Tuple[str, Dict]:
        """Parse action text into function name and arguments."""
        # Pattern: Action: tool_name(param1=value1, param2=value2, ...)
        match = re.match(r'Action:\s*(\w+)\((.*)\)', action_text)
        if not match:
            return None, {}
        
        function_name = match.group(1)
        args_text = match.group(2)
        
        # Parse arguments
        args_dict = {}
        if args_text.strip():
            # Simple parsing - in a real implementation, use a more robust parser
            for arg_pair in args_text.split(','):
                if '=' in arg_pair:
                    key, value = arg_pair.split('=', 1)
                    # Clean up and attempt to parse values (basic)
                    key = key.strip()
                    value = value.strip()
                    
                    # Strip quotes from string values (handle both single and double quotes)
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    # Try to parse as JSON if it looks like a data structure
                    elif value.startswith('{') or value.startswith('[') or value in ('true', 'false', 'null') or value.isdigit():
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    args_dict[key] = value
        
        return function_name, args_dict
    
    def run(self, user_query: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        full_response = []
        iterations = 0
        
        while iterations < self.max_iterations:
            iterations += 1
            
            response = self.client.chat.completions.create(
                model=self.llm,
                messages=messages,
                temperature=0.7,
                verbose=True
            )
            
            assistant_response = response.choices[0].message.content
            
            # Check if this is a direct answer (no action)
            if "Action:" not in assistant_response:
                # If it's just a thought or a direct answer
                full_response.append(assistant_response)
                break
            
            # Extract thought, action, and add to full response
            thought_match = re.search(r'Thought:(.*?)(?=Action:|$)', assistant_response, re.DOTALL)
            action_match = re.search(r'Action:(.*?)(?=Observation:|$)', assistant_response, re.DOTALL)
            
            thought = thought_match.group(1).strip() if thought_match else ""
            action_text = action_match.group(1).strip() if action_match else ""
            
            # Add the thought and action to our collected response
            full_response.append(f"Thought: {thought}")
            full_response.append(f"Action: {action_text}")
            
            # Parse and execute the action
            function_name, arguments = self.parse_action(f"Action: {action_text}")
            
            if function_name is None:
                observation = "Error: Could not parse the action correctly."
            else:
                observation = self.execute_tool(function_name, arguments)
            
            full_response.append(f"Observation: {observation}")
            
            # Add to messages for context
            messages.append({"role": "assistant", "content": assistant_response})
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        
        if iterations >= self.max_iterations:
            full_response.append("Reached maximum iterations without a final answer.")
        
        return "\n\n".join(full_response)

