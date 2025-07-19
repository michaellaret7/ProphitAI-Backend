import json
import tiktoken

def get_token_count(data):
    """Get token count for the data using tiktoken"""
    # Convert to JSON string
    data_string = json.dumps(data, default=str)
    
    # Count tokens using tiktoken (GPT-4 encoding)
    encoding = tiktoken.encoding_for_model("gpt-4")
    token_count = len(encoding.encode(data_string))
    
    return token_count