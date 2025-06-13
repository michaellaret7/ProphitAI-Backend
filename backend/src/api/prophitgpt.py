from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import json

from openai import OpenAI
from backend.src.utils.choose_model_and_client import deepseek_model_and_client, openai_model_and_client, grok_model_and_client, perplexity_model_and_client

from backend.src.prophitai_gpt.functionSchemas.tools import tools
from backend.src.utils.formatting import strip_formatting
from backend.src.utils.ticker_utils import name_to_ticker
from backend.src.utils.retrieve_portfolio_from_db import retrieve_user_current_portfolio
from backend.src.prophitai_gpt.dataRetrievalTools.retrieve_financial_metrics import retrieve_financial_metric
from backend.src.auth import get_current_user

# ---------------------------------------------------------------------------
# Configuration for Grok / OpenAI client
# ---------------------------------------------------------------------------

model, client = deepseek_model_and_client('deepseek-chat')

# ---------------------------------------------------------------------------
# FastAPI setup
# ---------------------------------------------------------------------------

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str  # "user" or "assistant" or "system"
    content: str

class ChatRequest(BaseModel):
    message: str  # newest user message
    history: Optional[List[Message]] = None  # optional previous conversation history

class ChatResponse(BaseModel):
    response: str

# ---------------------------------------------------------------------------
# Helper to execute tool calls emitted by the LLM
# ---------------------------------------------------------------------------

def _handle_tool_call(tool_call, current_user):
    """
    Execute tool calls emitted by the LLM and format the response.
    
    Processes the requested tool (get_portfolio_data or retrieve_financial_metric),
    executes it with the provided arguments, and returns a properly formatted message
    to append to the conversation history.
    
    Args:
        tool_call: OpenAI tool call object containing function name, arguments, and call ID.
        current_user: The authenticated user object.
        
    Returns:
        Dict containing role, content, and tool_call_id for the conversation history.
    """
    function_name = tool_call.function.name
    call_id = tool_call.id
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        # Malformed arguments – return error message
        return {
            "role": "tool",
            "content": f"Error: Could not parse arguments for tool {function_name}.",
            "tool_call_id": call_id,
        }

    # ------------------------------------------------------------------
    # get_portfolio_data
    # ------------------------------------------------------------------
    if function_name == "get_portfolio_data":
        user_id = current_user.id

        portfolio_df = retrieve_user_current_portfolio(
            user_id=user_id
        )
        if portfolio_df is None:
            result_str = "Error: Portfolio data could not be retrieved."
        elif portfolio_df.empty:
            result_str = f"No portfolio data found for user."
        else:
            result_str = portfolio_df.to_string()

        return {
            "role": "tool",
            "content": "Here is the user's portfolio data. Please format and display it appropriately:\n\n"
            + result_str,
            "tool_call_id": call_id,
        }

    # ------------------------------------------------------------------
    # retrieve_financial_metric
    # ------------------------------------------------------------------
    if function_name == "retrieve_financial_metric":
        ticker = args.get("ticker")
        metric_name = args.get("metric_name")

        potential_ticker = name_to_ticker(ticker)
        if potential_ticker:
            ticker = potential_ticker

        if not metric_name:
            result_str = "Error: Metric name was not provided."
        else:
            metric_data = retrieve_financial_metric(ticker, metric_name)
            if metric_data:
                result_str = f"Historical {metric_name} for {ticker}:\n"
                for date_val, val in metric_data:
                    date_str = str(date_val) if date_val else "N/A"
                    result_str += f"  Date: {date_str}, {metric_name}: {val:.2f}\n"
            elif metric_data == []:
                result_str = (
                    f"No historical data found for metric '{metric_name}' for ticker '{ticker}'."
                )
            else:
                result_str = (
                    f"Could not retrieve data for metric '{metric_name}' for ticker '{ticker}'."
                )

        result_str = strip_formatting(result_str)
        return {"role": "tool", "content": result_str, "tool_call_id": call_id}

    # ------------------------------------------------------------------
    # Unknown tool – should not normally happen
    # ------------------------------------------------------------------
    return {
        "role": "tool",
        "content": f"Error: Unknown tool '{function_name}'.",
        "tool_call_id": call_id,
    }

# ---------------------------------------------------------------------------
# Core chat logic
# ---------------------------------------------------------------------------

def _generate_assistant_response(user_message: str, history: Optional[List[Dict[str, str]]] = None, current_user=None) -> str:
    """
    Generate an AI assistant response using the configured LLM with tool calling capabilities.
    
    Runs a conversation loop with the model, handling any tool calls until a final answer
    is produced. Uses a Thought → Action → Observation pattern internally.
    
    Args:
        user_message: The new message from the user to respond to.
        history: Optional list of previous conversation messages (dicts with 'role' and 'content').
        current_user: The authenticated user object.
        
    Returns:
        str: The final assistant response with formatting stripped.
    """

    # Base system prompt identical to standalone script
    messages = [
        {
            "role": "system",
            "content": (
                "Role: You are an expert portfolio manager, specializing in all things trading and investing.\n\n"
                "Follow the Thought → Action → Observation loop internally (Do not print your thoughts):\n"
                "1. Thought: brief reasoning.\n"
                "2. Action: call ONE tool exactly like  \n"
                "   Action: tool_name(param=value, …)\n"
                "3. PAUSE  \n"
                "4. Observation: reflect on the tool result.\n\n"
                "IMPORTANT: \n"
                "- if the user proceeds with a question (e.g. what should I buy?) do not initiate any order placing tools"
            ),
        }
    ]

    # Append history if provided
    if history:
        for h in history:
            # Support both plain dicts and Pydantic Message objects
            role = h.role if hasattr(h, "role") else h.get("role")
            content = h.content if hasattr(h, "content") else h.get("content")

            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})

    # Append the new user message
    messages.append({"role": "user", "content": user_message})

    while True:
        completion = client.chat.completions.create(
            model=model, 
            messages=messages, 
            tools=tools, 
            tool_choice="auto"
        )

        response_msg = completion.choices[0].message
        messages.append(response_msg)

        if response_msg.tool_calls:
            # Execute each tool and append its observation
            for tool_call in response_msg.tool_calls:
                tool_obs_msg = _handle_tool_call(tool_call, current_user)
                messages.append(tool_obs_msg)
            # Loop again for model to incorporate observations
            continue
        else:
            # Final answer – return stripped
            return strip_formatting(response_msg.content)

# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

@router.post("/prophitgpt/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user=Depends(get_current_user)):
    """
    Handle chat requests for the ProphitGPT AI assistant API endpoint.
    
    Processes incoming chat messages with optional conversation history and returns
    AI-generated responses using the configured LLM model with tool capabilities.
    
    Args:
        request: ChatRequest containing the message and optional conversation history.
        current_user: The authenticated user object, injected by dependency.
        
    Returns:
        ChatResponse: Object containing the AI assistant's response.
        
    Raises:
        HTTPException: 500 error if response generation fails.
    """
    try:
        answer = _generate_assistant_response(request.message, request.history, current_user)
        return ChatResponse(response=answer)
    except Exception as e:
        # Log error server-side; return generic error to client
        print(f"Error in ProphitGPT chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error generating response from ProphitGPT.") 