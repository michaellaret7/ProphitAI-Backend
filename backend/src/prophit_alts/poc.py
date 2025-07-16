import json
import os
import re
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
from backend.src.prophit_alts.core.equip_tools import register_tools
from backend.src.utils.choose_model_and_client import openai_model_and_client, deepseek_model_and_client

load_dotenv()

class RetailFundCIO:
    def __init__(self):
        self.llm, self.client = deepseek_model_and_client()
        self.tools = []
        self.tool_functions = {}
        self.max_iterations = 100
        self.verbose = True
        self.system_prompt = """
Role: You are low level analyst who reports returns for a given ticker.

Follow the Thought → Action → Observation loop internally:
1. Thought: brief reasoning.
2. Action: call ONE tool exactly like  
   Action: tool_name(param=value, …)
3. Observation: reflect on the tool result.

list of tickers --> [msft, aapl, lmt, nvda, avgo, amzn, tsla, jpm, unh]

<instructions>
- Call get_ticker_daily_total_returns(ticker) to get the historical stock data for a given ticker.
- After getting the stock data, you must analyze the data and report the results.
- Write an anlysis report on how the stock performed in the time window of the data you have.
- Pick ONE and only ONE stock to go long because you think it will outperform the others.
- Pick ONE and only ONE stock to go short because you think it will underperform the others.
</instructions>

<rules>
- You may NOT hallucinate, if there is data returned by the tool and it is missing, you must say so.
- Do not use a tool for the analysis phase, only use tools for data fetching.
- you must run the tools and analysis for EVERY ticker in the list.
</rules>

Tools:
- get_ticker_daily_total_returns(ticker:string) --> returns full daily price history for deeper analysis
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
        if self.verbose:
            print(f"🚀 Starting ReactAgent analysis...")
            print(f"Query: {user_query}")
            print("=" * 60)
            
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        full_response = []
        iterations = 0
        
        while iterations < self.max_iterations:
            iterations += 1
            
            if self.verbose:
                print(f"\n🔄 Iteration {iterations}")
            
            response = self.client.chat.completions.create(
                model=self.llm,
                messages=messages,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            
            # Check if this is a direct answer (no action)
            if "Action:" not in assistant_response:
                # If it's just a thought or a direct answer
                full_response.append(assistant_response)
                if self.verbose:
                    print(f"\n✅ Final Answer: {assistant_response}")
                break
            
            # Extract thought, action, and add to full response
            thought_match = re.search(r'Thought:(.*?)(?=Action:|$)', assistant_response, re.DOTALL)
            action_match = re.search(r'Action:(.*?)(?=Observation:|$)', assistant_response, re.DOTALL)
            
            thought = thought_match.group(1).strip() if thought_match else ""
            action_text = action_match.group(1).strip() if action_match else ""
            
            # Add the thought and action to our collected response
            thought_output = f"Thought: {thought}"
            action_output = f"Action: {action_text}"
            full_response.append(thought_output)
            full_response.append(action_output)
            
            # Print in real-time if verbose
            if self.verbose:
                print(f"\n{thought_output}")
                print(f"{action_output}")
            
            # Parse and execute the action
            function_name, arguments = self.parse_action(f"Action: {action_text}")
            
            if function_name is None:
                observation = "Error: Could not parse the action correctly."
            else:
                if self.verbose:
                    print("Executing tool...")
                observation = self.execute_tool(function_name, arguments)
            
            observation_output = f"Observation: {observation}"
            full_response.append(observation_output)
            
            # Print observation in real-time if verbose
            if self.verbose:
                print(f"{observation_output}\n" + "="*50)
            
            # Add to messages for context
            messages.append({"role": "assistant", "content": assistant_response})
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        
        if iterations >= self.max_iterations:
            full_response.append("Reached maximum iterations without a final answer.")
            if self.verbose:
                print("\n ⚠️ Reached maximum iterations without a final answer.")
        
        if self.verbose:
            print(f"\n🎯 Analysis complete after {iterations} iterations!")
            print("=" * 60)
        
        return "\n\n".join(full_response)


start_time = time.time()
agent = RetailFundCIO()
register_tools(agent)
# Get the output and write to file
output = agent.run("Analyze the stocks and come up with a trading strategy for each of them")

# Create output filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_filename = f"trading_strategy_analysis_{timestamp}.txt"
output_path = os.path.join(os.path.dirname(__file__), output_filename)

# Write output to file
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"Multi-Stock Trading Strategy Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("Stocks: MSFT, AAPL, LMT\n")
    f.write("=" * 60 + "\n\n")
    f.write(output)

end_time = time.time()
elapsed_time = end_time - start_time
print(f"Analysis complete! Output saved to: {output_path}")
print(f"Execution time: {elapsed_time:.2f} seconds")
