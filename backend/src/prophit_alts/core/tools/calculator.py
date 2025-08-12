import math
import re
from typing import Union, Dict, Any


def calculator(expression: str = None, operation: str = None, **kwargs) -> Dict[str, Any]:
    """
    A comprehensive calculator tool for agents that can evaluate mathematical expressions
    or perform specific operations.
    
    Args:
        expression (str, optional): A mathematical expression to evaluate (e.g., "2 + 3 * 4")
        operation (str, optional): A specific operation to perform. Supported operations:
            - 'add', 'subtract', 'multiply', 'divide': Basic arithmetic
            - 'power', 'sqrt', 'log', 'ln': Advanced operations
            - 'sin', 'cos', 'tan': Trigonometric functions
            - 'factorial', 'abs', 'round': Other operations
        **kwargs: Additional arguments for specific operations:
            - a, b: Numbers for binary operations
            - n: Number for unary operations
            - decimals: Number of decimal places for rounding
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'success': Boolean indicating if operation was successful
            - 'result': The calculated result (if successful)
            - 'error': Error message (if unsuccessful)
            - 'operation': The operation performed
            - 'input': The input values used
    
    Examples:
        >>> calculator(expression="2 + 3 * 4")
        {'success': True, 'result': 14, 'operation': 'expression', 'input': '2 + 3 * 4'}
        
        >>> calculator(operation='add', a=5, b=3)
        {'success': True, 'result': 8, 'operation': 'add', 'input': {'a': 5, 'b': 3}}
        
        >>> calculator(operation='sqrt', n=16)
        {'success': True, 'result': 4.0, 'operation': 'sqrt', 'input': {'n': 16}}
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
            return {
                'success': True,
                'result': result,
                'operation': 'expression',
                'input': expression
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation': 'expression',
                'input': expression
            }
    
    # Handle specific operations
    if operation:
        try:
            # Basic arithmetic operations
            if operation == 'add':
                a, b = kwargs.get('a'), kwargs.get('b')
                if a is None or b is None:
                    raise ValueError("'add' requires parameters 'a' and 'b'")
                result = float(a) + float(b)
                
            elif operation == 'subtract':
                a, b = kwargs.get('a'), kwargs.get('b')
                if a is None or b is None:
                    raise ValueError("'subtract' requires parameters 'a' and 'b'")
                result = float(a) - float(b)
                
            elif operation == 'multiply':
                a, b = kwargs.get('a'), kwargs.get('b')
                if a is None or b is None:
                    raise ValueError("'multiply' requires parameters 'a' and 'b'")
                result = float(a) * float(b)
                
            elif operation == 'divide':
                a, b = kwargs.get('a'), kwargs.get('b')
                if a is None or b is None:
                    raise ValueError("'divide' requires parameters 'a' and 'b'")
                if float(b) == 0:
                    raise ValueError("Division by zero")
                result = float(a) / float(b)
                
            # Advanced operations
            elif operation == 'power':
                a, b = kwargs.get('a'), kwargs.get('b')
                if a is None or b is None:
                    raise ValueError("'power' requires parameters 'a' (base) and 'b' (exponent)")
                result = float(a) ** float(b)
                
            elif operation == 'sqrt':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'sqrt' requires parameter 'n'")
                if float(n) < 0:
                    raise ValueError("Cannot take square root of negative number")
                result = math.sqrt(float(n))
                
            elif operation == 'log':
                n = kwargs.get('n')
                base = kwargs.get('base', 10)
                if n is None:
                    raise ValueError("'log' requires parameter 'n'")
                if float(n) <= 0:
                    raise ValueError("Logarithm undefined for non-positive numbers")
                result = math.log(float(n), float(base))
                
            elif operation == 'ln':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'ln' requires parameter 'n'")
                if float(n) <= 0:
                    raise ValueError("Natural logarithm undefined for non-positive numbers")
                result = math.log(float(n))
                
            # Trigonometric functions (input in radians)
            elif operation == 'sin':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'sin' requires parameter 'n' (in radians)")
                result = math.sin(float(n))
                
            elif operation == 'cos':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'cos' requires parameter 'n' (in radians)")
                result = math.cos(float(n))
                
            elif operation == 'tan':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'tan' requires parameter 'n' (in radians)")
                result = math.tan(float(n))
                
            # Other operations
            elif operation == 'factorial':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'factorial' requires parameter 'n'")
                n_int = int(float(n))
                if n_int < 0:
                    raise ValueError("Factorial undefined for negative numbers")
                result = math.factorial(n_int)
                
            elif operation == 'abs':
                n = kwargs.get('n')
                if n is None:
                    raise ValueError("'abs' requires parameter 'n'")
                result = abs(float(n))
                
            elif operation == 'round':
                n = kwargs.get('n')
                decimals = kwargs.get('decimals', 0)
                if n is None:
                    raise ValueError("'round' requires parameter 'n'")
                result = round(float(n), int(decimals))
                
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            # Prepare input information for response
            input_info = {k: v for k, v in kwargs.items() if v is not None}
            
            return {
                'success': True,
                'result': result,
                'operation': operation,
                'input': input_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation': operation,
                'input': kwargs
            }
    
    # No operation specified
    return {
        'success': False,
        'error': "No expression or operation specified. Please provide either 'expression' or 'operation' parameter.",
        'operation': None,
        'input': None
    }


# Example usage and tests
if __name__ == "__main__":
    # Test expression evaluation
    print("Expression Tests:")
    print(calculator(expression="2 + 3 * 4"))
    print(calculator(expression="(10 - 5) * 2"))
    print(calculator(expression="sqrt(16) + 3"))
    
    print("\nBasic Operations:")
    print(calculator(operation='add', a=5, b=3))
    print(calculator(operation='divide', a=10, b=2))
    
    print("\nAdvanced Operations:")
    print(calculator(operation='sqrt', n=25))
    print(calculator(operation='power', a=2, b=3))
    print(calculator(operation='log', n=100))
    
    print("\nTrigonometric Functions:")
    print(calculator(operation='sin', n=math.pi/2))
    print(calculator(operation='cos', n=0))
    
    print("\nError Handling:")
    print(calculator(operation='divide', a=5, b=0))
    print(calculator(operation='sqrt', n=-4))
    print(calculator(expression="2 + + 3"))