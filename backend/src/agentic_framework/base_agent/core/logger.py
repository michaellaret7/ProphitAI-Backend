"""Message logging functionality for BaseAgent."""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path


class MessageLogger:
    """Manages message logging and saving for agent conversations."""
    
    def __init__(self, save_messages: bool = True, verbose: bool = True, model_name: str = None):
        self.save_messages = save_messages
        self.verbose = verbose
        self.model_name = model_name
        
        if self.save_messages:
            # Updated path since this file is now in core/ subfolder
            self.messages_log_path = Path(__file__).parent.parent.parent / "agent_output" / "agent_messages.json"
            self.live_messages_log_path = Path(__file__).parent.parent.parent / "agent_output" / "live_agent_messages.json"
            # Clear the messages file at start
            try:
                with open(self.messages_log_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            except Exception:
                pass
            # Clear the live messages file at start
            try:
                with open(self.live_messages_log_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            except Exception:
                pass
    
    def save_messages_to_json(self, messages: List[Dict[str, Any]], iteration: int, total_tokens: int = None) -> None:
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
            if total_tokens is not None:
                data["live_total_tokens"] = int(total_tokens)

            with open(self.messages_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save messages: {e}")

    def save_live_messages_to_json(self, messages: List[Dict[str, Any]], iteration: int, total_tokens: int = None) -> None:
        """Save the actual input messages used for the next model call to live_agent_messages.json."""
        if not self.save_messages:
            return
        try:
            serializable_messages = []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                serializable_msg = {"role": msg.get("role"), "content": msg.get("content", "")}
                if "tool_calls" in msg and msg["tool_calls"]:
                    try:
                        serializable_msg["tool_calls"] = [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": getattr(tc.function, "name", None),
                                    "arguments": getattr(tc.function, "arguments", None),
                                },
                            }
                            for tc in msg["tool_calls"]
                        ]
                    except Exception:
                        serializable_msg["tool_calls"] = []
                if "tool_call_id" in msg:
                    serializable_msg["tool_call_id"] = msg.get("tool_call_id")
                serializable_messages.append(serializable_msg)

            data = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "messages": serializable_messages,
                "message_count": len(serializable_messages)
            }
            if total_tokens is not None:
                data["live_total_tokens"] = int(total_tokens)

            with open(self.live_messages_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save live messages: {e}")
    
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
                    "total_tokens": result["total_tokens"]
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
