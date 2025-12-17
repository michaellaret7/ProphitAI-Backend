from app.utils.choose_model_and_client import get_model_and_client
import re
import json
from typing import List
from pydantic import BaseModel, Field

model, client = get_model_and_client('groq', 'Kimi-K2-instruct')

class ClaimsSchema(BaseModel):
    claims: List[str] = Field(..., description="A list of claims from the text")

def extract_facts(text: str) -> List[str]:
    """Extract factual claims from the text using an LLM."""
    system_prompt = """
    You are an expert at extracting claims from text.
    Your task is to identify and list all claims present, true or false, in the given text. 
    Each claim should be a single, verifiable statement.
    Consider various forms of claims, including assertions, statistics, and quotes. 
    Do not skip any claims, even if they seem obvious. Do not include in the list 'The text contains a claim that needs to be checked for hallucinations' - this is not a claim.
    Present the claims as a JSON array of strings, and do not include any additional text.
    """

    user_prompt = f"Extract factual claims from this text: {text}"

    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format=ClaimsSchema
    )

    return response.choices[0].message.parsed

if __name__ == "__main__":
    text = """
    Tesla reported record deliveries of 1.8 million vehicles in 2023, representing a 38% increase from the previous year. 
    The company's Gigafactory in Berlin produced over 250,000 Model Y vehicles in its first full year of operation. 
    Elon Musk announced that the Cybertruck would enter mass production in Q3 2024, with initial pricing starting at $39,900 for the base model.
    Tesla's Full Self-Driving (FSD) software is currently available in 15 countries and has accumulated over 500 million miles of autonomous driving data.
    The company's energy storage division deployed 14.7 GWh of battery storage systems globally in 2023, making it the largest energy storage provider in North America.
    Tesla's market capitalization briefly exceeded $1 trillion in November 2023, surpassing the combined value of Toyota, Volkswagen, and Ford.
    The new 4680 battery cells have achieved a 16% increase in range and reduce production costs by $1,500 per vehicle compared to the previous 2170 cells.
    """

    for fact in extract_facts(text).claims:
        print(fact)