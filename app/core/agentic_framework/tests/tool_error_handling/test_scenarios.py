"""
Simple test scenario generator for tool error testing.

Provides basic error scenarios for testing any tool with an agent.
"""

from typing import List


def get_basic_test_scenarios() -> List[str]:
    """
    Get the three basic test scenarios for any tool.

    Returns:
        List of 3 basic test scenario descriptions:
        1. Pass wrong type for first parameter
        2. Omit required parameter
        3. Call correctly with valid parameters

    Example:
        scenarios = get_basic_test_scenarios()
        # Returns: ["Pass wrong type for first parameter", ...]
    """
    return [
        "Pass wrong type for first parameter",
        "Omit required parameter",
        "Call correctly with valid parameters",
    ]
