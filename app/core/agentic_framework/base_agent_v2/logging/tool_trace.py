"""Tool Trace Logger

Logs tool validation output to tools.yaml.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from app.utils.time_utils import get_current_utc_time


def log_tool_call(tool_call_history: List[Dict[str, Any]]) -> None:
    """Write entire tool call history to tools.yaml.

    Args:
        tool_call_history: List of tool validation dictionaries
    """
    # Get path to tools.yaml
    tool_trace_file = Path(__file__).parent.parent / "tools.yaml"

    # Add timestamp to each entry
    timestamped_history = []
    for entry in tool_call_history:
        # Create copy to avoid modifying original
        timestamped_entry = entry.copy()
        if "timestamp" not in timestamped_entry:
            timestamped_entry["timestamp"] = get_current_utc_time().isoformat()
        timestamped_history.append(timestamped_entry)

    # Overwrite file with entire history, adding dividers between entries
    with open(tool_trace_file, 'w') as f:
        for i, entry in enumerate(timestamped_history, 1):
            # Add tool call header with divider
            f.write(f"# {'='*70}\n")
            f.write(f"# Tool Call #{i}\n")
            f.write(f"# {'='*70}\n")

            # Write the entry as YAML list item
            f.write("- ")
            yaml_str = yaml.dump(entry, default_flow_style=False, sort_keys=False)
            # Indent all lines after the first to align with list marker
            lines = yaml_str.split('\n')
            f.write(lines[0] + '\n')
            for line in lines[1:]:
                if line:  # Skip empty lines
                    f.write("  " + line + '\n')
                elif line == '' and lines.index(line) != len(lines) - 1:
                    f.write('\n')
            f.write('\n')
