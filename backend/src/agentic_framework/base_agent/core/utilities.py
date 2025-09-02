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
            "You are a JSON ReAct agent. You MUST use one of these two formats:\n"
            "1. Native tool-calls (preferred if supported)\n"
            "2. JSON format: {\"thought\":\"...\",\"action\":{\"tool\":\"name\",\"args\":{}}}\n\n"
            "3. The list can be as long as you want, the priority is to complete the task at hand as accurately and analytically as possible.\n"
            "CRITICAL RULES:\n"
            "- NEVER output plain text like 'Thought: ...' or 'Action: ...'\n"
            "- ALWAYS use complete JSON objects when not using native tool calls\n"
            "- Use exact tool names WITHOUT 'functions.' prefix (e.g., 'get_ticker_data' not 'functions.get_ticker_data')\n"
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
            
            # Record error and check for solutions if error memory is enabled
            if self.agent.error_memory and not is_retry:  # Only attempt auto-retry on first failure
                error_key = self.agent.error_memory.record_error(name, args, error_msg)
                solution = self.agent.error_memory.get_solution(name, error_msg)
                
                if solution and solution.get('confidence', 0) >= 0.7:
                    # High confidence solution found, attempt auto-retry
                    if self.agent.verbose:
                        print(f"🔄 Auto-retrying {name} with corrected arguments from memory (confidence: {solution['confidence']:.2f})")
                    
                    # Attempt retry with solution's example args or merge with original
                    expected_params = []
                    try:
                        import inspect
                        sig = inspect.signature(func)
                        for pname, p in sig.parameters.items():
                            if pname != 'self' and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                                expected_params.append(pname)
                    except Exception:
                        pass
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
                    if not isinstance(retry_result, str) or not retry_result.startswith("Error"):
                        if self.agent.verbose:
                            print(f"✅ Auto-retry successful for {name}!")
                        # Record the successful solution
                        self.agent.error_memory.record_solution(
                            error_key,
                            retry_args,
                            "Auto-retry with memory solution succeeded"
                        )
                        self.agent.last_tool_error = None  # Clear error
                        return retry_result
                    else:
                        # Retry also failed, return original error with guidance
                        if self.agent.verbose:
                            print(f"⚠️ Auto-retry failed for {name}, returning guidance")
                        return (
                            f"{error_response}\n\n"
                            f"💡 AUTO-RETRY ATTEMPTED BUT FAILED:\n"
                            f"{solution['guidance']}\n\n"
                            f"Manual correction may be needed."
                        )
                else:
                    # No high-confidence solution, store error for future learning
                    self.agent.last_tool_error = {
                        'tool_name': name,
                        'error_key': error_key if self.agent.error_memory else None,
                        'error_message': error_msg,
                        'failed_args': args
                    }
                    
                    # If solution exists but low confidence, provide guidance
                    if solution:
                        return (
                            f"{error_response}\n\n"
                            f"💡 SOLUTION FOUND (low confidence: {solution.get('confidence', 0):.2f}):\n"
                            f"{solution['guidance']}\n\n"
                            f"Please verify and retry."
                        )
            
            return error_response
            
        except Exception as e:
            error_msg = str(e)
            error_response = f"Unhandled error in tool '{name}': {error_msg}"
            
            # Record error and check for solutions if error memory is enabled
            if self.agent.error_memory and not is_retry:  # Only attempt auto-retry on first failure
                error_key = self.agent.error_memory.record_error(name, args, error_msg)
                solution = self.agent.error_memory.get_solution(name, error_msg)
                
                if solution and solution.get('confidence', 0) >= 0.7:
                    # High confidence solution found, attempt auto-retry
                    if self.agent.verbose:
                        print(f"🔄 Auto-retrying {name} after general error (confidence: {solution['confidence']:.2f})")
                    
                    # Attempt retry with solution's example args or merge with original
                    expected_params = []
                    try:
                        import inspect
                        sig = inspect.signature(func)
                        for pname, p in sig.parameters.items():
                            if pname != 'self' and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                                expected_params.append(pname)
                    except Exception:
                        pass
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
                    if not isinstance(retry_result, str) or (not retry_result.startswith("Error") and not retry_result.startswith("Unhandled")):
                        if self.agent.verbose:
                            print(f"✅ Auto-retry successful for {name}!")
                        # Record the successful solution
                        self.agent.error_memory.record_solution(
                            error_key,
                            retry_args,
                            "Auto-retry with memory solution succeeded"
                        )
                        self.agent.last_tool_error = None  # Clear error
                        return retry_result
                    else:
                        # Retry also failed
                        if self.agent.verbose:
                            print(f"⚠️ Auto-retry failed for {name}")
                else:
                    # No high-confidence solution, store error for future learning
                    self.agent.last_tool_error = {
                        'tool_name': name,
                        'error_key': error_key if self.agent.error_memory else None,
                        'error_message': error_msg,
                        'failed_args': args
                    }
            
            return error_response
    
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
            # Check if there's a get_initial_portfolio_dict result in recent observations
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
        """Convert observation to string format."""
        try:
            if isinstance(observation, (dict, list)):
                return json.dumps(observation, ensure_ascii=False)
            return str(observation)
        except Exception:
            return "<unserializable observation>"
    
    def update_stagnation(self, name: str, args: Dict[str, Any]):
        """Update stagnation detection for repeated actions."""
        name = self._strip_functions_prefix(name)
        key = f"{name}:{json.dumps(args, sort_keys=True)}"
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
