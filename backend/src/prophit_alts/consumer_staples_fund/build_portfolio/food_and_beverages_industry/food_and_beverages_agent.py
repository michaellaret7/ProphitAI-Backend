from backend.src.prophit_alts.base_agent_class import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.food_and_beverages_industry.prompts import system_prompt, user_prompt
import time

class RetailFundCIO(BaseAgent):
    def __init__(self, system_prompt: str, user_prompt: str):
        super().__init__(system_prompt, user_prompt)

    def run(self):
        return super().run()


if __name__ == "__main__":
    start_time = time.time()
    agent = RetailFundCIO(system_prompt, user_prompt)
    agent.run()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.2f} seconds")