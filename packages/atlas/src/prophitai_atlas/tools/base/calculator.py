"""Calculator tool for mathematical expressions."""

import math

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response


# ================================
# --> Helper funcs
# ================================

def _safe_eval(expr: str) -> float:
    """Safely evaluate a mathematical expression."""
    expr = expr.replace(' ', '')

    allowed_chars = '0123456789+-*/().eE'
    if not all(c in allowed_chars for c in expr):
        expr = expr.replace('sqrt', 'math.sqrt')
        expr = expr.replace('sin', 'math.sin')
        expr = expr.replace('cos', 'math.cos')
        expr = expr.replace('tan', 'math.tan')
        expr = expr.replace('log', 'math.log10')
        expr = expr.replace('ln', 'math.log')
        expr = expr.replace('pi', 'math.pi')
        expr = expr.replace('e', 'math.e')

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


# ================================
# --> Tools
# ================================

@agent_tool(name="calculator")
def calculator(expression: str) -> str:
    """LAST RESORT TOOL - ONLY use when absolutely necessary for complex mathematical calculations
that cannot be done with other tools. Most metrics are already calculated in factor tools.
Provide the expression string and the tool returns the result.
Supports basic arithmetic (+, -, *, /), parentheses, and math functions (sqrt, sin, cos, tan, log, ln, pi, e).

    Args:
        expression: Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)').
    """
    if expression:
        try:
            result = _safe_eval(expression)
            return success_response({
                'result': result,
                'input': expression
            })
        except Exception as e:
            return error_response(str(e))

    return error_response("No expression provided.")
