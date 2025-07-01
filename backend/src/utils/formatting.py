"""
Utilities for formatting data into human-readable or LLM-friendly formats.
"""

import re

def strip_formatting(text):
    """Strip asterisks and hashtags from the output text."""
    if not text:
        return text
    # Remove asterisks
    text = text.replace('*', '')
    # Remove hashtags
    text = text.replace('#', '')
    return text

def round_floats_in_object(obj, num_decimal_places=3):
    """
    Recursively iterates through a nested object (dict, list, or other)
    and rounds all float values to a specified number of decimal places.
    """
    if isinstance(obj, float):
        return round(obj, num_decimal_places)
    elif isinstance(obj, dict):
        return {key: round_floats_in_object(value, num_decimal_places) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [round_floats_in_object(item, num_decimal_places) for item in obj]
    else:
        return obj

def repair_json(json_string):
    """
    Attempt to repair common JSON formatting issues, like unquoted strings.
    """
    # This regex is a bit simplified. It might not cover all edge cases,
    # but it's designed to fix the specific issue of unquoted values like `24 vs. sector 4.6`
    
    def quote_unquoted(match):
        key = match.group(1)
        value = match.group(2).strip()
        
        # If the value is already a valid JSON value (number, bool, null, or quoted string), leave it.
        if re.match(r'^-?\d+(\.\d+)?$', value) or value in ['true', 'false', 'null'] or (value.startswith('"') and value.endswith('"')):
            return match.group(0)
            
        # Otherwise, quote it.
        value = value.replace('"', '\\"') # Escape internal quotes
        return f'"{key}": "{value}"'

    # This regex looks for a key, a colon, and a value that is not properly quoted.
    # It's specifically looking for values that don't start with a quote, a number, t, f, or n.
    json_string = re.sub(r'"([^"]+)"\s*:\s*([^"tf\d-][^,}]+)', quote_unquoted, json_string)
    
    return json_string
