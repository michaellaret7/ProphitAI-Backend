import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import json
import time
from app.utils.choose_model_and_client import get_model_and_client

load_dotenv()

# os.environ['GEMINI_API_KEY'] = os.getenv("GEMINI_API_KEY")

# response = completion(
#     model="gemini/gemini-3-pro-preview", 
#     messages=[{"role": "user", "content": "Write a plan for a new product launch"}]
# )

# print(response)

def x(a,b):
    return a+b

# Tool schema for x function
x_tool = {
    "type": "function",
    "function": {
        "name": "x",
        "description": "Add two numbers together",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    }
}

def transform_gemini_to_openai(gemini_response):
    # 1. Extract the Candidate (the main answer data)
    # Gemini returns a list of candidates, usually we just want the first one.
    try:
        candidate = gemini_response.get("candidates", [])[0]
    except IndexError:
        return {"error": "No candidates returned"}

    # 2. Parse Content vs. Thoughts
    # Gemini 2.0/3.0 structures often separate "Thinking" from the "Response"
    parts = candidate.get("content", {}).get("parts", [])
    
    final_content = ""
    thought_process = ""

    for part in parts:
        # Check if this part is a "thought" (based on your JSON structure)
        if part.get("thought") is True:
            thought_process = part.get("text", "")
        else:
            # Append to final content (in case there are multiple text parts)
            final_content += part.get("text", "")

    # 3. Map Token Usage
    gemini_usage = gemini_response.get("usage_metadata", {})
    openai_usage = {
        "prompt_tokens": gemini_usage.get("prompt_token_count", 0),
        "completion_tokens": gemini_usage.get("candidates_token_count", 0),
        "total_tokens": gemini_usage.get("total_token_count", 0)
    }

    # 4. Construct the OpenAI Object
    openai_format = {
        "id": gemini_response.get("response_id", "chatcmpl-fallback"),
        "object": "chat.completion",
        "created": int(time.time()), # Gemini doesn't always give a unix timestamp, so we generate one
        "model": gemini_response.get("model_version", "gemini-unknown"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_content,
                    # Note: Standard OpenAI clients won't see this, but we can 
                    # hide the thought process in the 'refusal' or a custom field
                    # if you want to debug it later.
                    "refusal": None 
                },
                "finish_reason": candidate.get("finish_reason", "stop").lower(),
                # Some newer OpenAI implementations (like o1) use reasoning_content
                # You could uncomment the line below to support that:
                # "reasoning_content": thought_process 
            }
        ],
        "usage": openai_usage,
        "system_fingerprint": None
    }

    return openai_format


# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# # Gemini tool schema
# x_tool_gemini = types.Tool(
#     function_declarations=[
#         types.FunctionDeclaration(
#             name="x",
#             description="Add two numbers together",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "a": {"type": "number", "description": "First number"},
#                     "b": {"type": "number", "description": "Second number"}
#                 },
#                 "required": ["a", "b"]
#             }
#         )
#     ]
# )

# response = client.models.generate_content(
#     model="gemini-3-pro-preview",
#     contents="Write a plan for a new product launch, keep it short and concise",
#     config=types.GenerateContentConfig(
#         tools=[x_tool_gemini],
#         thinking_config=types.ThinkingConfig(
#             include_thoughts=True,  # Enable thinking mode
#             thinking_budget=1024    # Optional: control depth of reasoning
#         )
#     )
# )

# print("====GEMINI=====")
# print(response.model_dump_json(indent=2))


model, client = get_model_and_client('gemini', 'gemini-3-pro-preview')

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Write a plan for a new product launch, keep it short and concise"}],
    tools=[x_tool],
    tool_choice="auto"
)

print("====GEMINI=====")
resonse = response 

model, client = get_model_and_client('openai', 'gpt-4o')

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Write a plan for a new product launch, keep it short and concise"}],
    tools=[x_tool],
    tool_choice="auto"
)

# Access the response
print("====OPENAI=====")
print(response.model_dump_json(indent=2))

model, client = get_model_and_client('anthropic')

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Write a plan for a new product launch, keep it short and concise"}],
    tools=[x_tool],
    tool_choice="auto"
)

# Access the response
print("====CLAUDE=====")
print(response.model_dump_json(indent=2))
