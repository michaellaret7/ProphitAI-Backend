"""
Ultra simple GPT-4o parser utility for converting data to Pydantic models
"""
from typing import Type, TypeVar, Dict, List
from pydantic import BaseModel, Field
from app.utils.choose_model_and_client import openai_model_and_client, huggingface_model_and_client
import json
from app.models.portfolio_models import PortfolioInput

T = TypeVar('T', bound=BaseModel)

# Helper model for parsing portfolio data
class PortfolioItem(BaseModel):
    ticker: str
    allocation: float = Field(..., ge=0.0, le=1.0)
    position: str

class PortfolioWrapper(BaseModel):
    """Wrapper to help parse portfolio data"""
    portfolio: List[PortfolioItem]

def parse_with_gpt(query: str, target_model: Type[T], system_prompt: str = None) -> T:
    """
    Generic LLM parser that converts natural language to structured Pydantic models.

    Args:
        query: Natural language input to parse
        target_model: Pydantic model class to parse into
        system_prompt: Optional custom system prompt (default provides generic instructions)

    Returns:
        Parsed instance of target_model
    """
    model, client = openai_model_and_client('gpt-5-mini')
    # model, client = huggingface_model_and_client(model="openai/gpt-oss-120b:fireworks-ai")

    if system_prompt is None:
        system_prompt = f"""Parse the user's input into the requested structured format.
        Extract all relevant information and populate the fields accurately.
        If information is not provided, leave fields as None/null, do not make up any information."""

    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        response_format=target_model,
        reasoning_effort="low"
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
    # Convert data to string
    data_str = str(data) if not isinstance(data, str) else data

    system_prompt = """Parse the input into a portfolio format.
    Extract tickers, allocations (as decimals between 0-1), and positions (long/short).
    Examples of input formats you might see:
    - "AAPL 10% long, MSFT 5% short"
    - {"AAPL": 0.1, "MSFT": -0.05}
    - [("AAPL", 0.1, "long"), ("MSFT", 0.05, "short")]
    Always output as a list of portfolio items."""

    # Parse using generic parser
    parsed = parse_with_gpt(data_str, PortfolioWrapper, system_prompt)

    # Convert to desired dict format
    portfolio_dict = {}
    for item in parsed.portfolio:
        portfolio_dict[item.ticker] = {
            "allocation": item.allocation,
            "position": item.position.lower()
        }

    return portfolio_dict

def canonical_portfolio(portfolio: PortfolioInput | dict) -> Dict[str, Dict]:
    """Convert any portfolio format to canonical dictionary using GPT parser."""
    # If already in the correct format, return as-is
    if isinstance(portfolio, dict):
        # Check if it's already in canonical format
        if all(isinstance(v, dict) and 'allocation' in v and 'position' in v for v in portfolio.values()):
            # Ensure position is lowercase and allocation is float
            return {
                ticker: {
                    "allocation": float(config['allocation']),
                    "position": config['position'].lower() if isinstance(config['position'], str) else config['position']
                }
                for ticker, config in portfolio.items()
            }
    
    # Use GPT parser for any other format
    return parse_portfolio_with_gpt(portfolio)