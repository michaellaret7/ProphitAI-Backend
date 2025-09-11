"""
Ultra simple GPT-4o parser utility for converting data to Pydantic models
"""
from typing import Type, TypeVar, Dict, List
from pydantic import BaseModel, Field
from backend.src.utils.choose_model_and_client import openai_model_and_client
import json

T = TypeVar('T', bound=BaseModel)

# Helper model for parsing portfolio data
class PortfolioItem(BaseModel):
    ticker: str
    allocation: float = Field(..., ge=0.0, le=1.0)
    position: str

class PortfolioWrapper(BaseModel):
    """Wrapper to help parse portfolio data"""
    portfolio: List[PortfolioItem]

def parse_with_gpt(
    data: any,
    pydantic_model: Type[T],
    system_prompt: str = None
) -> T:
    """
    Ultra simple function to parse any data into a Pydantic model using GPT-4o
    
    Args:
        data: The data to parse (can be dict, string, etc.)
        pydantic_model: The Pydantic model class to parse into
        system_prompt: Optional custom system prompt (defaults to simple parsing instruction)
    
    Returns:
        Parsed Pydantic model instance
    """
    model, client = openai_model_and_client('gpt-4o')
    
    if system_prompt is None:
        system_prompt = f"Parse the provided data into the {pydantic_model.__name__} format."
    
    # Convert data to string if it's not already
    data_str = str(data) if not isinstance(data, str) else data
    
    # Use OpenAI's structured output parsing
    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": data_str}
        ],
        response_format=pydantic_model
    )
    
    return completion.choices[0].message.parsed

def parse_portfolio_with_gpt(data: any) -> Dict:
    """
    Parse any data into a portfolio dictionary format
    
    Args:
        data: Any input data (string, dict, list, etc.)
    
    Returns:
        Dict in format: {"TICKER": {"allocation": 0.x, "position": "long/short"}, ...}
    """
    model, client = openai_model_and_client('gpt-4o')
    
    # Convert data to string
    data_str = str(data) if not isinstance(data, str) else data
    
    system_prompt = """Parse the input into a portfolio format. 
    Extract tickers, allocations (as decimals between 0-1), and positions (long/short).
    Examples of input formats you might see:
    - "AAPL 10% long, MSFT 5% short"  
    - {"AAPL": 0.1, "MSFT": -0.05}
    - [("AAPL", 0.1, "long"), ("MSFT", 0.05, "short")]
    Always output as a list of portfolio items."""
    
    # Parse to intermediate format
    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": data_str}
        ],
        response_format=PortfolioWrapper
    )
    
    parsed = completion.choices[0].message.parsed
    
    # Convert to desired dict format
    portfolio_dict = {}
    for item in parsed.portfolio:
        portfolio_dict[item.ticker] = {
            "allocation": item.allocation,
            "position": item.position.lower()
        }
    
    return portfolio_dict
