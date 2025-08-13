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
            self.messages_log_path = Path(__file__).parent.parent / "agent_output" / "agent_messages.json"
            # Clear the messages file at start
            try:
                with open(self.messages_log_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            except Exception:
                pass
    
    def save_messages_to_json(self, messages: List[Dict[str, Any]], iteration: int) -> None:
        """Save messages to JSON file during execution."""
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
            
            data = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "messages": serializable_messages,
                "message_count": len(serializable_messages)
            }
            
            with open(self.messages_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save messages: {e}")
    
    def save_final_json(self, messages: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
        """Save final messages and results to JSON file."""
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
            
            final_data = {
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "final_result": {
                    "final_text": result["final_text"],
                    "iterations": result["iterations"],
                    "stopped_reason": result["stopped_reason"],
                    "total_tokens": result["total_tokens"]
                },
                "messages": serializable_messages,
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
