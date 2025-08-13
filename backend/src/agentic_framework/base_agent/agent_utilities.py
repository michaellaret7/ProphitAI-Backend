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
            "CRITICAL RULES:\n"
            "- NEVER output plain text like 'Thought: ...' or 'Action: ...'\n"
            "- ALWAYS use complete JSON objects when not using native tool calls\n"
            "- Use exact tool names WITHOUT 'functions.' prefix (e.g., 'get_ticker_data' not 'functions.get_ticker_data')\n"
            "- Do NOT invent wrapper tools like 'multi_tool_use.parallel'\n"
            "- When ready to finalize, output 'Final Answer:' followed by your answer\n\n"
            "CHECKLIST PROTOCOL:\n"
            "- When you complete a task from your checklist, explicitly state it\n"
            "- Use phrases like 'Step X complete' or 'Task X done' to indicate completion\n"
            "- Stay focused on your current task until it's complete before moving on\n"
            "- Provide evidence for task completion (e.g., 'Retrieved data for all tickers')\n\n"
            "IMPORTANT: If you find yourself outputting 'functions.' prefix, remove it immediately."
        )
    
    def accumulate_usage(self, response) -> None:
        """Accumulate token usage from response."""
        try:
            if hasattr(response, "usage") and response.usage and response.usage.total_tokens:
                self.agent.total_tokens += int(response.usage.total_tokens)
        except Exception:
            pass
    
    def execute_tool_safe(self, name: str, args: Dict[str, Any]):
        """Safely execute a tool with error handling."""
        name = self._strip_functions_prefix(name)
        func = self.agent.tool_functions.get(name)
        if not func:
            # Try to find the tool with case-insensitive matching as fallback
            for tool_name, tool_func in self.agent.tool_functions.items():
                if tool_name.lower() == name.lower():
                    func = tool_func
                    break
            if not func:
                return f"Error: tool '{name}' not found. Available tools: {list(self.agent.tool_functions.keys())}"
        try:
            return func(**args) if isinstance(args, dict) else func(args)
        except TypeError as e:
            return f"Error calling tool '{name}': {e} (args={args})"
        except Exception as e:
            return f"Unhandled error in tool '{name}': {e}"
    
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
