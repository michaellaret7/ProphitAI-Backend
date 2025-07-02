import json
import openai
from backend.testing.react_agent_class import ReactAgent
import os
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
import numpy as np
import math
from functools import lru_cache
import random
import time
# Load environment variables from .env file
load_dotenv()

# Create a ReactAgent
agent = ReactAgent(llm="gpt-4.1-2025-04-14", api_key=os.environ.get("OPENAI_API_KEY"), max_iterations=100)

def print_word():
    # Simple list of random words
    words = [
        "apple", "banana", "computer", "elephant", "guitar", "mountain", 
        "ocean", "rainbow", "butterfly", "telescope", "adventure", "whisper",
        "treasure", "dragon", "kingdom", "mystery", "journey", "sunset",
        "crystal", "thunder", "forest", "river", "castle", "phoenix"
    ]
    word = random.choice(words)

    return word

# Add tools to the agent
agent.add_tool(
    name="print_word",
    description="Prints a random word to the console.",
    parameters={
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to print to the console."
            }
        },
        "required": [],
        "additionalProperties": False
    },
    function=print_word
)

query = """
You have one tool available to you:
- print_word() --> prints a random word to the console

You must use the tool to print a random word to the console.

Once you print the word, using the tool, respond by saying what comes to your mind first when you see the word?
"""

while True:
    result = agent.run(query)

    print("\n=== AGENT RESPONSE ===\n")
    print(result) 

    time.sleep(60)
