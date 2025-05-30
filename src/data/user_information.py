import json

def get_user_information():
    """
    Get user information from the user's profile.
    """
    user_data = {
        "user_information": {
            "age": "52",
            "net_worth": "$3,500,000",
            "investment size(as a percentage of net worth)": "70%",
            "risk_tolerance": "Moderate-High",
            "investment_goals": "Capital Growth and Income Generation",
            "time_horizon": "5 Years",
            "Overall Description": """
            I am an experienced investor with a moderate to high risk tolerance. I am looking for a portfolio that will grow my capital and provide me with a reliable income stream.
            The portfolio should be well balanced and include some private equity etfs. I am also very bullish on the tech sector and the future of AI.
            """
        }
    }

    return user_data