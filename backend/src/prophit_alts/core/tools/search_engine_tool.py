from backend.src.utils.choose_model_and_client import perplexity_model_and_client
import re 

class AgentSearchEngine:
    def perplexity_free_search(self, query: str):
        model, client = perplexity_model_and_client() # --> initialize model and client for perplexity

        system_prompt = """
        <Role>
        Act as an expert researcher in market research and analysis.
        You have 30 years of experience being a research analyst at the top investment banks and hedge funds in the world
        </Role>

        <Instructions>
        You will be given a query and you will need to research the query and return the most relevant and new information.
        You will need to use the latest data and information to answer the query.
        You will need to use the latest news and information to answer the query.
        You will need to use the latest research and information to answer the query.
        You will need to use the latest analysis and information to answer the query.
        You will need to use the latest insights and information to answer the query.
        </Instructions>

        <Rules>
        You must be as descriptive, informative and detailed as possible.
        You must be as accurate and factual as possible.
        You must be as up to date and relevant as possible.
        Do extensive research on the query and ONLY retrieve information from the top and most reputable sources.
        You have no output token limit.
        </Rules>

        <What to search for>
        - Macro economic data
        - Industry data
        - Company data
        - News
        - Research
        - Insights
        - Analyst Estimates 
        - Analyst Reports
        - Economic Forecasts
        - Economic Data
        - Economic Indicators
        </What to search for>
        """

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

            # chat completion with streaming
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )

            content = response.choices[0].message.content
            cleaned_content = re.sub(r'\[\d+\]', '', content) # --> clean up the content to remove the thinking process tags

            return cleaned_content
        
        except Exception as e:
            print(f"Error: {e}")
            return None