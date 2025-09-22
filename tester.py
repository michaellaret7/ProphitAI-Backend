"""
Braintrust Tool-Calling Agent Evaluation: Travel Assistant
This example evaluates an AI travel assistant that uses multiple tools to help users plan trips.

Requirements:
pip install braintrust openai
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from braintrust import Eval, init_logger
from app.utils.choose_model_and_client import openai_model_and_client
import random

# Initialize OpenAI client
model, client = openai_model_and_client('gpt-4o-mini')

# ================== MOCK TOOL IMPLEMENTATIONS ====================
def search_flights(departure: str, destination: str, date: str, budget: Optional[str] = None) -> Dict:
    """Mock flight search tool"""
    # In production, this would call a real flight API
    base_price = random.randint(200, 800)
    flights = [
        {
            "airline": "United Airlines",
            "flight_number": "UA 123",
            "departure_time": "08:00",
            "arrival_time": "11:30",
            "price": base_price,
            "duration": "3h 30m"
        },
        {
            "airline": "Delta",
            "flight_number": "DL 456",
            "departure_time": "14:00",
            "arrival_time": "17:15",
            "price": base_price + 50,
            "duration": "3h 15m"
        },
        {
            "airline": "Southwest",
            "flight_number": "SW 789",
            "departure_time": "18:30",
            "arrival_time": "22:00",
            "price": base_price - 75,
            "duration": "3h 30m"
        }
    ]
    
    if budget and budget == "low":
        flights = [f for f in flights if f["price"] < 500]
    
    return {
        "status": "success",
        "route": f"{departure} → {destination}",
        "date": date,
        "flights_found": len(flights),
        "flights": flights[:3]  # Return top 3
    }

def search_hotels(location: str, checkin: str, checkout: str, preferences: Optional[str] = None) -> Dict:
    """Mock hotel search tool"""
    hotels = [
        {
            "name": "Hilton Downtown",
            "rating": 4.5,
            "price_per_night": 180,
            "amenities": ["WiFi", "Pool", "Gym", "Restaurant"],
            "distance_from_center": "0.5 miles"
        },
        {
            "name": "Budget Inn Express",
            "rating": 3.8,
            "price_per_night": 89,
            "amenities": ["WiFi", "Breakfast"],
            "distance_from_center": "2.1 miles"
        },
        {
            "name": "The Grand Plaza",
            "rating": 4.8,
            "price_per_night": 350,
            "amenities": ["WiFi", "Spa", "Pool", "Concierge", "Restaurant", "Bar"],
            "distance_from_center": "0.2 miles"
        }
    ]
    
    if preferences:
        if "luxury" in preferences.lower():
            hotels = [h for h in hotels if h["price_per_night"] > 250]
        elif "budget" in preferences.lower():
            hotels = [h for h in hotels if h["price_per_night"] < 150]
    
    return {
        "status": "success",
        "location": location,
        "checkin": checkin,
        "checkout": checkout,
        "hotels_found": len(hotels),
        "hotels": hotels
    }

def get_weather(location: str, date: str) -> Dict:
    """Mock weather tool"""
    weather_conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Thunderstorms"]
    temp = random.randint(60, 85)
    
    return {
        "status": "success",
        "location": location,
        "date": date,
        "forecast": {
            "condition": random.choice(weather_conditions),
            "high_temp": temp + 10,
            "low_temp": temp,
            "precipitation_chance": random.randint(0, 60),
            "humidity": random.randint(40, 80)
        }
    }

def calculate_trip_budget(flights: List, hotel_nights: int, hotel_price: float, daily_expenses: float = 100) -> Dict:
    """Mock budget calculation tool"""
    flight_total = sum(f.get("price", 0) for f in flights)
    hotel_total = hotel_nights * hotel_price
    expenses_total = hotel_nights * daily_expenses
    
    return {
        "status": "success",
        "breakdown": {
            "flights": flight_total,
            "accommodation": hotel_total,
            "daily_expenses": expenses_total,
            "total": flight_total + hotel_total + expenses_total
        },
        "currency": "USD"
    }

# ================== TOOL DEFINITIONS FOR OPENAI ====================
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two cities",
            "parameters": {
                "type": "object",
                "properties": {
                    "departure": {"type": "string", "description": "Departure city"},
                    "destination": {"type": "string", "description": "Destination city"},
                    "date": {"type": "string", "description": "Travel date (YYYY-MM-DD)"},
                    "budget": {"type": "string", "enum": ["low", "medium", "high"], "description": "Budget preference"}
                },
                "required": ["departure", "destination", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Search for hotels in a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or area to search"},
                    "checkin": {"type": "string", "description": "Check-in date (YYYY-MM-DD)"},
                    "checkout": {"type": "string", "description": "Check-out date (YYYY-MM-DD)"},
                    "preferences": {"type": "string", "description": "Hotel preferences (luxury, budget, business, etc.)"}
                },
                "required": ["location", "checkin", "checkout"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather forecast for a location on a specific date",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or location"},
                    "date": {"type": "string", "description": "Date for forecast (YYYY-MM-DD)"}
                },
                "required": ["location", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_trip_budget",
            "description": "Calculate total trip budget based on flights, hotels, and expenses",
            "parameters": {
                "type": "object",
                "properties": {
                    "flights": {"type": "array", "items": {"type": "object"}, "description": "List of flight objects with prices"},
                    "hotel_nights": {"type": "integer", "description": "Number of nights"},
                    "hotel_price": {"type": "number", "description": "Price per night"},
                    "daily_expenses": {"type": "number", "description": "Estimated daily expenses", "default": 100}
                },
                "required": ["flights", "hotel_nights", "hotel_price"]
            }
        }
    }
]

# Tool execution dispatcher
TOOL_FUNCTIONS = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "get_weather": get_weather,
    "calculate_trip_budget": calculate_trip_budget
}

# ================== DATASET ====================
def get_travel_planning_dataset():
    """Test cases for travel planning scenarios"""
    return [
        {
            "input": {
                "user_request": "I need to fly from New York to Los Angeles next Friday for a weekend trip. Can you find me flights and hotels? I'm on a tight budget.",
                "context": {
                    "current_date": "2024-12-10",
                    "next_friday": "2024-12-20",
                    "return_date": "2024-12-22"
                }
            },
            "expected": {
                "tools_to_use": ["search_flights", "search_hotels"],
                "should_consider_budget": True,
                "should_search_return_flight": True,
                "date_accuracy": True
            },
            "metadata": {"scenario": "budget_weekend_trip"}
        },
        {
            "input": {
                "user_request": "What's the weather going to be like in Miami next week? I'm planning a beach vacation.",
                "context": {
                    "current_date": "2024-12-10",
                    "next_week": "2024-12-17"
                }
            },
            "expected": {
                "tools_to_use": ["get_weather"],
                "should_mention_beach_conditions": True,
                "should_suggest_packing": True
            },
            "metadata": {"scenario": "weather_check"}
        },
        {
            "input": {
                "user_request": "Plan a complete 3-day business trip to Chicago. I need flights from Boston, a nice hotel near downtown, and what's my total budget looking like?",
                "context": {
                    "current_date": "2024-12-10",
                    "trip_start": "2024-12-15",
                    "trip_end": "2024-12-18"
                }
            },
            "expected": {
                "tools_to_use": ["search_flights", "search_hotels", "calculate_trip_budget"],
                "should_pick_business_hotel": True,
                "should_calculate_total": True,
                "should_be_comprehensive": True
            },
            "metadata": {"scenario": "business_trip_full"}
        },
        {
            "input": {
                "user_request": "Find me luxury hotels in Paris for my anniversary next month. We want something really special.",
                "context": {
                    "current_date": "2024-12-10",
                    "next_month": "2025-01-15"
                }
            },
            "expected": {
                "tools_to_use": ["search_hotels"],
                "should_filter_luxury": True,
                "should_be_romantic_tone": True,
                "should_mention_amenities": True
            },
            "metadata": {"scenario": "luxury_anniversary"}
        },
        {
            "input": {
                "user_request": "I'm flying to Seattle tomorrow but worried about the weather. Should I pack an umbrella?",
                "context": {
                    "current_date": "2024-12-10",
                    "tomorrow": "2024-12-11"
                }
            },
            "expected": {
                "tools_to_use": ["get_weather"],
                "should_give_packing_advice": True,
                "should_mention_seattle_rain": True
            },
            "metadata": {"scenario": "weather_packing_advice"}
        }
    ]

# ================== TRAVEL ASSISTANT AGENT ====================
def travel_assistant_agent(input_data: Dict[str, Any], version: str = "v1") -> Dict[str, Any]:
    """
    Travel assistant that uses tools to help users plan trips.
    Returns both the response and metadata about tool usage.
    """
    
    user_request = input_data["user_request"]
    context = input_data.get("context", {})
    
    # System prompts for different versions
    system_prompts = {
        "v1": "You are a travel assistant. Help users plan their trips using the available tools.",
        "v2": """You are an expert travel assistant. 
        - Always use appropriate tools to get accurate information
        - Consider budget constraints when mentioned
        - For trips, search both outbound and return flights
        - Provide comprehensive responses with specific details
        - Calculate total budgets when planning complete trips
        - Be mindful of dates and use the context provided"""
    }
    
    # Add context to the user message
    enhanced_request = f"{user_request}\n\nContext: Today is {context.get('current_date', '2024-12-10')}"
    if "next_friday" in context:
        enhanced_request += f", next Friday is {context['next_friday']}"
    if "trip_start" in context:
        enhanced_request += f", trip starts {context['trip_start']} and ends {context['trip_end']}"
    
    messages = [
        {"role": "system", "content": system_prompts[version]},
        {"role": "user", "content": enhanced_request}
    ]
    
    # Track tool calls for evaluation
    tool_calls_made = []
    tool_responses = []
    
    # First API call to determine tool usage
    response = client.chat.completions.create(
        model="gpt-4o-mini" if version == "v2" else "gpt-3.5-turbo",
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
        temperature=0.3
    )
    
    message = response.choices[0].message
    
    # Process tool calls if any
    if message.tool_calls:
        # First, add the assistant message with tool_calls
        messages.append({
            "role": "assistant",
            "content": message.content if message.content else "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })
        
        # Then process each tool call and add tool responses
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Record the tool call
            tool_calls_made.append({
                "name": function_name,
                "arguments": function_args
            })
            
            # Execute the tool
            if function_name in TOOL_FUNCTIONS:
                tool_result = TOOL_FUNCTIONS[function_name](**function_args)
                tool_responses.append(tool_result)
                
                # Add tool response message
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result),
                    "tool_call_id": tool_call.id
                })
        
        # Get final response after tool execution
        final_response = client.chat.completions.create(
            model="gpt-4o-mini" if version == "v2" else "gpt-3.5-turbo",
            messages=messages,
            temperature=0.3
        )
        
        final_message = final_response.choices[0].message.content
    else:
        final_message = message.content
    
    return {
        "response": final_message,
        "tool_calls": tool_calls_made,
        "tool_responses": tool_responses,
        "tokens_used": response.usage.total_tokens
    }

# ================== SCORING FUNCTIONS ====================
def tool_selection_scorer(input_data: Dict, output: Dict, expected: Dict) -> float:
    """
    Scores whether the agent used the correct tools for the task.
    """
    expected_tools = set(expected.get("tools_to_use", []))
    used_tools = set([call["name"] for call in output.get("tool_calls", [])])
    
    if not expected_tools:
        return 1.0
    
    # Check if all expected tools were used
    correct_tools = expected_tools.intersection(used_tools)
    unnecessary_tools = used_tools - expected_tools
    
    # Penalize for missing tools and unnecessary tools
    score = len(correct_tools) / len(expected_tools)
    penalty = len(unnecessary_tools) * 0.1
    
    return max(0, score - penalty)

def tool_parameter_scorer(input_data: Dict, output: Dict, expected: Dict) -> float:
    """
    Scores whether tools were called with appropriate parameters.
    """
    tool_calls = output.get("tool_calls", [])
    context = input_data.get("context", {})
    score_components = []
    
    for call in tool_calls:
        if call["name"] == "search_flights":
            args = call["arguments"]
            # Check if dates are correct
            if "date" in args:
                if "next_friday" in context and context["next_friday"] in args["date"]:
                    score_components.append(1.0)
                elif "trip_start" in context and context["trip_start"] in args["date"]:
                    score_components.append(1.0)
                else:
                    score_components.append(0.5)  # Date present but maybe not optimal
            
            # Check if budget considered when mentioned
            if expected.get("should_consider_budget") and "budget" in args:
                score_components.append(1.0)
            elif expected.get("should_consider_budget") and "budget" not in args:
                score_components.append(0.0)
        
        elif call["name"] == "search_hotels":
            args = call["arguments"]
            # Check for luxury preference when expected
            if expected.get("should_filter_luxury"):
                if "preferences" in args and "luxury" in args["preferences"].lower():
                    score_components.append(1.0)
                else:
                    score_components.append(0.0)
    
    return sum(score_components) / len(score_components) if score_components else 1.0

def response_completeness_scorer(input_data: Dict, output: Dict, expected: Dict) -> float:
    """
    Evaluates if the response addresses all aspects of the user's request.
    """
    response = output.get("response", "").lower()
    score_components = []
    
    # Check for budget consideration
    if expected.get("should_consider_budget"):
        if any(word in response for word in ["budget", "affordable", "cheap", "economical", "save"]):
            score_components.append(1.0)
        else:
            score_components.append(0.0)
    
    # Check for return flight mention
    if expected.get("should_search_return_flight"):
        if any(word in response for word in ["return", "round trip", "back", "both ways"]):
            score_components.append(1.0)
        else:
            score_components.append(0.3)
    
    # Check for weather-related packing advice
    if expected.get("should_give_packing_advice"):
        if any(word in response for word in ["pack", "bring", "umbrella", "jacket", "clothes"]):
            score_components.append(1.0)
        else:
            score_components.append(0.0)
    
    # Check for comprehensive response
    if expected.get("should_be_comprehensive"):
        word_count = len(response.split())
        if word_count > 100:
            score_components.append(1.0)
        elif word_count > 50:
            score_components.append(0.7)
        else:
            score_components.append(0.3)
    
    return sum(score_components) / len(score_components) if score_components else 1.0

def efficiency_scorer(output: Dict) -> float:
    """
    Scores the efficiency of tool usage (not using too many unnecessary tools).
    """
    tool_calls = output.get("tool_calls", [])
    
    if len(tool_calls) == 0:
        return 0.5  # No tools used might be inefficient
    elif len(tool_calls) <= 3:
        return 1.0  # Optimal number
    elif len(tool_calls) <= 5:
        return 0.8  # Acceptable
    else:
        return 0.5  # Too many tool calls

# ================== LOGGING FOR PRODUCTION ====================
def travel_assistant_with_logging(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Production version with detailed tracing"""
    logger = init_logger(project="travel-assistant")
    
    with logger.start_span(name="travel_request", input=input_data) as span:
        result = travel_assistant_agent(input_data, version="v2")
        
        # Log each tool call as a separate span
        for i, tool_call in enumerate(result.get("tool_calls", [])):
            with span.start_span(name=f"tool_{tool_call['name']}") as tool_span:
                tool_span.log(
                    tool=tool_call["name"],
                    arguments=tool_call["arguments"],
                    response=result["tool_responses"][i] if i < len(result["tool_responses"]) else None
                )
        
        span.log(
            output=result["response"],
            metrics={
                "num_tools_called": len(result.get("tool_calls", [])),
                "tokens_used": result.get("tokens_used", 0),
                "response_length": len(result["response"])
            }
        )
        
        return result

