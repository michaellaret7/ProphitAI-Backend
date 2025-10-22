"""Agent utility functions for BaseAgent."""

import json
import re
import yaml
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from .parser import parse_tool_result


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

    def execute_tool_safe(self, name: str, args: Dict[str, Any], is_retry: bool = False):
        """Safely execute a tool with error handling.

        Returns tool results in standardized YAML dict format matching all tools:
        - Success: {"success": True, "data": ...}
        - Error: {"success": False, "error": "..."}

        Args:
            name: Tool name to execute
            args: Arguments to pass to the tool
            is_retry: Whether this is a retry attempt

        Returns:
            YAML string in dict format with success/error fields
        """
        if not name:
            return yaml.dump({
                "success": False,
                "error": "Tool name is None or empty",
                "available_tools": list(self.agent.tool_functions.keys())
            }, default_flow_style=False)

        name = self._strip_functions_prefix(name)
        func = self.agent.tool_functions.get(name)
        if not func:
            # Try to find the tool with case-insensitive matching as fallback
            for tool_name, tool_func in self.agent.tool_functions.items():
                if tool_name and name and tool_name.lower() == name.lower():
                    func = tool_func
                    break
            if not func:
                return yaml.dump({
                    "success": False,
                    "error": f"Tool '{name}' not found",
                    "available_tools": list(self.agent.tool_functions.keys())
                }, default_flow_style=False)

        try:
            # Auto-inject _simulation_date for simulation agents
            if self.agent.simulation_date is not None and isinstance(args, dict):
                args['_simulation_date'] = self.agent.simulation_date

            result = func(**args) if isinstance(args, dict) else func(args)
            return result

        except TypeError as e:
            error_msg = str(e)

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

            # Return standardized error format
            return yaml.dump({
                "success": False,
                "error": f"Invalid arguments for '{name}': {error_msg}",
                "args_provided": {k: str(v)[:100] for k, v in args.items()} if args else {}
            }, default_flow_style=False)

        except Exception as e:
            error_msg = str(e)
            return yaml.dump({
                "success": False,
                "error": f"Tool execution failed: {error_msg}"
            }, default_flow_style=False)

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
        """Update stagnation detection for repeated actions.

        NOTE: This method now delegates to StagnationTracker (Phase 3 refactor).
        """
        name = self._strip_functions_prefix(name)
        # Filter out _simulation_date for stagnation key (not JSON serializable)
        stag_args = {k: v for k, v in args.items() if k != '_simulation_date'}
        # Delegate to StagnationTracker (Phase 3 refactor)
        self.agent.stagnation_tracker.update(name, stag_args)
    
    def trace_to_dict(self, s: StepTrace) -> Dict[str, Any]:
        """Convert StepTrace to dictionary."""
        return {
            "iteration": s.iteration,
            "assistant_raw": s.assistant_raw,
            "tool_call": s.tool_call,
            "observation": s.observation,
            "analysis": s.analysis,
        }
    
    def parse_agent_dict_output(
        self,
        final_text: str,
        response_format,
        verbose: bool = True
    ) -> str:
        """
        Parse agent output for dict-based models without using OpenAI structured outputs.
        Used for models with Dict[str, ...] fields that don't work with OpenAI's schema validation.

        Args:
            final_text: Raw output text from agent
            response_format: Pydantic model for validation
            verbose: Whether to print debug messages

        Returns:
            JSON string of parsed data
        """
        # Strip "Final Answer:" prefix if present
        final_text = final_text.strip()
        if final_text.startswith("Final Answer:"):
            final_text = final_text[len("Final Answer:"):].strip()

        # Try to parse as JSON directly (agent outputs valid JSON)
        try:
            parsed_json = json.loads(final_text)

            # Validate with Pydantic model
            try:
                validated = response_format.model_validate(parsed_json)
                if verbose:
                    print(f"✅ {response_format.__name__} validated successfully")
                return json.dumps(validated.model_dump())
            except Exception as validation_error:
                if verbose:
                    print(f"⚠️ Pydantic validation warning: {validation_error}")
                # Return original if validation fails but JSON is valid
                return json.dumps(parsed_json)

        except json.JSONDecodeError as e:
            if verbose:
                print(f"⚠️ JSON decode failed: {e}")
                print("⚠️ Returning original text")
            return final_text

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
        Supports both list-based (CIO, CRO, Industry) and dict-based (Optimizer) outputs.

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
                    {"role": "system", "content": "Convert the output to match the schema format."},
                    {"role": "user", "content": final_text},
                ],
                response_format=response_format,
            )
            parsed = final_comp.choices[0].message.parsed

            # Get the primary output attribute
            primary_output = getattr(parsed, output_key)

            # Handle both list-based and dict-based outputs
            if isinstance(primary_output, list):
                # List-based output (CIO, CRO, Industry agents)
                output_data = {
                    output_key: [item.model_dump() for item in primary_output]
                }
            elif isinstance(primary_output, dict):
                # Dict-based output (Optimizer agent)
                output_data = {
                    output_key: {k: v.model_dump() for k, v in primary_output.items()}
                }
            else:
                # Fallback: use parsed model dump
                output_data = parsed.model_dump()

            # Handle additional keys (e.g., CRO 'suggestions', Optimizer 'changes')
            for attr_name in ['suggestions', 'changes']:
                if hasattr(parsed, attr_name):
                    attr_value = getattr(parsed, attr_name)
                    if isinstance(attr_value, list):
                        output_data[attr_name] = [item.model_dump() for item in attr_value]
                    elif hasattr(attr_value, 'model_dump'):
                        output_data[attr_name] = attr_value.model_dump()
                    else:
                        output_data[attr_name] = attr_value

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
                                {"role": "system", "content": "Convert the output to match the schema format."},
                                {"role": "user", "content": final_text},
                            ],
                            response_format=fallback_format,
                        )
                        parsed = final_comp.choices[0].message.parsed

                        # Handle list vs dict for fallback too
                        fallback_output = getattr(parsed, fallback_key)
                        if isinstance(fallback_output, list):
                            output_data = {
                                fallback_key: [item.model_dump() for item in fallback_output]
                            }
                        elif isinstance(fallback_output, dict):
                            output_data = {
                                fallback_key: {k: v.model_dump() for k, v in fallback_output.items()}
                            }
                        else:
                            output_data = parsed.model_dump()

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