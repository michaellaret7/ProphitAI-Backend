import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def deepseek_model_and_client(model: str = None):
    """
    Create a DeepSeek model name and OpenAI client instance.
    
    Args:
        model: Model name to use (default: from DEEPSEEK_MODEL env var)
        
    Returns:
        tuple: (model_name, openai_client) for DeepSeek API
    """
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    if model is None:
        model = os.environ.get("DEEPSEEK_MODEL")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    return model, client

def openai_model_and_client(model: str = None):
    """
    Create an OpenAI model name and client instance.
    
    Args:
        model: Model name to use (default: from OPENAI_MODEL env var)
        
    Returns:
        tuple: (model_name, openai_client) for OpenAI API
    """
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if model is None:
        model = os.environ.get("OPENAI_MODEL")

    client = OpenAI(api_key=OPENAI_API_KEY)

    return model, client

def grok_model_and_client(model: str = None):
    """
    Create a Grok model name and OpenAI client instance.
    
    Args:
        model: Model name to use (default: from GROK_MODEL env var)
        
    Returns:
        tuple: (model_name, openai_client) for Grok API
    """
    GROK_API_KEY = os.getenv("GROK_API_KEY")

    if model is None:
        model = os.environ.get("GROK_MODEL")

    client = OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.x.ai/v1",
    )

    return model, client

def perplexity_model_and_client(model: str = None):
    """
    Create a Perplexity model name and OpenAI client instance.
    
    Args:
        model: Model name to use (default: from PERPLEXITY_MODEL env var)
        
    Returns:
        tuple: (model_name, openai_client) for Perplexity API
    """
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

    if model is None:
        model = os.environ.get("PERPLEXITY_MODEL")

    client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
    
    return model, client

def claude_model_and_client(model: str = None):
    """
    Create a Claude model name and OpenAI client instance.
    
    Args:
        model: Model name to use (default: from CLAUDE_MODEL env var)
        
    Returns:
        tuple: (model_name, openai_client) for Claude API
    """
    CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    if model is None:
        model = os.environ.get("ANTHROPIC_MODEL")

    client = OpenAI(api_key=CLAUDE_API_KEY, base_url="https://api.anthropic.com/v1")

    return model, client

def openai_huggingface_model_and_client(model: str = None):
    """
    Create an OpenAI model name and client instance.
    
    Args:
        model: Model name to use (default: from OPENAI_MODEL env var)
        
    Returns:
        tuple: (model_name, openai_client) for OpenAI API
    """
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

    if model is None:
        model = os.environ.get("HUGGINGFACE_MODEL")

    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=HUGGINGFACE_API_KEY,
    )

    return model, client