# ================== RUN EVALUATION ====================
# if __name__ == "__main__":
#     print("✈️  Starting Travel Assistant Evaluation...\n")
#     print("=" * 60)
    
#     # Evaluate Version 1 (Basic)
#     print("📊 Evaluating Version 1 (Basic System Prompt)...")
#     eval_v1 = Eval(
#         name="Travel Assistant Agent",
#         data=get_travel_planning_dataset,
#         task=lambda input: travel_assistant_agent(input, version="v1"),
#         scores=[
#             tool_selection_scorer,
#             tool_parameter_scorer,
#             response_completeness_scorer,
#             efficiency_scorer
#         ],
#         metadata={
#             "version": "v1_basic",
#             "model": "gpt-3.5-turbo",
#             "system_prompt": "basic"
#         }
#     )
    
    
#     # Evaluate Version 2 (Enhanced)
#     print("📊 Evaluating Version 2 (Enhanced System Prompt)...")
#     eval_v2 = Eval(
#         name="Travel Assistant Agent",
#         data=get_travel_planning_dataset,
#         task=lambda input: travel_assistant_agent(input, version="v2"),
#         scores=[
#             tool_selection_scorer,
#             tool_parameter_scorer,
#             response_completeness_scorer,
#             efficiency_scorer
#         ],
#         metadata={
#             "version": "v2_enhanced",
#             "model": "gpt-4o-mini",
#             "system_prompt": "detailed"
#         }
#     )
    
    
#     # Summary
#     print("=" * 60)
#     print("🎯 EVALUATION COMPLETE!")
#     print("=" * 60)
#     print("\nThis evaluation tested:")
#     print("  • Tool Selection - Did the agent choose the right tools?")
#     print("  • Parameter Quality - Were tools called with correct arguments?")
#     print("  • Response Completeness - Did the response address all needs?")
#     print("  • Efficiency - Was tool usage optimal?")
#     print("\nKey scenarios evaluated:")
#     print("  • Budget-conscious trip planning")
#     print("  • Weather checking for packing advice")
#     print("  • Complete business trip coordination")
#     print("  • Luxury hotel searches")
#     print("\nView detailed results and tool call traces:")


