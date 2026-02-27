import json
import tiktoken

def get_token_count(data):
    """Get token count for the data using tiktoken"""
    # Convert to JSON string
    data_string = json.dumps(data, default=str)
    
    # Count tokens using tiktoken (GPT-4 encoding)
    encoding = tiktoken.encoding_for_model("gpt-4o")
    token_count = len(encoding.encode(data_string))
    
    return token_count

def get_chat_token_count(messages, model="gpt-4o"):
    """
    Get accurate token count for chat messages following OpenAI's format.
    
    Based on OpenAI's token counting documentation for chat models:
    - Every message has a base cost of 3 tokens
    - Additional tokens for role and content
    - Additional formatting overhead
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding for newer models
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens_per_message = 3  # Every message follows <|im_start|>{role/name}\n{content}<|im_end|>\n
    tokens_per_name = 1  # If there's a name field
    
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        
        # Count tokens for each field in the message
        for key, value in message.items():
            if value is None:
                continue
                
            if key == "role":
                num_tokens += len(encoding.encode(value))
            elif key == "content":
                num_tokens += len(encoding.encode(str(value)))
            elif key == "tool_calls":
                # Tool calls are serialized as JSON
                num_tokens += len(encoding.encode(json.dumps(value, default=str)))
            elif key == "tool_call_id":
                num_tokens += len(encoding.encode(value))
            elif key == "name":
                num_tokens += len(encoding.encode(value))
                num_tokens += tokens_per_name
    
    num_tokens += 3  # Every reply is primed with <|im_start|>assistant<|im_sep|>
    return num_tokens