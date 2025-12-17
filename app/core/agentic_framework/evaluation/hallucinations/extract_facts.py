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

    response_parsed = response.choices[0].message.parsed

    return response_parsed.claims

    