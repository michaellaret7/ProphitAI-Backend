from backend.src.portfolio_optimization.phase_two.phase_two_run import PhaseTwo
from backend.src.portfolio_optimization.phase_one.phase_one_run import optimize
from backend.src.data.user_information import get_user_information
import logging
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)

test_user_id = "user_01JXG39MMAVW1P3XVGX7YHN2DT"
test_email = "michael@laret.com"

def main(user_id: str, email: str):
    phase_one_data = optimize(user_id=user_id, email=email) # --> run the phase_one optimization process and return the data
    logger.info(phase_one_data)

    phase_two = PhaseTwo(phase_one_data) # --> initialize the phase_two class with the phase_one data

    user_profile_formatted = get_user_information() # --> get the user profile formatted data

    filtered_tickers = phase_two.filter_tickers() # --> filter the tickers based on daily average volume and composite score

    final_recommendations = phase_two.final_recommendations(filtered_tickers, user_profile_formatted) # --> run the phase_two process and return the data

    logger.info(final_recommendations)

    # write this to the output file 
    current_date = datetime.now().strftime('%Y-%m-%d')
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
    main(test_user_id, test_email)