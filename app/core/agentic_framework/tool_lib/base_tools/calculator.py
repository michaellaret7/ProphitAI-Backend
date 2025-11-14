import yaml
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
            return yaml.dump({
                'success': True,
                'data': {
                    'result': result,
                    'input': expression
                }
            }, default_flow_style=False)
        except Exception as e:
            return yaml.dump({
                'success': False,
                'error': str(e),
                'data': {}
            }, default_flow_style=False)
    # No expression provided
    return yaml.dump({
        'success': False,
        'error': "No expression provided.",
        'data': {}
    }, default_flow_style=False)


