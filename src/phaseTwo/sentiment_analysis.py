import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Import from utils package
from src.utils.caching import cache_result

# Load environment variables
load_dotenv()

# Load environment variables
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL")

@cache_result
def get_news_sentiment(query):
    """
    Get news sentiment for a particular stock.
    
    Args:
        query (str): A detailed query to retrieve recent news about a stock (this should be a detailed query)
        
    Returns:
        str: News sentiment results
    """
    # Set up system and user prompts
    system_prompt = "You are a financial analyst. Analyze news sentiment about stocks objectively."
    user_prompt = f"Analyze the recent news sentiment for: {query}. Provide a summary of the sentiment (positive, negative, or neutral) with supporting evidence from recent articles. The date is {datetime.now().strftime('%Y-%m-%d')}, do not take news into account that is more than 2 weeks old. This is for a stock outlook to see if I should recomend to buy or not. Make sure to look at analyst ratings."
    
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {   
            "role": "user",
            "content": user_prompt
        },
    ]

    # Initialize client with Perplexity API
    perplexity_client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # Chat completion without streaming
        response = perplexity_client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=messages
        )
        
        # Get the response content
        result = response.choices[0].message.content
        return result
                
    except Exception as e:
        error_message = f"Error retrieving news sentiment: {str(e)}"
        print(error_message)
        return error_message

def batch_analyze_news_sentiment(ticker_queries, batch_size=3):
    """
    Analyze news sentiment for multiple tickers in batches to reduce API calls.
    
    Args:
        ticker_queries: List of tuples (ticker, query)
        batch_size: Number of tickers to analyze in each batch
        
    Returns:
        dict: Dictionary mapping tickers to their sentiment analysis
    """
    results = {}
    
    # Process tickers in batches
    for i in range(0, len(ticker_queries), batch_size):
        batch = ticker_queries[i:i+batch_size]
        
        # Prepare combined query for the batch
        combined_query = "\n\n".join([
            f"TICKER: {ticker}\nQUERY: {query}" 
            for ticker, query in batch
        ])
        
        # Set up system prompt for batch processing
        system_prompt = """
You are a financial analyst. Analyze news sentiment about multiple stocks objectively.
I will provide information about several stocks. For EACH stock:
1. Analyze recent news sentiment (positive, negative, or neutral)
2. Provide supporting evidence from recent articles
3. Consider analyst ratings if available

Format your response as:
TICKER1:
[Your analysis for TICKER1]

TICKER2:
[Your analysis for TICKER2]

And so on. Keep each analysis concise but informative.
"""
        
        user_prompt = f"Analyze the recent news sentiment for these stocks. The date is {datetime.now().strftime('%Y-%m-%d')}, do not take news into account that is more than 2 weeks old.\n\n{combined_query}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Make a single API call for the batch
        try:
            # Initialize client with Perplexity API
            perplexity_client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
            
            response = perplexity_client.chat.completions.create(
                model=PERPLEXITY_MODEL,
                messages=messages
            )
            
            batch_result = response.choices[0].message.content
            
            # Parse the batch result to extract individual ticker analyses
            current_ticker = None
            current_analysis = []
            
            # Add a sentinel to process the last ticker
            for line in batch_result.split('\n') + ['SENTINEL:']:
                # Check if this is a ticker header line
                ticker_match = False
                for ticker, _ in batch:
                    if line.startswith(f"{ticker}:") or line.startswith(f"TICKER: {ticker}"):
                        # Save the previous ticker's analysis if there was one
                        if current_ticker:
                            results[current_ticker] = '\n'.join(current_analysis)
                            current_analysis = []
                        
                        # Start new ticker
                        current_ticker = ticker
                        ticker_match = True
                        break
                
                # If this is a sentinel or new ticker was found, continue to next line
                if line.startswith('SENTINEL:') or ticker_match:
                    continue
                    
                # Otherwise add to current analysis
                if current_ticker:
                    current_analysis.append(line)
            
        except Exception as e:
            print(f"Error in batch sentiment analysis: {e}")
            # Fallback to individual processing
            for ticker, query in batch:
                try:
                    results[ticker] = get_news_sentiment(query)
                except:
                    results[ticker] = f"Unable to retrieve sentiment for {ticker}"
    
    return results 

