from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.macro_agent_prompts import macro_analyst_system_prompt, macro_analyst_user_prompt
import re
import json
import sys
from io import StringIO
from contextlib import redirect_stdout

class MacroAnalyst(BaseAgent):
    def __init__(self):
        super().__init__(macro_analyst_system_prompt, macro_analyst_user_prompt)

    def run(self):
        return super().run()

#     def get_final_recommendation(self):
#         return """
# {'macro_environment_summary': 'As of July 2025, the global macroeconomic environment is defined by resilient but modest growth, ongoing policy divergence, and heightened downside risks across trade, geopolitics, and financial markets. The world economy has outperformed earlier 2025 forecasts, with global GDP projected to expand by 3.0% in 2025 (IMF baseline), and a modest uptick to 3.1% in 2026. This improvement reflects accommodative financial conditions, selective fiscal expansion, and a front-loading of economic activity ahead of new trade barriers. However, growth remains below pre-2025 expectations due to persistent trade friction, protectionism, and policy uncertainty. \n\n---\n\n**Global Growth and Regional Divergence**\n\nThe resilience in global growth masks significant divergences across regions:\n\n- The United States economy continues to demonstrate underlying strength, with a robust labor market and solid consumer spending. However, the pace of expansion is moderating, and inflation remains above the Federal Reserve’s 2% target. Headline CPI is estimated at 2.7% year-over-year for July 2025, with core inflation at 3.0%. The Federal Reserve is maintaining a cautious stance, keeping the federal funds rate at 4.25%–4.50% despite political pressure for cuts; policymakers are prioritizing inflation containment, even as growth slows and uncertainty about future policy direction persists.\n\n- The Eurozone is experiencing subdued but stable growth, with GDP projected to rise by just 0.9% in 2025. A rebound in Q2 was not enough to offset weak domestic demand, a lagging property sector, and external headwinds from US tariffs and global trade fragmentation. Inflation has fallen back to the ECB’s 2% target, allowing the central bank to pause its rate-cutting cycle at a 1.75% deposit rate. Fiscal support, particularly in Germany, and increased military spending provide some offset, but investment remains weak and labor market gains are plateauing.\n\n- China stands out for its strong headline growth, with H1 2025 GDP up 5.3% year-over-year, outpacing official targets. Industrial output, exports, and targeted investment are the main drivers, while domestic consumption and the property sector remain laggards. Policymakers have deployed proactive fiscal and monetary measures, but the sustainability of above-target growth is in question due to structural property sector weaknesses, soft domestic demand, and the potential for renewed trade friction with the US and other partners.\n\n- India remains a bright spot, maintaining growth above 6% on strong domestic demand and services sector dynamism. Other emerging markets face a challenging environment, contending with higher-for-longer US interest rates, volatile capital flows, and increased vulnerability to climate and geopolitical shocks.\n\n---\n\n**Inflation and Monetary Policy**\n\nGlobal inflation is moderating—forecast at 4.2% in 2025 and 3.6% in 2026—but remains above target in key economies. The US, in particular, faces persistent core inflation, driven by services, energy price volatility, and new tariffs. The Federal Reserve’s reluctance to cut rates despite political pressure reflects concern over inflation’s persistence and the risks of unanchored expectations. In contrast, the ECB is nearing the end of its easing cycle, with inflation at target, and is prepared to act further if growth falters. China’s inflation remains subdued, providing space for continued policy support.\n\nMonetary policy divergence is a core theme: The Fed’s high-for-longer stance is keeping global financial conditions tighter than they might otherwise be, contributing to volatility in capital flows, particularly for emerging markets. Central bank independence is increasingly tested by political pressures, with market sensitivity to policy communication at elevated levels.\n\n---\n\n**Trade, Geopolitics, and Policy Fragmentation**\n\nThe global trade environment remains fraught. Front-loading of activity ahead of new tariffs has masked underlying weakness, while effective tariff rates have been somewhat lower than feared. Still, the reintroduction of US tariffs has led to growth downgrades in the Eurozone and heightened policy uncertainty worldwide. The World Economic Forum and IMF both highlight the risk of persistent trade fragmentation, which is now viewed as a structural feature of the global landscape. Geopolitical risks—particularly in Eastern Europe and East Asia—are amplifying volatility in energy and commodity markets and undermining the predictability of cross-border investment and supply chains.\n\n---\n\n**Financial Conditions, Fiscal Policy, and Market Vulnerabilities**\n\nFinancial conditions have eased since the start of 2025, buoyed by a weaker US dollar and improved market sentiment, but this is a fragile equilibrium. The IMF’s FSAP flags vulnerabilities in systemically important markets, including housing (notably Canada), climate risk, and cyber resilience. Elevated private and public debt leave economies susceptible to abrupt tightening if confidence deteriorates or if central banks are forced to react sharply to inflation or external shocks. Fiscal expansion in the US, China, and parts of Asia is supporting growth but raising concerns about long-run debt sustainability.\n\n---\n\n**Societal, Political, and Climate Risks**\n\nThe World Economic Forum emphasizes rising political polarization and social unrest as macro-critical risks, with the potential for policy gridlock and disruptive elections to undermine effective response to shocks. Extreme weather events, amplified by climate change, are becoming immediate, rather than long-term, macro risks—impacting food security, supply chains, and asset valuations. Rapid technological advances (particularly in AI) are introducing new systemic threats, such as misinformation and cyber-attacks.\n\n---\n\n**Macro Outlook: Balance of Risks, Upside and Downside Scenarios**\n\nThe balance of risks remains tilted to the downside. Major downside risks include:\n- A breakdown in US-China or US-EU trade negotiations, leading to renewed tariff escalation and global supply chain disruption.\n- Persistent inflation in the US or a global commodity price shock, forcing central banks to tighten policy further and triggering a growth slowdown or market correction.\n- Geopolitical escalation (e.g., in Eastern Europe or East Asia), energy market shocks, and climate disasters.\n- Market volatility or a loss of confidence in central bank independence, leading to sudden tightening of financial conditions.\n\nUpside scenarios are possible, particularly if breakthroughs occur in trade talks, if inflation falls faster than expected, or if successful structural reforms and investment in productivity/technology boost long-term growth potential. However, the prevailing expert sentiment is cautious, with institutions such as the IMF, OECD, and WEF all warning that the global outlook is highly sensitive to unforeseen shocks.\n\n---\n\n**Strategic Implications**\n\nFor investors and corporates, the current environment necessitates:\n- Cautious risk management with an emphasis on diversification and resilience to sudden shocks.\n- Close monitoring of policy signals, especially regarding US inflation, Fed policy, and trade negotiations.\n- Scenario planning for downside risks, including market corrections and supply chain disruptions, but also maintaining flexibility to capture upside opportunities if global policy coordination and reforms materialize.\n\nIn sum, the July 2025 macro landscape is one of stable but fragile growth, moderating but divergent inflation, and a risk environment that is both more persistent and more complex than in prior years. Policy is at the center of both the opportunities and the risks: decisive, credible, and coordinated action will be required to restore confidence and lay the groundwork for more robust and sustainable global expansion.', 'key_drivers_and_risks': {'drivers': ['Accommodative financial conditions and selective fiscal expansion, particularly in the US and Asia.', 'Resilient industrial output and exports in China, alongside proactive policy support.', 'Easing global inflation trends (except in the US), allowing for more flexible monetary policy in some regions.', 'Robust labor markets and household incomes in developed economies, supporting consumption and services sectors.'], 'risks': ['Persistent and potentially escalating trade tensions between major economies (US-EU, US-China) and the risk of renewed tariff escalation.', 'Sticky inflation in the US, risking further tightening or delayed rate cuts by the Federal Reserve, with spillovers to global financial conditions.', 'Elevated geopolitical risks, including regional conflicts, energy and commodity market volatility, and fragmented global governance.', 'Structural vulnerabilities in property markets (notably China and parts of the Eurozone), high public and private debt, and potential for abrupt tightening of financial conditions.', 'Climate-related disruptions, technological risks (cyber, misinformation), and growing societal/political polarization undermining policy effectiveness.']}}
# """

    def get_final_recommendation(self):
        """
        Get clean JSON recommendation without ReAct formatting.
        Returns the JSON output extracted from <output></output> tags.
        Suppresses all print output when used as a tool.
        """
        # Capture and suppress all print output
        f = StringIO()
        try:
            with redirect_stdout(f):
                # Temporarily disable verbose output
                original_verbose = self.verbose
                self.verbose = False
                
                full_output = self.run()
                
                # Restore original verbose setting
                self.verbose = original_verbose
            
            # Extract JSON from <output></output> tags
            output_match = re.search(r'<output>(.*?)</output>', full_output, re.DOTALL)
            if output_match:
                json_str = output_match.group(1).strip()
                try:
                    # Parse and return the JSON to ensure it's valid
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the raw content
                    return json_str
            
            # Fallback: return full output if no <output> tags found
            return full_output
            
        except Exception as e:
            # If anything goes wrong, restore verbose and re-raise
            self.verbose = True
            raise e

if __name__ == "__main__":
    macro_agent = MacroAnalyst()
    macro_agent.run()
