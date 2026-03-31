"""Test harness for tools - run, time, and measure tool outputs.

Usage:
    python test_harness.py <tool_name> '<args_json>'
    python test_harness.py ticker_performance '{"ticker": "AAPL", "years_back": 1}'
    python test_harness.py --list
    python test_harness.py --schema ticker_performance
"""

import sys
import os
import json
import time
import traceback

from dotenv import load_dotenv
load_dotenv()

import tiktoken

from prophitai_tools.registry import ALL_TOOL_FUNCTIONS, CHAT_ONLY_TOOLS

# Reason: Build AVAILABLE_TOOLS dict from registry, excluding chat-only tools
AVAILABLE_TOOLS = {
    func.tool["name"]: func.tool
    for func in ALL_TOOL_FUNCTIONS
    if func.tool["name"] not in CHAT_ONLY_TOOLS
}


# ================================
# --> Helper funcs
# ================================

OUTPUT_TRUNCATE_CHARS = 8000


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding (GPT-4 / Claude approximation)."""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def truncate(text: str, limit: int = OUTPUT_TRUNCATE_CHARS) -> str:
    """Truncate text with indicator if it exceeds limit."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [TRUNCATED - {len(text)} total chars]"


def run_tool_test(tool_name: str, args: dict) -> dict:
    """Run a single tool with given args and return structured results.

    Args:
        tool_name: Registered tool name from AVAILABLE_TOOLS.
        args: Keyword arguments to pass to the tool function.

    Returns:
        Dict with: tool, args, status, elapsed_seconds, token_count,
        output_chars, error, output (truncated).
    """
    tool = AVAILABLE_TOOLS.get(tool_name)
    if not tool:
        return {
            "tool": tool_name,
            "args": args,
            "status": "UNKNOWN_TOOL",
            "error": f"Unknown tool '{tool_name}'.",
            "elapsed_seconds": 0,
            "token_count": 0,
            "output_chars": 0,
            "output": None,
        }

    func = tool["function"]

    start = time.perf_counter()
    try:
        output = func(**args)
        elapsed = time.perf_counter() - start
        status = "SUCCESS"
        error = None
    except Exception as e:
        elapsed = time.perf_counter() - start
        output = traceback.format_exc()
        status = "EXCEPTION"
        error = f"{type(e).__name__}: {e}"

    output_str = str(output)
    token_count = count_tokens(output_str)

    return {
        "tool": tool_name,
        "args": args,
        "status": status,
        "elapsed_seconds": round(elapsed, 3),
        "token_count": token_count,
        "output_chars": len(output_str),
        "error": error,
        "output": truncate(output_str),
    }


def list_tools() -> None:
    """Print all registered tools with short descriptions."""
    for name in sorted(AVAILABLE_TOOLS):
        desc = AVAILABLE_TOOLS[name].get("description", "")
        first_line = desc.split("\n")[0][:100]
        print(f"  {name}: {first_line}")


def show_schema(tool_name: str) -> None:
    """Print the JSON schema for a tool's parameters."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if not tool:
        print(f"Unknown tool: {tool_name}")
        sys.exit(1)

    schema_info = {
        "name": tool["name"],
        "description": tool.get("description", "")[:300],
        "parameters": tool.get("parameters", {}),
    }
    print(json.dumps(schema_info, indent=2))


def main() -> None:
    """Entry point - parse CLI args and dispatch."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_harness.py <tool_name> [args_json]")
        print("  python test_harness.py --list")
        print("  python test_harness.py --schema <tool_name>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "--list":
        list_tools()
        return

    if cmd == "--schema":
        if len(sys.argv) < 3:
            print("Usage: python test_harness.py --schema <tool_name>")
            sys.exit(1)
        show_schema(sys.argv[2])
        return

    # Normal mode: run a tool
    tool_name = cmd
    args_json = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        args = json.loads(args_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON args: {e}"}, indent=2))
        sys.exit(1)

    result = run_tool_test(tool_name, args)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
