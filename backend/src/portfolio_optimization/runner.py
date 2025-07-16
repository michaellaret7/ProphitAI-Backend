from backend.src.portfolio_optimization.phase_two.phase_two_run import PhaseTwo
from backend.src.portfolio_optimization.phase_one.phase_one_run import optimize
from backend.src.data.user_information import get_user_information
from backend.src.db.core.db_config import UserSession, MarketSession
from backend.src.db.core.user_data_models import Portfolio
from backend.src.db.core.market_data_models import Ticker
import logging
import os
from datetime import datetime, timezone
import json
import uuid

logger = logging.getLogger(__name__)

test_email = "michaellaret7@gmail.com"

def save_portfolio_to_db(final_recommendations, portfolio_name, user_id=None, company_id=None):
    """
    Save portfolio recommendations to the database.
    
    Args:
        final_recommendations (dict): The final recommendations dictionary from phase_two
        portfolio_name (str): Name for this portfolio
        user_id (str, optional): User ID who owns this portfolio
        company_id (str, optional): Company ID if portfolio belongs to a company
    """
    user_session = UserSession()
    market_session = MarketSession()
    
    try:
        # Generate a unique portfolio ID for this portfolio session
        portfolio_id = uuid.uuid4()
        
        # Loop through each asset class in the final recommendations
        for asset_class_name, asset_class_data in final_recommendations.items():
            recommendations = asset_class_data.get("recommendations", [])
            
            # Loop through each recommendation within the asset class
            for recommendation in recommendations:
                ticker_symbol = recommendation.get("ticker")
                allocation = recommendation.get("allocation")
                reason_for_recommendation = recommendation.get("reason_for_recommendation")
                supporting_metrics = recommendation.get("supporting_metrics", {})
                
                # Get ticker information from market database to get sector/industry info
                ticker_info = market_session.query(Ticker).filter(
                    Ticker.ticker == ticker_symbol
                ).first()
                
                # Create portfolio entry
                portfolio_entry = Portfolio(
                    portfolio_id=portfolio_id,
                    name=portfolio_name,
                    ticker=ticker_symbol,
                    sector=ticker_info.sector if ticker_info else asset_class_name,
                    industry=ticker_info.industry if ticker_info else asset_class_name,
                    sub_industry=ticker_info.sub_industry if ticker_info else asset_class_name,
                    allocation=allocation,
                    is_current=False,
                    user_id=user_id,
                    company_id=company_id,
                    created_date=datetime.now(timezone.utc),
                    updated_date=datetime.now(timezone.utc),
                    supporting_metrics=supporting_metrics,
                    reason_for_rec=reason_for_recommendation
                )
                
                user_session.add(portfolio_entry)
                
                logger.info(f"Added {ticker_symbol} to portfolio with {allocation}% allocation")
        
        # Commit all changes
        user_session.commit()
        logger.info(f"Successfully saved portfolio '{portfolio_name}' to database with portfolio_id: {portfolio_id}")
        
        return portfolio_id
        
    except Exception as e:
        user_session.rollback()
        logger.error(f"Error saving portfolio to database: {str(e)}")
        raise
    finally:
        user_session.close()
        market_session.close()

def main(email: str):
    phase_one_data = optimize(email=email) # --> run the phase_one optimization process and return the data
    logger.info(phase_one_data)

    phase_two = PhaseTwo(phase_one_data) # --> initialize the phase_two class with the phase_one data

    user_profile_formatted = get_user_information() # --> get the user profile formatted data

    filtered_and_analyzed_tickers = phase_two.screen_and_analyze_tickers() # --> filter the tickers based on daily average volume and composite score

    final_recommendations = phase_two.final_recommendations(filtered_and_analyzed_tickers, user_profile_formatted) # --> run the phase_two process and return the data

    logger.info(final_recommendations)

    # Save portfolio to database
    current_date = datetime.now().strftime('%Y-%m-%d')
    portfolio_name = "Auto/Tech and ETF focused Portfolio"
    
    try:
        portfolio_id = save_portfolio_to_db(
            final_recommendations=final_recommendations,
            portfolio_name=portfolio_name,
            user_id="f2231c17-92f5-4e78-9d36-a2c0c3f525a5",  # Set this to actual user ID if available
            company_id="91ad5428-3d79-467f-ae89-83639e20a894"  # Set this to actual company ID if available
        )
        logger.info(f"Portfolio saved with ID: {portfolio_id}")
    except Exception as e:
        logger.error(f"Failed to save portfolio to database: {str(e)}")

    # write this to the output file 
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"portfolio_optimization_{current_date}.txt")

    with open(output_filename, "a", encoding="utf-8") as f:
        f.write("\n\n" + "="*80 + "\n")
        f.write("PHASE TWO: FINAL RECOMMENDATIONS\n")
        f.write("="*80 + "\n\n")
        f.write(json.dumps(final_recommendations, indent=4))
        
    return final_recommendations

if __name__ == "__main__":
    main(test_email)