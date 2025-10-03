"""Message logging functionality for BaseAgent."""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

class MessageLogger:
    """Manages message logging and saving for agent conversations."""

    def __init__(self, save_messages: bool = True, verbose: bool = True, model_name: str = None, agent_name: str = None, output_dir: Path = None):
        self.save_messages = save_messages
        self.verbose = verbose
        self.model_name = model_name
        self.agent_name = agent_name or "BaseAgent"
        self.last_llm_received_tokens = None  # Track the last llm_received_tokens value

        if self.save_messages:
            if not output_dir:
                raise ValueError("output_dir is required when save_messages=True")

            self.messages_log_path = output_dir / "agent_messages.json"

            # Clear the messages file at start
            try:
                with open(self.messages_log_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            except Exception:
                pass
    
    def save_messages_to_json(self, messages: List[Dict[str, Any]], iteration: int, total_tokens: int = None, input_tokens: int = None) -> None:
        """Append new messages to agent_messages.json (full workflow log)."""
        if not self.save_messages:
            return
        
        try:
            # Create a serializable version of messages
            serializable_messages = []
            for msg in messages:
                serializable_msg = {"role": msg["role"], "content": msg.get("content", "")}
                
                # Handle tool calls if present
                if "tool_calls" in msg and msg["tool_calls"]:
                    serializable_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in msg["tool_calls"]
                    ]
                
                # Handle tool_call_id if present
                if "tool_call_id" in msg:
                    serializable_msg["tool_call_id"] = msg["tool_call_id"]
                
                serializable_messages.append(serializable_msg)
            
            # Load existing and compute delta by previous count
            existing_messages: List[Dict[str, Any]] = []
            prev_count = 0
            try:
                with open(self.messages_log_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    existing_messages = existing_data.get("messages") or []
                    if isinstance(existing_messages, list):
                        prev_count = existing_data.get("message_count") or len(existing_messages)
                    else:
                        existing_messages = []
                        prev_count = 0
            except Exception:
                existing_messages = []
                prev_count = 0

            start_idx = prev_count if isinstance(prev_count, int) and prev_count <= len(serializable_messages) else len(serializable_messages)
            to_append = serializable_messages[start_idx:]
            combined_messages = (existing_messages or []) + to_append

            data = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "messages": combined_messages,
                "message_count": len(combined_messages)
            }
            # Include the exact input tokens being sent to LLM
            if input_tokens is not None:
                data["llm_received_tokens"] = int(input_tokens)
                self.last_llm_received_tokens = int(input_tokens)  # Track the last value

            with open(self.messages_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save messages: {e}")

    def save_final_json(self, messages: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
        """Append final messages to the full workflow log and include final result summary."""
        if not self.save_messages:
            return
        
        try:
            # Create serializable messages
            serializable_messages = []
            for msg in messages:
                serializable_msg = {"role": msg["role"], "content": msg.get("content", "")}
                
                if "tool_calls" in msg and msg["tool_calls"]:
                    serializable_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in msg["tool_calls"]
                    ]
                
                if "tool_call_id" in msg:
                    serializable_msg["tool_call_id"] = msg["tool_call_id"]
                
                serializable_messages.append(serializable_msg)
            
            # Load existing to append delta
            existing_messages: List[Dict[str, Any]] = []
            prev_count = 0
            try:
                with open(self.messages_log_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    existing_messages = existing_data.get("messages") or []
                    if isinstance(existing_messages, list):
                        prev_count = existing_data.get("message_count") or len(existing_messages)
                    else:
                        existing_messages = []
                        prev_count = 0
            except Exception:
                existing_messages = []
                prev_count = 0

            start_idx = prev_count if isinstance(prev_count, int) and prev_count <= len(serializable_messages) else len(serializable_messages)
            to_append = serializable_messages[start_idx:]
            combined_messages = (existing_messages or []) + to_append

            final_data = {
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "final_result": {
                    "final_text": result["final_text"],
                    "iterations": result["iterations"],
                    "stopped_reason": result["stopped_reason"],
                    "total_tokens": self.last_llm_received_tokens if self.last_llm_received_tokens is not None else result.get("total_tokens", 0)
                },
                "messages": combined_messages,
                "message_count": len(combined_messages),
                "trace_summary": [
                    {
                        "iteration": t["iteration"],
                        "tool_call": t["tool_call"]["name"] if t["tool_call"] else None,
                        "has_observation": t["observation"] is not None
                    } for t in result["trace"]
                ]
            }
            
            # Save to the same messages file (not a separate final file)
            with open(self.messages_log_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            if self.verbose:
                print(f"\n✅ Final messages saved to: {self.messages_log_path}")
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save final messages: {e}")
