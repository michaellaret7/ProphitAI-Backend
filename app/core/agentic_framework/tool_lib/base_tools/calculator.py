import yaml
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
import math
from typing import Dict, Any

def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.

    Args:
        expression (str): Mathematical expression to evaluate (e.g., "2 + 3 * 4").

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether evaluation succeeded
            - 'data' (dict): Contains 'result' (float) and 'input' (str) when successful
            - 'error' (str): Error message when unsuccessful
    """
    
    def safe_eval(expr: str) -> float:
        """Safely evaluate a mathematical expression."""
        # Remove whitespace
        expr = expr.replace(' ', '')
        
        # Check for invalid characters
        allowed_chars = '0123456789+-*/().eE'
        if not all(c in allowed_chars for c in expr):
            # Check for special functions
            expr = expr.replace('sqrt', 'math.sqrt')
            expr = expr.replace('sin', 'math.sin')
            expr = expr.replace('cos', 'math.cos')
            expr = expr.replace('tan', 'math.tan')
            expr = expr.replace('log', 'math.log10')
            expr = expr.replace('ln', 'math.log')
            expr = expr.replace('pi', 'math.pi')
            expr = expr.replace('e', 'math.e')
        
        # Create a safe namespace with math functions
        safe_dict = {
            'math': math,
            '__builtins__': None,
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
        }
        
        try:
            result = eval(expr, safe_dict)
            return float(result)
        except Exception as e:
            raise ValueError(f"Invalid expression: {str(e)}")
    
    # Handle expression evaluation
    if expression:
        try:
            result = safe_eval(expression)
            return success_response({
                'result': result,
                'input': expression
            })
        except Exception as e:
            return error_response(str(e))
    # No expression provided
    return error_response("No expression provided.")


CALCULATOR_DESCRIPTION = (
    "LAST RESORT TOOL - ONLY use when absolutely necessary for complex mathematical calculations "
    "that cannot be done with other tools. Most metrics are already calculated in factor tools. "
    "Provide the expression string and the tool returns the result. "
    "Supports basic arithmetic (+, -, *, /), parentheses, and math functions (sqrt, sin, cos, tan, log, ln, pi, e)."
)

CALCULATOR_PARAMETERS = {
    "type": "object",
    "properties": {
        "expression": {
            "type": "string",
            "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)')."
        }
    },
    "required": ["expression"],
}

CALCULATOR_TOOL = {
    "name": "calculator",
    "description": CALCULATOR_DESCRIPTION,
    "parameters": CALCULATOR_PARAMETERS,
    "function": calculator,
}
