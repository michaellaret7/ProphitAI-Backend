from openai import OpenAI
from dotenv import load_dotenv
from backend.src.utils.choose_model_and_client import openai_model_and_client

load_dotenv()

model, client = openai_model_and_client()

def agent_a(prompt: str) -> str:
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content.strip()

def agent_b(prompt: str) -> str:
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content.strip()

def run_dialogue(start_msg: str, turns: int = 6) -> None:
    msg = start_msg
    for i in range(turns):
        msg = agent_a(msg)          # A responds
        print(f"A: {msg}")
        print("--------------------------------")
        msg = agent_b(msg)
        print("--------------------------------")
        print(f"B: {msg}")
        print("--------------------------------")


if __name__ == "__main__":
    prompt = """
    You are the CIO of ProphitAI Capital. You are currently in a room with the CRO of ProphitAI Capital.
    You guys are discussing a new fund that you are launching. You will both collectievely decide on the Risk/hedging strategy for the fund.
    The fund will be a long/short Consumer Staples Fund.
    """
    
    # run_dialogue(prompt)

    run_dialogue("You are Agent A. Greet Agent B and ask a question.")



