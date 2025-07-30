from backend.src.utils.choose_model_and_client import perplexity_model_and_client, openai_model_and_client
import re 

class AgentSearchEngine:
    def perplexity_free_search(self, query: str):
        model, client = perplexity_model_and_client('sonar-pro') # --> initialize model and client for perplexity

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
    
    def openai_search(self, query: str):
        model, client = openai_model_and_client() 
        """
        Processes a user query using the Deep Research API for detailed market analysis.
        """
        system_message = """
    You are a professional financial analyst preparing a structured, data-driven report. Your task is to analyze the user's query about the macroeconomic environment and its implications for the stock market.

    Do:
    - Focus on data-rich insights: include specific figures, economic indicators (e.g., GDP growth, inflation rates, unemployment), market trends, and statistical data.
    - Prioritize reliable, up-to-date sources: government economic reports (e.g., from the Federal Reserve, Bureau of Labor Statistics), major financial news outlets (e.g., Bloomberg, Reuters, Wall Street Journal), and reports from reputable financial institutions.
    - Structure the report with clear headers for different sections (e.g., "Current Macroeconomic Indicators", "Inflation and Monetary Policy", "Geopolitical Factors", "Stock Market Outlook", "Sector-specific Implications").
    - Include inline citations for all data points and return all source metadata.
    - Be analytical, objective, and avoid speculation without data-backed reasoning.
    """
        try:
            response = client.responses.create(
                model="o3",
                input=[
                    {"role": "developer", "content": [{"type": "input_text", "text": system_message}]},
                    {"role": "user", "content": [{"type": "input_text", "text": query}]}
                ],
                tools=[
                    {"type": "web_search_preview"}
                ]
            )
            
            # For deep research response, the final report is in the last output item
            if hasattr(response, 'output') and response.output:
                final_report = response.output[-1]
                if hasattr(final_report, 'content'):
                    return final_report.content[0].text
            return "No response generated"
            
        except AttributeError as e:
            print(f"AttributeError: {e}")
            print("Make sure you have the latest OpenAI library: pip install --upgrade openai")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None