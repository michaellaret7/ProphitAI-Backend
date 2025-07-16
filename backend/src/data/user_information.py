import json

def get_user_information():
    """
    Get user information from the user's profile.
    
    Returns predefined user profile data including demographics, financial status,
    risk tolerance, and investment goals for portfolio optimization.
    
    Args:
        None
        
    Returns:
        Dict: Dictionary containing comprehensive user information including age,
        net worth, risk tolerance, investment goals, and time horizon.
    """
    user_data = {
        "user_information": {
            "age": "35",
            "net_worth": "$5,000,000",
            "investment size(as a percentage of net worth)": "70%",
            "risk_tolerance": "High",
            "investment_goals": "Capital Growth",
            "time_horizon": "2 Years",
            "Overall Description": """I am a young investor with a high rick tolerance. I am comfortable with volatility and interested in the technology and automobile sectors.
            I am looking for a portfolio that will grow aggressively grow my wealth over the next 2 years. I am olso bullish on etf's, I think they provide good 
            overall exposure and returns. I want you to build me the best portfolio possible for me. The goal is to have a portfolio with smaller drawdowns and higher returns."""
        }
    }

    return user_data