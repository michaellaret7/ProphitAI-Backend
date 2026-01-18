from app.utils.choose_model_and_client import get_model_and_client
from app.repositories.transcripts_data import get_latest_transcript

model, client = get_model_and_client("openai", "gpt-4o")

transcript = get_latest_transcript("CRWV")

system_prompt = """
You are a helpful assistant that chunks earnings call transcripts into its proper structure:

1. Theres the prepared remarks 
2. Then the analyst Q&A 
3. If the prepared remarks are too long we can semantically chunk that and then keep the the smaller parts in tact
    1. **Operator intro**
        - Safe harbor note (“forward-looking statements”), replay info, housekeeping.
    2. **Management welcome**
        - CEO/IR sets agenda, introduces speakers.
    3. **Prepared remarks**
        - **CEO**: narrative (quarter highlights, strategy, demand, customers, product).
        - **CFO**: financials (revenue, margins, opex, cash flow, balance sheet, guidance).
        - Sometimes other execs (COO, segment heads).
    4. **Guidance / outlook**
        - Next quarter + full-year ranges, key drivers, sensitivities.
    5. **Q&A**
        - Operator queues analysts.
        - **Analyst question(s)** → **Management answer(s)** (often CEO/CFO).
        - Follow-ups happen here.
    6. **Closing remarks**
        - CEO thanks, sign-off.
    7. **Operator close**
        - “You may now disconnect.”

Please return the entire transcript in the proper structure, in json format.
"""

def chunk_earnings_call(transcript: str) -> list[str]:
    """
    Chunk an earnings call transcript into a list of chunks.
    """
    completions = client.chat.completions.create(
        model=model,
        messages=[  
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ]
    )
    return completions.choices[0].message.content

print(chunk_earnings_call(transcript["content"]))