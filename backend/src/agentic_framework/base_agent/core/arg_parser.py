import json
import re
import inspect
from typing import Any, Dict, Optional, List, get_type_hints
from datetime import datetime

class ToolArgumentParser:
    """Robust argument parser for LLM tool calls with validation and error recovery."""
    
    def __init__(self, tool_registry: Dict[str, Dict], verbose: bool = False):
        """
        Args:
            tool_registry: Maps tool names to their definitions including parameters schema
            verbose: Whether to log parameter transformations for debugging
        """
        self.tool_registry = tool_registry
        self._verbose = verbose
        self._type_converters = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': self._parse_bool,
            'array': list,
            'object': dict
        }
    
    def parse_arguments(self, tool_name: str, args_json: str, tool_function: Optional[callable] = None) -> Dict[str, Any]:
        """
        Parse and validate tool arguments with multiple fallback strategies.
        
        Returns:
            Dict of validated arguments ready for function call
        """
        # Strategy 1: Try standard JSON parsing
        args = self._try_json_parse(args_json)
        
        # Strategy 2: If failed, try to repair common JSON issues
        if args is None:
            args = self._repair_and_parse_json(args_json)
        
        # Strategy 3: If still failed, try key-value extraction
        if args is None:
            args = self._extract_key_values(args_json)
        
        # Strategy 4: Last resort - wrap as single parameter
        if args is None:
            args = self._wrap_as_single_param(tool_name, args_json)
        
        # Strategy 5: Handle GPT-5 parameter flattening (after successful parsing)
        if args is not None:
            args = self._handle_gpt5_flattening(tool_name, args)
        
        # Validate and coerce types based on schema
        if tool_name in self.tool_registry:
            args = self._validate_and_coerce(tool_name, args)
        
        # Fill in missing required parameters with defaults if possible
        args = self._fill_defaults(tool_name, args)
        
        # Final validation against function signature if provided
        if tool_function:
            args = self._validate_against_function(tool_function, args)
        
        return args
    
    def _try_json_parse(self, args_json: str) -> Optional[Dict]:
        """Standard JSON parsing with recursive parsing of nested JSON strings."""
        try:
            result = json.loads(args_json)
            if not isinstance(result, dict):
                return {'value': result}
            
            # Recursively parse any string values that look like JSON
            return self._parse_nested_json(result)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def _parse_nested_json(self, obj):
        """Recursively parse JSON strings within a dict/list structure."""
        if isinstance(obj, dict):
            parsed = {}
            for key, value in obj.items():
                if isinstance(value, str) and value.strip() and value.strip()[0] in '{[':
                    try:
                        # Try to parse as JSON
                        parsed[key] = self._parse_nested_json(json.loads(value))
                    except (json.JSONDecodeError, ValueError):
                        parsed[key] = value  # Keep as string if not valid JSON
                elif isinstance(value, (dict, list)):
                    parsed[key] = self._parse_nested_json(value)
                else:
                    parsed[key] = value
            return parsed
        elif isinstance(obj, list):
            return [self._parse_nested_json(item) for item in obj]
        else:
            return obj
    
    def _repair_and_parse_json(self, args_json: str) -> Optional[Dict]:
        """Repair common JSON formatting issues."""
        if not args_json:
            return {}
        
        repaired = args_json.strip()
        
        # Fix common issues
        repairs = [
            # Missing quotes around keys
            (r'(\w+):', r'"\1":'),
            # Single quotes to double quotes
            (r"'([^']*)'", r'"\1"'),
            # Trailing commas
            (r',\s*}', '}'),
            (r',\s*]', ']'),
            # Python True/False/None to JSON
            (r'\bTrue\b', 'true'),
            (r'\bFalse\b', 'false'),
            (r'\bNone\b', 'null'),
            # Remove comments
            (r'//.*$', '', re.MULTILINE),
            (r'/\*.*?\*/', '', re.DOTALL),
        ]
        
        for pattern, replacement, *flags in repairs:
            flag = flags[0] if flags else 0
            repaired = re.sub(pattern, replacement, repaired, flags=flag)
        
        # Ensure it's wrapped in braces if not already
        if not repaired.startswith('{'):
            repaired = '{' + repaired
        if not repaired.endswith('}'):
            repaired = repaired + '}'
        
        try:
            result = json.loads(repaired)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None
    
    def _extract_key_values(self, args_json: str) -> Optional[Dict]:
        """Extract key-value pairs from malformed JSON-like strings."""
        if not args_json:
            return {}
        
        result = {}
        
        # Pattern for key: value pairs
        patterns = [
            r'"(\w+)"\s*:\s*"([^"]*)"',  # "key": "value"
            r"'(\w+)'\s*:\s*'([^']*)'",  # 'key': 'value'
            r'(\w+)\s*:\s*"([^"]*)"',    # key: "value"
            r"(\w+)\s*:\s*'([^']*)'",    # key: 'value'
            r'(\w+)\s*:\s*([^,}\s]+)',   # key: value
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, args_json):
                key, value = match.groups()
                # Try to parse value as JSON literal
                try:
                    if value.lower() in ('true', 'false', 'null'):
                        value = json.loads(value.lower())
                    elif value.isdigit():
                        value = int(value)
                    elif re.match(r'^\d+\.\d+$', value):
                        value = float(value)
                except:
                    pass  # Keep as string
                result[key] = value
        
        return result if result else None
    
    def _wrap_as_single_param(self, tool_name: str, args_json: str) -> Dict:
        """Wrap raw string as single parameter based on tool schema."""
        if tool_name not in self.tool_registry:
            return {"input": args_json}
        
        schema = self.tool_registry[tool_name].get('parameters', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # If there's exactly one required parameter, use it
        if len(required) == 1:
            return {required[0]: args_json}
        
        # Find the first string parameter
        for param_name, param_schema in properties.items():
            if param_schema.get('type') == 'string':
                return {param_name: args_json}
        
        # Default fallback
        return {"input": args_json}
    
    def _handle_gpt5_flattening(self, tool_name: str, args: Dict) -> Dict:
        """
        Handle GPT-5 parameter flattening where single-parameter tools have their
        parameter structure flattened directly into the arguments.
        
        Example:
        GPT-4: {"portfolio_dict": {"AAPL": {"conviction": 0.1, "position": "long"}}}
        GPT-5: {"AAPL": {"conviction": 0.1, "position": "long"}}
        
        This method detects the GPT-5 pattern and wraps it properly.
        """
        if tool_name not in self.tool_registry or not isinstance(args, dict):
            return args
        
        schema = self.tool_registry[tool_name].get('parameters', {})
        required = schema.get('required', [])
        properties = schema.get('properties', {})
        
        # Only apply this fix for single required parameter tools
        if len(required) != 1:
            return args
        
        param_name = required[0]
        param_schema = properties.get(param_name, {})
        param_type = param_schema.get('type')
        
        # Only fix if the parameter is supposed to be an object but is currently flattened
        if param_type != 'object':
            return args
        
        # Check if the expected parameter is missing but we have data that looks like it should be wrapped
        if param_name not in args and len(args) > 0:
            # Log the transformation for debugging
            if self._verbose:
                print(f"🔧 GPT-5 parameter flattening detected for {tool_name}: wrapping arguments under '{param_name}'")
            
            # Wrap all current arguments under the expected parameter name
            return {param_name: args}
        
        return args
    
    def _validate_and_coerce(self, tool_name: str, args: Dict) -> Dict:
        """Validate and coerce types based on tool schema."""
        if tool_name not in self.tool_registry:
            return args
        
        schema = self.tool_registry[tool_name].get('parameters', {})
        properties = schema.get('properties', {})
        
        coerced = {}
        for key, value in args.items():
            if key in properties:
                expected_type = properties[key].get('type')
                if expected_type and expected_type in self._type_converters:
                    try:
                        converter = self._type_converters[expected_type]
                        coerced[key] = converter(value)
                    except (ValueError, TypeError):
                        coerced[key] = value  # Keep original if conversion fails
                else:
                    coerced[key] = value
            else:
                # Keep extra parameters that aren't in schema
                coerced[key] = value
        
        return coerced
    
    def _fill_defaults(self, tool_name: str, args: Dict) -> Dict:
        """Fill in missing required parameters with defaults."""
        if tool_name not in self.tool_registry:
            return args
        
        schema = self.tool_registry[tool_name].get('parameters', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        for param_name in required:
            if param_name not in args and param_name in properties:
                param_schema = properties[param_name]
                # Try to provide sensible defaults
                param_type = param_schema.get('type')
                if 'default' in param_schema:
                    args[param_name] = param_schema['default']
                elif 'enum' in param_schema:
                    args[param_name] = param_schema['enum'][0]
                elif param_type == 'string':
                    args[param_name] = ""
                elif param_type == 'integer':
                    args[param_name] = 0
                elif param_type == 'number':
                    args[param_name] = 0.0
                elif param_type == 'boolean':
                    args[param_name] = False
                elif param_type == 'array':
                    args[param_name] = []
                elif param_type == 'object':
                    args[param_name] = {}
        
        return args
    
    def _validate_against_function(self, func: callable, args: Dict) -> Dict:
        """Validate against actual function signature."""
        try:
            sig = inspect.signature(func)
            validated = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    # Accept all remaining kwargs
                    validated.update(args)
                elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                    # Skip *args
                    continue
                elif param_name in args:
                    validated[param_name] = args[param_name]
                elif param.default is not inspect.Parameter.empty:
                    # Has default, optional
                    pass
                else:
                    # Required parameter missing - try to find similar key
                    similar = self._find_similar_key(param_name, args.keys())
                    if similar:
                        validated[param_name] = args[similar]
            
            return validated
        except Exception:
            return args  # Return original if inspection fails
    
    def _find_similar_key(self, target: str, keys: List[str]) -> Optional[str]:
        """Find similar key using case-insensitive and underscore/hyphen matching."""
        target_lower = target.lower().replace('_', '').replace('-', '')
        for key in keys:
            if key.lower().replace('_', '').replace('-', '') == target_lower:
                return key
        return None
    
    def _parse_bool(self, value: Any) -> bool:
        """Parse boolean from various representations."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
