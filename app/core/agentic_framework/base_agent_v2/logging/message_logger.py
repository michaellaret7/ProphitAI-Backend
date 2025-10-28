"""Message Logger - Logs conversation messages to messages.json file."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def write_messages_to_json(messages: List[Dict[str, Any]], output_dir: Optional[str] = None) -> None:
    """Write message history to messages.json file.

    Args:
        messages: List of message dictionaries from the agent
        output_dir: Directory to write the file to (defaults to base_agent_v2 directory)
    """
    if not messages:
        return

    # Default to base_agent_v2 directory (same location as task_state.yaml)
    if output_dir is None:
        base_agent_v2_dir = Path(__file__).parent.parent
        output_path = base_agent_v2_dir / "messages.json"
    else:
        output_path = Path(output_dir) / "messages.json"

    # Convert messages to JSON-serializable format
    serializable_messages = []
    for msg in messages:
        serializable_msg = {"role": msg.get("role")}

        # Add content if present
        if "content" in msg:
            serializable_msg["content"] = msg["content"]

        # Add tool_calls if present (convert to dict format)
        if "tool_calls" in msg and msg["tool_calls"]:
            tool_calls_list = []
            for tc in msg["tool_calls"]:
                tool_call_dict = {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    },
                    "type": tc.type
                }
                tool_calls_list.append(tool_call_dict)
            serializable_msg["tool_calls"] = tool_calls_list

        # Add tool_call_id if present (for tool response messages)
        if "tool_call_id" in msg:
            serializable_msg["tool_call_id"] = msg["tool_call_id"]

        serializable_messages.append(serializable_msg)

    # Write to file with pretty formatting
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_messages, f, indent=2, ensure_ascii=False)
