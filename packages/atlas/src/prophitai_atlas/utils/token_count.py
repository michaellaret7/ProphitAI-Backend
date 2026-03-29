import json
import tiktoken

def get_token_count(data):
    """Get token count for the data using tiktoken"""
    data_string = json.dumps(data, default=str)
    encoding = tiktoken.encoding_for_model("gpt-4o")
    token_count = len(encoding.encode(data_string))
    return token_count

def get_chat_token_count(messages, model="gpt-4o"):
    """Get accurate token count for chat messages following OpenAI's format."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_per_message = 3
    tokens_per_name = 1

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if value is None:
                continue
            if key == "role":
                num_tokens += len(encoding.encode(value))
            elif key == "content":
                num_tokens += len(encoding.encode(str(value)))
            elif key == "tool_calls":
                num_tokens += len(encoding.encode(json.dumps(value, default=str)))
            elif key == "tool_call_id":
                num_tokens += len(encoding.encode(value))
            elif key == "name":
                num_tokens += len(encoding.encode(value))
                num_tokens += tokens_per_name

    num_tokens += 3
    return num_tokens
