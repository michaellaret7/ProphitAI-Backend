"""Message Logger - Logs conversation messages to messages.yaml file."""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional


def write_messages_to_yaml(
    messages: List[Dict[str, Any]],
    output_dir: Optional[str] = None,
    iteration_indices: Optional[Dict[int, int]] = None
) -> None:
    """Write message history to messages.yaml file.

    Args:
        messages: List of message dictionaries from the agent
        output_dir: Directory to write the file to. If None, logging is skipped.
        iteration_indices: Dict mapping iteration number to message index where it starts
    """
    if not messages or output_dir is None:
        return

    output_path = Path(output_dir) / "messages.yaml"

    serializable_messages = []
    for msg in messages:
        serializable_msg = {"role": msg.get("role")}

        if "content" in msg:
            serializable_msg["content"] = msg["content"]

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

        if "tool_call_id" in msg:
            serializable_msg["tool_call_id"] = msg["tool_call_id"]

        serializable_messages.append(serializable_msg)

    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, entry in enumerate(serializable_messages):
            if iteration_indices:
                for iter_num in sorted(iteration_indices.keys()):
                    if iteration_indices[iter_num] == idx:
                        f.write(f"\n# {'='*70}\n")
                        f.write(f"# Iteration {iter_num}\n")
                        f.write(f"# {'='*70}\n\n")
                        break

            f.write("- ")
            yaml_str = yaml.dump(entry, default_flow_style=False, sort_keys=False)
            lines = yaml_str.split('\n')
            f.write(lines[0] + '\n')
            for line in lines[1:]:
                if line:
                    f.write("  " + line + '\n')
                elif line == '' and lines.index(line) != len(lines) - 1:
                    f.write('\n')
            f.write('\n')
