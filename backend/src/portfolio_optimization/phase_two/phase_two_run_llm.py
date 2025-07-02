import json
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
            temperature=0.7,
            response_format={"type": "json_object"}  # Force JSON output
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
            
            # Additional cleaning for common issues
            # Remove any BOM characters
            response_content = response_content.lstrip('\ufeff')
            
            # First, try to parse as regular JSON to identify specific issues
            try:
                parsed_json = json.loads(response_content)
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON decode error: {json_error}")
                logger.error(f"Error position: line {json_error.lineno}, column {json_error.colno}")
                
                # Try to extract a snippet around the error position
                lines = response_content.split('\n')
                if json_error.lineno and json_error.lineno <= len(lines):
                    error_line = lines[json_error.lineno - 1]
                    logger.error(f"Error line content: {error_line}")
                    if json_error.colno:
                        logger.error(f"Error at character: '{error_line[json_error.colno-1] if json_error.colno <= len(error_line) else 'END'}'")
                
                raise
            
            # Parse and validate with Pydantic
            recommendations = PhaseTwoRecommendations.model_validate(parsed_json)

            return recommendations
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {response_content}")
            logger.error(f"Response length: {len(response_content)} characters")
            raise ValueError(f"Invalid LLM response format: {e}")