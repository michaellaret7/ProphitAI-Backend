import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def deepseek_model_and_client(model: str = None):
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    if model is None:
        model = os.environ.get("DEEPSEEK_MODEL")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    return model, client

def openai_model_and_client(model: str = None):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if model is None:
        model = os.environ.get("OPENAI_MODEL")

    client = OpenAI(api_key=OPENAI_API_KEY)

    return model, client

def grok_model_and_client(model: str = None):
    GROK_API_KEY = os.getenv("GROK_API_KEY")

    if model is None:
        model = os.environ.get("GROK_MODEL")

    client = OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.x.ai/v1",
    )

    return model, client

def perplexity_model_and_client(model: str = None):
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

    if model is None:
        model = os.environ.get("PERPLEXITY_MODEL")

    client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
    
    return model, client
