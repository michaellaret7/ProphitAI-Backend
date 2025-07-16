from backend.src.prophit_alts.core.base_agent_class import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.distribution_and_retail.prompts import system_prompt, user_prompt
from datetime import datetime
import os
import time

class DistributionAndRetailAgent(BaseAgent):
    def __init__(self, system_prompt: str, user_prompt: str):
        super().__init__(system_prompt, user_prompt)

    def run(self):
        return super().run()


if __name__ == "__main__":
    start_time = time.time()

    agent = DistributionAndRetailAgent(system_prompt, user_prompt)
    output = agent.run()

    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"trading_strategy_analysis_{timestamp}.txt"
    output_path = os.path.join(os.path.dirname(__file__), output_filename)

    # Write output to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Multi-Stock Trading Strategy Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Stocks: MSFT, AAPL, LMT\n")
        f.write("=" * 60 + "\n\n")
        f.write(output)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Analysis complete! Output saved to: {output_path}")
    print(f"Execution time: {elapsed_time:.2f} seconds")
