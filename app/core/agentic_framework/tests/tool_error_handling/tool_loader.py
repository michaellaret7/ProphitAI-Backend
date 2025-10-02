"""
Tool loader for dynamically discovering and loading tools from tool_lib.

This module scans the tool_lib directory for *_TOOL exports and provides
functions to load tools by name for testing purposes.
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Add project root to sys.path to enable imports
# Current file: app/core/agentic_framework/tests/framework/tool_loader.py
# Project root: 5 levels up
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Cache for discovered tools to avoid repeated filesystem scans
_TOOL_CACHE: Optional[Dict[str, str]] = None

def discover_all_tools() -> Dict[str, str]:
    """
    Scan tool_lib directory and discover all *_TOOL exports.

    Returns:
        Dict mapping tool_name to file_path
        Example: {"calculate_portfolio_performance": "app/core/.../performance.py"}
    """
    global _TOOL_CACHE

    # Return cached results if available
    if _TOOL_CACHE is not None:
        return _TOOL_CACHE

    tools = {}

    # Get the tool_lib directory path
    # Current file: app/core/agentic_framework/tests/framework/tool_loader.py
    # Tool lib: app/core/agentic_framework/tool_lib/
    current_file = Path(__file__).resolve()
    agentic_framework_dir = current_file.parent.parent.parent
    tool_lib_path = agentic_framework_dir / "tool_lib"

    if not tool_lib_path.exists():
        print(f"Warning: tool_lib path not found: {tool_lib_path}")
        _TOOL_CACHE = tools
        return tools

    # Recursively search for Python files in tool_lib
    for py_file in tool_lib_path.rglob("*.py"):
        # Skip __init__.py files
        if py_file.name == "__init__.py":
            continue

        # Convert path to module name
        # Find app/ in the path and build module name from there
        parts = py_file.resolve().parts
        try:
            app_index = parts.index("app")
            module_parts = parts[app_index:-1] + (py_file.stem,)
            module_name = ".".join(module_parts)
        except ValueError:
            continue  # Skip if can't find app in path

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Look for *_TOOL exports
            for attr_name in dir(module):
                if attr_name.endswith("_TOOL") and not attr_name.startswith("_"):
                    tool_obj = getattr(module, attr_name)

                    # Verify it's a dict with expected structure
                    if isinstance(tool_obj, dict) and "name" in tool_obj:
                        tool_name = tool_obj["name"]
                        tools[tool_name] = str(py_file)

        except Exception as e:
            # Skip files that can't be imported (enable for debugging)
            if __name__ == "__main__":
                print(f"Debug: Failed to import {module_name}: {type(e).__name__}")
            pass

    # Cache the results
    _TOOL_CACHE = tools
    return tools


def load_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """
    Load a tool definition by its name.

    Args:
        tool_name: Name of the tool (e.g., "calculate_portfolio_performance")

    Returns:
        Dict containing tool definition with keys: name, description, parameters, function
        Ready to use with: agent.add_tool(**tool_def)

    Raises:
        ValueError: If tool not found

    Example:
        tool = load_tool_by_name("calculate_portfolio_performance")
        agent.add_tool(**tool)
    """
    # Discover all tools
    all_tools = discover_all_tools()

    # Check if tool exists
    if tool_name not in all_tools:
        available = ", ".join(sorted(all_tools.keys())[:10])
        raise ValueError(
            f"Tool '{tool_name}' not found. "
            f"Available tools (first 10): {available}..."
        )

    file_path = all_tools[tool_name]

    # Convert file path to module name
    file_path_obj = Path(file_path)

    # Find the project root (where app/ starts)
    parts = file_path_obj.parts
    try:
        app_index = parts.index("app")
        module_parts = parts[app_index:-1] + (file_path_obj.stem,)
        module_name = ".".join(module_parts)
    except ValueError:
        raise ValueError(f"Could not determine module name from path: {file_path}")

    # Import the module
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        raise ValueError(f"Failed to import module {module_name}: {e}")

    # Find the *_TOOL export matching this tool name
    for attr_name in dir(module):
        if attr_name.endswith("_TOOL") and not attr_name.startswith("_"):
            tool_obj = getattr(module, attr_name)

            if isinstance(tool_obj, dict) and tool_obj.get("name") == tool_name:
                return tool_obj

    raise ValueError(f"Tool definition not found in module {module_name}")


def get_tool_function(tool_name: str) -> Callable:
    """
    Get just the callable function for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Callable function

    Example:
        func = get_tool_function("calculate_portfolio_performance")
        result = func(portfolio_dict={"AAPL": {...}})
    """
    tool_def = load_tool_by_name(tool_name)
    return tool_def["function"]


if __name__ == "__main__":
    """Test the tool loader."""

    # Enable debug output for testing
    import sys
    current_file = Path(__file__).resolve()
    agentic_framework_dir = current_file.parent.parent.parent
    tool_lib_path = agentic_framework_dir / "tool_lib"
    print(f"Debug: Tool lib path: {tool_lib_path}")
    print(f"Debug: Path exists: {tool_lib_path.exists()}")
    if tool_lib_path.exists():
        py_files = list(tool_lib_path.rglob("*.py"))
        print(f"Debug: Found {len(py_files)} Python files")
        if py_files:
            print(f"Debug: First file: {py_files[0]}")

    print("\n" + "="*80)
    print("DISCOVERING ALL TOOLS")
    print("="*80)

    all_tools = discover_all_tools()
    print(f"\nFound {len(all_tools)} tools:")
    for i, (tool_name, file_path) in enumerate(sorted(all_tools.items())[:10], 1):
        print(f"{i}. {tool_name}")
        print(f"   → {file_path}")

    if len(all_tools) > 10:
        print(f"   ... and {len(all_tools) - 10} more")

    print("\n" + "="*80)
    print("TESTING TOOL LOAD")
    print("="*80)

    # Test loading a specific tool
    test_tool_name = "calculate_portfolio_performance"
    print(f"\nLoading tool: {test_tool_name}")

    try:
        tool_def = load_tool_by_name(test_tool_name)
        print(f"\n✓ Successfully loaded tool!")
        print(f"  Name: {tool_def['name']}")
        print(f"  Description: {tool_def['description'][:100]}...")
        print(f"  Parameters: {list(tool_def['parameters'].get('properties', {}).keys())}")
        print(f"  Function: {tool_def['function'].__name__}")
    except Exception as e:
        print(f"\n✗ Failed to load tool: {e}")

    print("\n" + "="*80)
    print("TESTING TOOL FUNCTION EXTRACTION")
    print("="*80)

    try:
        func = get_tool_function(test_tool_name)
        print(f"\n✓ Successfully extracted function: {func.__name__}")
    except Exception as e:
        print(f"\n✗ Failed to extract function: {e}")