import json
from typing import List, Dict, Any, Optional

def build_dataset_from_agent_messages(log_path: str, max_cases: Optional[int] = None) -> List[Dict[str, Any]]:
    with open(log_path, "r") as f:
        data = json.load(f)
        print(data)

    messages = data.get("messages", [])
    current_date = None
    for m in messages:
        if m.get("role") == "system" and "CURRENT DATE:" in (m.get("content") or ""):
            for line in m["content"].splitlines():
                if "CURRENT DATE:" in line:
                    current_date = line.split("CURRENT DATE:")[1].strip()
                    break
            break

    dataset: List[Dict[str, Any]] = []
    last_user = ""
    seen = set()  # dedupe identical (prompt, tools) pairs

    for m in messages:
        role = m.get("role")
        if role == "user":
            last_user = (m.get("content") or "").strip()
            continue

        if role == "assistant" and m.get("tool_calls"):
            tools = []
            for tc in m["tool_calls"]:
                fn_name = (tc.get("function") or {}).get("name")
                if fn_name:
                    tools.append(fn_name)

            if not tools:
                continue

            key = (last_user[:200], tuple(sorted(set(tools))))
            if key in seen:
                continue
            seen.add(key)

            dataset.append({
                "input": {
                    "user_request": last_user or "Follow the plan and continue.",
                    "context": {"current_date": current_date}
                },
                "expected": {
                    "tools_to_use": sorted(list(set(tools)))
                },
                "metadata": {
                    "scenario": f"log_run_case_{len(dataset)+1}",
                    "tools_observed": tools
                }
            })

            if max_cases and len(dataset) >= max_cases:
                break

    return dataset

dataset = build_dataset_from_agent_messages(
    "/Users/michaellaret/Desktop/ProphitAI/app/core/agentic_framework/agent_output/agent_messages.json"
)

print(dataset)