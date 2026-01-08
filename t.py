"""Quick script to test LLM tool usage with fake data across different providers"""
from dotenv import load_dotenv

load_dotenv()


# Define the tool that returns fake stock data
def get_stock_data(ticker: str) -> dict:
    """Returns fake stock data for a given ticker"""
    fake_data = {
        "AAPL": {"price": 185.50, "change": 2.3, "volume": 45000000},
        "MSFT": {"price": 378.25, "change": -1.2, "volume": 22000000},
        "GOOGL": {"price": 140.80, "change": 0.8, "volume": 18000000},
    }
    return fake_data.get(ticker.upper(), {"price": 100.00, "change": 0.0, "volume": 1000000})


def openai_client():
    """Test tool usage with OpenAI client"""
    from openai import OpenAI
    import os

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_stock_data",
                "description": "Get current stock price, change, and volume for a ticker symbol",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                        }
                    },
                    "required": ["ticker"]
                }
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a financial assistant. Use the available tools to get stock data."},
            {"role": "user", "content": "What's the current price of Apple stock?"}
        ],
        tools=tools,
        tool_choice="auto"
    )

    return response


def google_client():
    """Test tool usage with Google Gemini client"""
    from google import genai
    from google.genai import types

    get_stock_data_function = {
        "name": "get_stock_data",
        "description": "Get current stock price, change, and volume for a ticker symbol",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                }
            },
            "required": ["ticker"]
        }
    }

    client = genai.Client()
    tools = types.Tool(function_declarations=[get_stock_data_function])
    config = types.GenerateContentConfig(tools=[tools])

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="What's the current price of Apple stock?",
        config=config,
    )

    return response

def anthropic_client():
    """Test tool usage with Anthropic client"""
    import anthropic

    client = anthropic.Anthropic()

    tools = [
        {
            "name": "get_stock_data",
            "description": "Get current stock price, change, and volume for a ticker symbol. The ticker symbol must be a valid symbol for a publicly traded company.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    }
                },
                "required": ["ticker"]
            }
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        tools=tools,
        messages=[
            {"role": "user", "content": "What's the current price of Apple stock?"}
        ],
        thinking={
            "type": "enabled",
            "budget_tokens": 1024
        },
        tool_choice={"type": "auto"}
    )

    return response


from dataclasses import dataclass
from typing import Optional, Any
import json

@dataclass
class NormalizedToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class NormalizedUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass
class NormalizedResponse:
    model: str
    provider: str
    tool_calls: list[NormalizedToolCall]
    content: Optional[str]
    usage: NormalizedUsage
    raw_response: Any  # Keep original for debugging

def normalize_openai(response) -> NormalizedResponse:
    tool_calls = []
    if response.choices[0].message.tool_calls:
        for tc in response.choices[0].message.tool_calls:
            tool_calls.append(NormalizedToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments)
            ))
    
    return NormalizedResponse(
        model=response.model,
        provider="openai",
        tool_calls=tool_calls,
        content=response.choices[0].message.content,
        usage=NormalizedUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens
        ),
        raw_response=response
    )

def normalize_gemini(response) -> NormalizedResponse:
    tool_calls = []
    content = None
    
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'function_call') and part.function_call:
            tool_calls.append(NormalizedToolCall(
                id=f"gemini_{response.response_id}",  # Gemini doesn't have tool call IDs
                name=part.function_call.name,
                arguments=dict(part.function_call.args)
            ))
        elif hasattr(part, 'text'):
            content = part.text
    
    return NormalizedResponse(
        model=response.model_version,
        provider="gemini",
        tool_calls=tool_calls,
        content=content,
        usage=NormalizedUsage(
            input_tokens=response.usage_metadata.prompt_token_count,
            output_tokens=response.usage_metadata.candidates_token_count,
            total_tokens=response.usage_metadata.total_token_count
        ),
        raw_response=response
    )

def normalize_anthropic(response) -> NormalizedResponse:
    tool_calls = []
    content_parts = []
    
    for block in response.content:
        if block.type == "tool_use":
            tool_calls.append(NormalizedToolCall(
                id=block.id,
                name=block.name,
                arguments=block.input
            ))
        elif block.type == "text":
            content_parts.append(block.text)
    
    return NormalizedResponse(
        model=response.model,
        provider="anthropic",
        tool_calls=tool_calls,
        content="\n".join(content_parts) if content_parts else None,
        usage=NormalizedUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens
        ),
        raw_response=response
    )

if __name__ == "__main__":
    print("\n" + "="*50)
    print(normalize_openai(openai_client()))
    print("\n" + "="*50)
    print(normalize_gemini(google_client()))
    print("\n" + "="*50)
    print(normalize_anthropic(anthropic_client()))
    print("\n" + "="*50)
