from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import EarningsTranscript, Ticker
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.utils.choose_model_and_client import openai_model_and_client


session = MarketSession()
ticker = 'PG'
transcript = session.query(EarningsTranscript).join(Ticker).filter(Ticker.ticker == ticker).first()
print(transcript.date)
transcript = serialize_sqlalchemy_obj(transcript)
# print(transcript)
session.close()


system_prompt = """
You are a financial analyst at a hedge fund. You will be given an earnings transcript from PG.
You will read the entire transcript, and then answer the following questions:
1. What is the overall tone of the transcript?
2. Did the operators say anything that could be considered a warning sign?
3. What was their tone? Optimistic, Concerned, Neutral, etc.
4. Were there any overwhelming positives or negatives?
5. Based on the transcript what is the overall outlook for the next Quarter/Year/5 Years?

Finally, Provide a Strong Buy/Buy/Hold/Sell/Strong Sell recommendation based on the transcript.
"""

model, client = openai_model_and_client()

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript['content']}
    ],
    temperature=0.7
)

response_content = response.choices[0].message.content
print(response_content)