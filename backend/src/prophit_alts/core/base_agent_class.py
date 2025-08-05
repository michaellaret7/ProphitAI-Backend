import json
import os
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
from backend.src.prophit_alts.core.tools.data_wrapper_tool import ProphitAltsDataWrapper
from backend.src.prophit_alts.core.tools.search_engine_tool import AgentSearchEngine
from backend.src.utils.choose_model_and_client import *

load_dotenv()

class BaseAgent:
    def __init__(self, system_prompt: str, user_prompt: str):
        self.llm, self.client = openai_huggingface_model_and_client()
        # self.llm, self.client = openai_model_and_client(model='gpt-4.1-mini')
        self.tools = []
        self.tool_functions = {}
        self.max_iterations = 100
        self.verbose = True
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        
        # Register tools directly
        self._register_tools()

    def _register_tools(self):
        """Register all tools for this agent."""
        # Tool descriptions
        ticker_data_description = """
        The get_ticker_data tool returns a comprehensive dictionary of financial data for a given stock ticker. 
        This includes performance metrics like weekly returns and style factors (Momentum, Volatility, etc.), fundamental data such as financial statements and analyst estimates, 
        recent news, earnings transcript summaries, and stock grades.
        """
        
        search_description = """
        The free_search tool gives you the ability to search the web for information. 
        You will create an indepth query that will be entered into the Perplexity search engine.
        """
        
        # Register ticker data tool
        self.add_tool(
            name="get_ticker_data",
            description=ticker_data_description,
            parameters={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "The stock ticker symbol to get price for."},
                },
                "required": ["ticker"]
            },
            function=lambda ticker: ProphitAltsDataWrapper(ticker).run_all()
        )
        
        # Register search tool
        self.add_tool(
            name="free_search",
            description=search_description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query to search the web for. This query should be indepth and detailed, the more detailed the better the results wil be."},
                },
                "required": ["query"]
            },
            function=lambda query: AgentSearchEngine().perplexity_free_search(query)
        )

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
    
    def run(self) -> str:
        if self.verbose:
            print(f"🚀 Starting ReactAgent analysis...")
            print(f"Query: {self.user_prompt}")
            print("=" * 60)
            
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt}
        ]
        
        full_response = []
        iterations = 0
        
        while iterations < self.max_iterations:
            iterations += 1
            
            if self.verbose:
                print(f"\n⚜️  Iteration {iterations}")
            
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
            
            # Check for multiple Thought/Action pairs (which shouldn't happen)
            all_thoughts = re.findall(r'Thought:(.*?)(?=Action:|Thought:|$)', assistant_response, re.DOTALL)
            all_actions = re.findall(r'Action:(.*?)(?=Observation:|Action:|Thought:|$)', assistant_response, re.DOTALL)
            
            if len(all_thoughts) > 1 or len(all_actions) > 1:
                if self.verbose:
                    print(f"\n ⚠️ WARNING: Multiple Thought/Action pairs detected in response!")
                    print(f"   Found {len(all_thoughts)} Thoughts and {len(all_actions)} Actions")
                    print(f"   Only processing the first one. This may cause skipped actions.")
            
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
            
            # Get analysis from the model
            analysis_prompt = "Now provide your Analysis of this observation:"
            messages.append({"role": "user", "content": analysis_prompt})
            
            analysis_response = self.client.chat.completions.create(
                model=self.llm,
                messages=messages,
                temperature=0.7
            )
            
            analysis = analysis_response.choices[0].message.content
            
            # Extract analysis if it has the "Analysis:" prefix
            analysis_match = re.search(r'Analysis:(.*?)(?=$)', analysis, re.DOTALL)
            if analysis_match:
                analysis_text = analysis_match.group(1).strip()
            else:
                analysis_text = analysis.strip()
            
            analysis_output = f"Analysis: {analysis_text}"
            full_response.append(analysis_output)
            
            if self.verbose:
                print(f"\n{analysis_output}\n" + "="*50)
            
            # Add analysis to message history
            messages.append({"role": "assistant", "content": analysis})
        
        if iterations >= self.max_iterations:
            full_response.append("Reached maximum iterations without a final answer.")
            if self.verbose:
                print("\n ⚠️ Reached maximum iterations without a final answer.")
        
        if self.verbose:
            print(f"\n🎯 Analysis complete after {iterations} iterations!")
            print("=" * 60)
        
        return "\n\n".join(full_response)

