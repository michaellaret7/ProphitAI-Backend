from backend.src.utils.choose_model_and_client import openai_model_and_client
from backend.src.portfolio_optimization.phase_two.phase_two_prompts import phase_two_system_prompt, phase_two_user_prompt
from backend.src.data_models.phase_two_models import PhaseTwoRecommendations
import logging

logger = logging.getLogger(__name__)

class PhaseTwoRunLLM:
    def __init__(self):
        self.model, self.client = openai_model_and_client()
    
    def build_system_prompt(self, user_profile_formatted, num_top_tickers):
        system_prompt = phase_two_system_prompt.format(user_profile_formatted=user_profile_formatted, num_tickers=num_top_tickers)
        return system_prompt
    
    def build_user_prompt(self, data):
        user_prompt = phase_two_user_prompt.format(asset_class_data=data)
        return user_prompt
    
    def run(self, system_prompt, user_prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
    
        response_content = response.choices[0].message.content

        return self.parse_llm_response(response_content)
    
    def parse_llm_response(self, response_content):
        try:
            # Clean the response if needed (remove markdown code blocks)
            if response_content.startswith("```json"):
                response_content = response_content[7:]
            if response_content.endswith("```"):
                response_content = response_content[:-3]
            response_content = response_content.strip()
            
            # Parse and validate with Pydantic
            recommendations = PhaseTwoRecommendations.model_validate_json(response_content)

            return recommendations
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {response_content}")
            raise ValueError(f"Invalid LLM response format: {e}")