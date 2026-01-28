"""Tool Trace Logger - Logs tool validation output to tools.yaml."""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.utils.time_utils import get_current_utc_time


def log_tool_call(
    tool_call_history: List[Dict[str, Any]],
    output_dir: Optional[str] = None
) -> None:
    """Write entire tool call history to tools.yaml.

    Args:
        tool_call_history: List of tool validation dictionaries
        output_dir: Directory to write the file to. If None, logging is skipped.
    """
    if output_dir is None:
        return

    tool_trace_file = Path(output_dir) / "tools.yaml"

    timestamped_history = []
    for entry in tool_call_history:
        timestamped_entry = entry.copy()
        if "timestamp" not in timestamped_entry:
            timestamped_entry["timestamp"] = get_current_utc_time().isoformat()
        timestamped_history.append(timestamped_entry)

    with open(tool_trace_file, 'w') as f:
        for i, entry in enumerate(timestamped_history, 1):
            f.write(f"# {'='*70}\n")
            f.write(f"# Tool Call #{i}\n")
            f.write(f"# {'='*70}\n")

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
