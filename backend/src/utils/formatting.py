"""
Utilities for formatting data into human-readable or LLM-friendly formats.
"""

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
