import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "28",
            "net_worth": "$500,000",
            "investment size(as a percentage of net worth)": "80%",
            "risk_tolerance": "High",
            "investment_goals": "Aggressive Capital Growth",
            "time_horizon": "10 Years",
            "Overall Description": """
            I am a young investor with a high risk tolerance and a long investment horizon. I am comfortable with volatility and interested in aggressively growing my wealth through exposure to high-growth sectors such as technology, AI, and emerging markets. I welcome innovative investment vehicles, including leveraged ETFs and cryptocurrencies, as part of a diversified yet growth-oriented portfolio.
            """
        }
    }

    return user_data