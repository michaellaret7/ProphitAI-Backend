"""Agent utility functions for BaseAgent."""

import json
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class StepTrace:
    iteration: int
    assistant_raw: str = ""
    tool_call: Optional[Dict[str, Any]] = None
    observation: Optional[Any] = None
    analysis: Optional[str] = None


class AgentUtilities:
    """Utility functions for BaseAgent operations."""
    
    def __init__(self, agent):
        """Initialize with reference to parent agent for accessing tools and state."""
        self.agent = agent
    
    def _strip_functions_prefix(self, name: str) -> str:
        """Remove 'functions.' prefix from tool name if present."""
        if name and name.startswith("functions."):
            return name[10:]
        return name
    
    def system_rules(self) -> str:
        """Return system rules for the agent - Enhanced for GPT-4.1."""
        # More explicit instructions for GPT-4.1 to ensure consistent JSON output
        return (
            "You MUST use one of these two formats:\n"
            "1. Native tool-calls (preferred if supported)\n"
            "2. JSON format: {\"thought\":\"...\",\"action\":{\"tool\":\"name\",\"args\":{}}}\n\n"
            "3. The list can be as long as you want, the priority is to complete the task at hand as accurately and analytically as possible.\n"
            "CRITICAL RULES:\n"
            "- NEVER output plain text like 'Thought: ...' or 'Action: ...'\n"
            "- ALWAYS use complete JSON objects when not using native tool calls\n"
            "- Use exact tool names WITHOUT 'functions.' prefix (e.g., 'calculator' not 'functions.calculator')\n"
            "- Do NOT invent wrapper tools like 'multi_tool_use.parallel'\n"
            "- When ready to finalize, output 'Final Answer:' followed by your answer\n\n"
            "TASK MANAGEMENT PROTOCOL:\n"
            "- Use the 'update_task_status' or 'mark_task_complete' tools to update task progress\n"
            "- When you complete a task, explicitly call the tool with evidence\n"
            "- Stay focused on your current task until it's complete before moving on\n"
            "- Provide clear evidence for task completion in the tool call\n"
            "- If you can't use the tools, state 'Step X complete' or 'Task X done' clearly\n\n"
            "IMPORTANT: If you find yourself outputting 'functions.' prefix, remove it immediately."
        )
    
    def accumulate_usage(self, response) -> None:
        """Accumulate token usage from response."""
        try:
            if hasattr(response, "usage") and response.usage and response.usage.total_tokens:
                self.agent.total_tokens += int(response.usage.total_tokens)
        except Exception:
            pass
    
    def _get_function_params(self, func: callable) -> List[str]:
        """Extract parameter names from a function signature.
        
        Args:
            func: The function to inspect
            
        Returns:
            List of parameter names excluding 'self' and var args
        """
        try:
            import inspect
            sig = inspect.signature(func)
            params = []
            for pname, p in sig.parameters.items():
                if pname != 'self' and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    params.append(pname)
            return params
        except Exception:
            return []
    
    def _attempt_auto_retry(self, name: str, args: Dict[str, Any], error_msg: str, 
                           error_response: str, func: callable) -> Any:
        """Helper method to attempt auto-retry with error memory solution.
        
        Args:
            name: Tool name
            args: Original arguments that failed
            error_msg: The error message
            error_response: The formatted error response
            func: The tool function
            
        Returns:
            Retry result if successful, error response otherwise
        """
        if not self.agent.error_memory or not func:
            return error_response
            
        error_key = self.agent.error_memory.record_error(name, args, error_msg)
        solution = self.agent.error_memory.get_solution(name, error_msg)
        
        if solution:
            if self.agent.verbose:
                print(f"🔄 Auto-retrying {name} with corrected arguments from memory")
            
            # Get expected params for merging
            expected_params = self._get_function_params(func)
            
            retry_args = self._merge_args_with_solution(args, solution.get('example_args', {}), expected_params)
            
            # Store error info for tracking
            self.agent.last_tool_error = {
                'tool_name': name,
                'error_key': error_key,
                'error_message': error_msg,
                'failed_args': args
            }
            
            # Attempt retry
            retry_result = self.execute_tool_safe(name, retry_args, is_retry=True)
            
            # Check if retry was successful
            if not isinstance(retry_result, str) or not any(retry_result.startswith(e) for e in ["Error", "Unhandled"]):
                if self.agent.verbose:
                    print(f"✅ Auto-retry successful for {name}!")
                self.agent.error_memory.record_solution(
                    error_key,
                    retry_args,
                    "Auto-retry with memory solution succeeded"
                )
                self.agent.last_tool_error = None
                self.agent.last_tool_auto_retry_success = True
                return retry_result
            else:
                # Retry failed
                if self.agent.verbose:
                    print(f"⚠️ Auto-retry failed for {name}")
                return (
                    f"{error_response}\n\n"
                    f"💡 AUTO-RETRY ATTEMPTED:\n"
                    f"{solution['guidance']}\n\n"
                    f"Manual correction may be needed."
                )
        else:
            # No solution found, store error for future learning
            self.agent.last_tool_error = {
                'tool_name': name,
                'error_key': error_key,
                'error_message': error_msg,
                'failed_args': args
            }
            return error_response
    
    def execute_tool_safe(self, name: str, args: Dict[str, Any], is_retry: bool = False):
        """Safely execute a tool with error handling, memory, and auto-retry."""
        if not name:
            return f"Error: tool name is None or empty. Available tools: {list(self.agent.tool_functions.keys())}"
        name = self._strip_functions_prefix(name)
        func = self.agent.tool_functions.get(name)
        if not func:
            # Try to find the tool with case-insensitive matching as fallback
            for tool_name, tool_func in self.agent.tool_functions.items():
                if tool_name and name and tool_name.lower() == name.lower():
                    func = tool_func
                    break
            if not func:
                return f"Error: tool '{name}' not found. Available tools: {list(self.agent.tool_functions.keys())}"
        try:
            # Auto-inject _simulation_date for simulation agents
            if self.agent.simulation_date is not None and isinstance(args, dict):
                args['_simulation_date'] = self.agent.simulation_date

            result = func(**args) if isinstance(args, dict) else func(args)

            # If this was a retry after an error and it succeeded, record the solution
            if self.agent.error_memory and self.agent.last_tool_error:
                if self.agent.last_tool_error.get('tool_name') == name:
                    self.agent.error_memory.record_solution(
                        self.agent.last_tool_error['error_key'],
                        args,
                        "Successful retry with corrected arguments"
                    )
                    self.agent.last_tool_error = None  # Clear the error
                    if self.agent.verbose:
                        print("✅ Tool succeeded after error correction!")
            
            return result
            
        except TypeError as e:
            error_msg = str(e)
            error_response = f"Error calling tool '{name}': {error_msg} (args={args})"
            # Opportunistic fix: if required 'portfolio_dict' is missing, infer from recent observations
            try:
                if ("required positional argument" in error_msg or "missing" in error_msg) and "'portfolio_dict'" in error_msg:
                    inferred = self._infer_portfolio_dict_from_context()
                    if inferred:
                        retry_args = dict(args or {})
                        retry_args['portfolio_dict'] = inferred
                        if self.agent.verbose:
                            print("🔧 Auto-injecting 'portfolio_dict' inferred from recent context and retrying")
                        return self.execute_tool_safe(name, retry_args, is_retry=True)
            except Exception:
                pass

            # Attempt auto-retry if not already a retry
            if not is_retry:
                return self._attempt_auto_retry(name, args, error_msg, error_response, func)

            return error_response
            
        except Exception as e:
            error_msg = str(e)
            error_response = f"Unhandled error in tool '{name}': {error_msg}"
            
            # Attempt auto-retry if not already a retry
            if not is_retry:
                return self._attempt_auto_retry(name, args, error_msg, error_response, func)
            
            return error_response

    def _infer_portfolio_dict_from_context(self) -> Optional[Dict[str, Any]]:
        """Infer a portfolio_dict-shaped object from recent tool observations.

        Looks for a dict mapping ticker-> {allocation/conviction/risk_allocation, position}.
        Falls back to common containers (e.g., under keys 'portfolio', 'positions', 'holdings').
        """
        def _looks_like_ticker(k: Any) -> bool:
            return isinstance(k, str) and k.isalpha() and 1 <= len(k) <= 10
        def _looks_like_position_dict(v: Any) -> bool:
            if not isinstance(v, dict):
                return False
            has_alloc = any(x in v for x in ['allocation', 'conviction', 'risk_allocation'])
            has_pos = isinstance(v.get('position'), str)
            return has_alloc and has_pos
        # Search last few observations for a usable mapping
        try:
            for obs in reversed(getattr(self.agent, 'recent_observations', [])[-8:]):
                candidate = None
                if isinstance(obs, dict):
                    # Direct mapping of tickers
                    if obs and all(_looks_like_ticker(k) and _looks_like_position_dict(v) for k, v in obs.items()):
                        candidate = obs
                    else:
                        # Nested common keys
                        for key in ('portfolio', 'positions', 'holdings'):
                            inner = obs.get(key)
                            if isinstance(inner, dict) and inner and all(_looks_like_ticker(k) and _looks_like_position_dict(v) for k, v in inner.items()):
                                candidate = inner
                                break
                if candidate:
                    return candidate
        except Exception:
            return None
        return None
    
    def _merge_args_with_solution(self, failed_args: Dict[str, Any], solution_args: Dict[str, Any], expected_params: List[str] = None) -> Dict[str, Any]:
        """Merge failed arguments with solution template intelligently.
        
        Args:
            failed_args: The arguments that caused the error
            solution_args: Example arguments from the memory solution
            expected_params: Parameter names expected by the tool function
            
        Returns:
            Merged arguments that should work
        """
        # Start with solution template
        merged = solution_args.copy()
        expected = set(expected_params or [])
        
        # Special case: if solution needs portfolio_dict and we can infer one, use it
        if 'portfolio_dict' in merged and merged['portfolio_dict']:
            inferred = self._infer_portfolio_dict_from_context()
            if inferred:
                merged['portfolio_dict'] = inferred
        
        # Remap common synonyms to expected param names if needed
        synonyms_map = {
            'portfolio': ['portfolio_dict', 'portfolio_data'],
            'portfolio_dict': ['portfolio', 'portfolio_data'],
            'portfolio_data': ['portfolio', 'portfolio_dict'],
        }
        for src_key, alt_keys in list(synonyms_map.items()):
            if src_key in merged and src_key not in expected:
                for alt in alt_keys:
                    if alt in expected:
                        merged[alt] = merged.pop(src_key)
                        break
        
        # For portfolio-specific tools, try to extract portfolio data from context
        if 'portfolio' in solution_args and not failed_args.get('portfolio'):
            # Check if there's a get_final_portfolio_dict result in recent observations
            if hasattr(self.agent, 'recent_observations'):
                for obs in reversed(self.agent.recent_observations[-5:]):  # Check last 5 observations
                    if isinstance(obs, dict) and any(key in obs for key in ['portfolio', 'positions', 'holdings']):
                        # Found portfolio data in recent observations
                        if 'portfolio' in obs:
                            merged['portfolio'] = obs['portfolio']
                        elif 'positions' in obs:
                            merged['portfolio'] = obs['positions']
                        elif 'holdings' in obs:
                            merged['portfolio'] = obs['holdings']
                        break
        
        # Override with any valid non-empty values from failed args
        for key, value in failed_args.items():
            if value is not None and value != {} and value != [] and value != "":
                # Keep the user's value if it's meaningful
                merged[key] = value
        
        return merged
    
    def _parse_plain_args(self, args_str: str) -> Dict[str, Any]:
        """Parse arguments from plain text format."""
        args = {}
        if not args_str:
            return args
            
        # Try JSON format first
        try:
            return json.loads("{" + args_str + "}")
        except json.JSONDecodeError:
            pass
            
        # Parse key=value pairs
        for pair in args_str.split(','):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                args[key.strip().strip('"\'')]  = value.strip().strip('"\'')
        
        return args
    
    def maybe_parse_json_step(self, content: str) -> Optional[Dict[str, Any]]:
        """Try to parse JSON step format from content - Enhanced for GPT-4.1."""
        content = (content or "").strip()
        if not content:
            return None
            
        # Check plain text format: "Action: tool_name(args)"
        plain_match = re.search(r'Action:\s*([a-zA-Z_\.]+)\s*\(([^)]*)\)', content, re.IGNORECASE)
        if plain_match:
            tool_name = self._strip_functions_prefix(plain_match.group(1))
            args_str = plain_match.group(2) if len(plain_match.groups()) > 1 else ""
            return {"tool": tool_name, "args": self._parse_plain_args(args_str)}
        
        # Try standard JSON parsing
        try:
            obj = json.loads(content)
            if isinstance(obj, dict) and "action" in obj and isinstance(obj["action"], dict):
                action = obj["action"]
                if "tool" in action and isinstance(action["tool"], str):
                    action["tool"] = self._strip_functions_prefix(action["tool"])
                return action
        except json.JSONDecodeError:
            pass
            
        # Try to find JSON object inside text
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict) and "action" in obj and isinstance(obj["action"], dict):
                    action = obj["action"]
                    if "tool" in action and isinstance(action["tool"], str):
                        action["tool"] = self._strip_functions_prefix(action["tool"])
                    return action
            except json.JSONDecodeError:
                pass
                
        return None
    
    def looks_final(self, text: str) -> bool:
        """Check if text indicates a final answer."""
        if not text:
            return False
        text_lower = text.strip().lower()
        
        # Check for various final answer patterns (case-insensitive)
        if text_lower.startswith("final answer:"):
            return True
        if "final answer:" in text_lower:
            return True
            
        # If the model returned a JSON with final true (rare when using content), accept
        try:
            j = json.loads(text)
            if isinstance(j, dict) and j.get("final") is True:
                return True
        except Exception:
            pass
        return False
    
    def extract_last_final(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Extract the last assistant message from messages."""
        for m in reversed(messages):
            if m["role"] == "assistant" and isinstance(m.get("content"), str):
                c = m["content"]
                if c and c.strip():
                    return c
        return None
    
    def stringify(self, observation: Any) -> str:
        """Convert observation to string format that is robustly JSON-serializable."""
        def _default(o):
            # Enums → use their value
            try:
                from enum import Enum
                if isinstance(o, Enum):
                    return o.value
            except Exception:
                pass
            
            # Dataclasses → asdict
            try:
                import dataclasses
                if dataclasses.is_dataclass(o):
                    return dataclasses.asdict(o)
            except Exception:
                pass
            
            # Pydantic v2 BaseModel → model_dump(mode="json")
            try:
                from pydantic import BaseModel  # type: ignore
                if isinstance(o, BaseModel):
                    return o.model_dump(mode="json")
            except Exception:
                pass
            
            # Pydantic-like objects with model_dump
            try:
                if hasattr(o, "model_dump") and callable(getattr(o, "model_dump")):
                    return o.model_dump()
            except Exception:
                pass
            
            # Pydantic v1 models → dict()
            try:
                if hasattr(o, "dict") and callable(getattr(o, "dict")):
                    return o.dict()
            except Exception:
                pass
            
            # Sets → list
            if isinstance(o, set):
                return list(o)
            
            # Fallback: string representation
            return str(o)
        
        try:
            if isinstance(observation, str):
                return observation
            # Prefer JSON so downstream LLM sees structured content
            return json.dumps(observation, ensure_ascii=False, default=_default)
        except Exception:
            # Final fallback to plain string or placeholder
            try:
                return str(observation)
            except Exception:
                return "<unserializable observation>"
    
    def update_stagnation(self, name: str, args: Dict[str, Any]):
        """Update stagnation detection for repeated actions."""
        name = self._strip_functions_prefix(name)
        # Filter out _simulation_date for stagnation key (not JSON serializable)
        stag_args = {k: v for k, v in args.items() if k != '_simulation_date'}
        key = f"{name}:{json.dumps(stag_args, sort_keys=True)}"
        if key in self.agent._recent_actions:
            self.agent._stuck_count += 1
        else:
            self.agent._stuck_count = 0
        self.agent._recent_actions.append(key)
        if len(self.agent._recent_actions) > 16:
            self.agent._recent_actions.pop(0)
    
    def trace_to_dict(self, s: StepTrace) -> Dict[str, Any]:
        """Convert StepTrace to dictionary."""
        return {
            "iteration": s.iteration,
            "assistant_raw": s.assistant_raw,
            "tool_call": s.tool_call,
            "observation": s.observation,
            "analysis": s.analysis,
        }
    
    def parse_agent_output(
        self,
        final_text: str,
        client,
        llm: str,
        response_format,
        output_key: str,
        fallback_formats: Optional[List[tuple]] = None,
        verbose: bool = True
    ) -> str:
        """
        Parse agent output text into structured JSON format.
        
        Args:
            final_text: Raw output text from agent
            client: OpenAI client instance
            llm: Model name for parsing
            response_format: Primary Pydantic model for parsing
            output_key: Key name for the parsed data (e.g., 'portfolio', 'recommendations')
            fallback_formats: Optional list of (format, key) tuples for fallback parsing
            verbose: Whether to print debug messages
        
        Returns:
            JSON string of parsed data
        """
        # Strip "Final Answer:" prefix if present
        final_text = final_text.strip()
        if final_text.startswith("Final Answer:"):
            final_text = final_text[len("Final Answer:"):].strip()
        
        # Try primary format
        try:
            final_comp = client.chat.completions.parse(
                model=llm,
                messages=[
                    {"role": "system", "content": f"Convert the output to match the schema format with a '{output_key}' key."},
                    {"role": "user", "content": final_text},
                ],
                response_format=response_format,
            )
            parsed = final_comp.choices[0].message.parsed
            
            # Build output data
            output_data = {
                output_key: [item.model_dump() for item in getattr(parsed, output_key)]
            }
            
            # For CRO agent with suggestions - handle both keys if present
            if hasattr(parsed, 'suggestions'):
                output_data['suggestions'] = [item.model_dump() for item in parsed.suggestions]
            
            return json.dumps(output_data)
            
        except Exception as e:
            if verbose:
                print(f"⚠️ {response_format.__name__} parse failed: {e}")
            
            # Try fallback formats if provided
            if fallback_formats:
                for fallback_format, fallback_key in fallback_formats:
                    try:
                        final_comp = client.chat.completions.parse(
                            model=llm,
                            messages=[
                                {"role": "system", "content": f"Convert the output to match the schema format with a '{fallback_key}' key."},
                                {"role": "user", "content": final_text},
                            ],
                            response_format=fallback_format,
                        )
                        parsed = final_comp.choices[0].message.parsed
                        
                        output_data = {
                            fallback_key: [item.model_dump() for item in getattr(parsed, fallback_key)]
                        }
                        
                        # Add empty suggestions for CRO fallback case
                        if fallback_key == 'portfolio' and response_format.__name__ == 'PortfolioWithSuggestions':
                            output_data['suggestions'] = []
                        
                        return json.dumps(output_data)
                        
                    except Exception as e2:
                        if verbose:
                            print(f"⚠️ {fallback_format.__name__} fallback failed: {e2}")
                        continue
            
            # If all parsing fails, return original
            if verbose:
                print(f"⚠️ All parsing failed, keeping original")
            return final_text