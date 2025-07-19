from backend.src.prophit_alts.core.base_agent_class import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.distribution_and_retail import distribution_and_retail_system_prompt, distribution_and_retail_user_prompt
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.beverages import beverages_system_prompt, beverages_user_prompt
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.household_products import household_products_system_prompt, household_products_user_prompt
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.personal_care_products import personal_care_products_system_prompt, personal_care_products_user_prompt
from datetime import datetime
import os
import time
import re
import json
from backend.src.db.core.db_config import ProphitAltsSession, MarketSession
from backend.src.utils.parsing_utils import parse_json_from_output
from backend.src.repositories.portfolio_data import add_initial_positions

class DistributionAndRetailAgent(BaseAgent):
    def __init__(self):
        super().__init__(distribution_and_retail_system_prompt, distribution_and_retail_user_prompt)

    def run(self):
        return super().run()

class BeveragesAgent(BaseAgent):
    def __init__(self):
        super().__init__(beverages_system_prompt, beverages_user_prompt)

    def run(self):
        return super().run()

class HouseholdProductsAgent(BaseAgent):
    def __init__(self):
        super().__init__(household_products_system_prompt, household_products_user_prompt)

    def run(self):
        return super().run()

class PersonalCareProductsAgent(BaseAgent):
    def __init__(self):
        super().__init__(personal_care_products_system_prompt, personal_care_products_user_prompt)

    def run(self):
        return super().run()

if __name__ == "__main__":
    agent = PersonalCareProductsAgent()
    output = agent.run()

    output_dict = parse_json_from_output(output)
    add_initial_positions(positions=output_dict, industry="personal_care_products", fund_name="consumer_staples_fund")

