import re
import json

def parse_json_from_output(output_string: str) -> dict:
    """
    Parse JSON data from within <output></output> tags.
    
    Args:
        output_string: String containing the output with <output> tags
        
    Returns:
        dict: Parsed JSON data or None if parsing fails
    """
    # Extract content between <output> and </output> tags
    pattern = r'<output>(.*?)</output>'
    match = re.search(pattern, output_string, re.DOTALL)
    
    if not match:
        raise ValueError("No <output> tags found in the output string")
    
    json_content = match.group(1).strip()
    
    try:
        # Parse the JSON content
        parsed_data = json.loads(json_content)
        return parsed_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")