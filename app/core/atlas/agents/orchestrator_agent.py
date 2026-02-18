"""OrchestratorAgent - Decomposes complex tasks and delegates to worker agents."""

from functools import partial
from typing import Optional, List, Union

from pydantic import BaseModel
from langfuse import propagate_attributes
from app.core.atlas.models.notebook import Notebook

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback, AgentResponse
from app.core.atlas.models.callbacks import ChatCallback
from app.core.atlas.models.new_plan import Plan
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.base.search_engine import LLM_WEB_SEARCH_TOOL
from app.core.atlas.tools.orchestrator import (
    UPDATE_PLAN_TOOL,
    update_plan,
)
from app.core.atlas.tools.orchestrator.retrieve_note import retrieve_notes, RETRIEVE_NOTES_TOOL
from app.core.atlas.tools.worker_agent.setup import DEPLOY_WORKER_TOOL, _resolve_and_deploy
from app.core.atlas.prompts.orchestrator_agent import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    build_plan_prompt,
)
from app.core.atlas.agents.planner_agent import PlannerAgent
from app.utils.gpt_parser import parse_with_gpt

from app.core.atlas.tools.alpaca import (
    ALPACA_ACCT_AND_PORTFOLIO_TOOL,
    OPTIONS_LOOKUP_TOOL,
    OPTIONS_CHAIN_TOOL,
    OPTIONS_TRADE_TOOL,
    TRADE_TOOL,
    CANCEL_ORDER_TOOL,
    CANCEL_ALL_ORDERS_TOOL,
    CLOSE_POSITION_TOOL,
    CLOSE_ALL_POSITIONS_TOOL,
    REPLACE_ORDER_TOOL,
    PORTFOLIO_HISTORY_TOOL,
    ASSET_LOOKUP_TOOL,
    GET_ORDER_TOOL,
    EXERCISE_OPTION_TOOL,
    MULTI_LEG_ORDER_TOOL,
    OPTION_BARS_TOOL,
    OPTION_LATEST_QUOTE_TOOL,
    OPTION_SNAPSHOT_TOOL,
)


class OrchestratorAgent(AgentBase):
    """Decomposes complex tasks and delegates sub-tasks to worker agents.

    Supports two modes:
    - Default: Ad-hoc decomposition using think + deploy_worker_agent.
    - Plan-first: PlannerAgent generates a structured plan, then the
      orchestrator executes each task and marks it complete via update_plan.
    """

    def __init__(
        self,
        task: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 50,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        plan_first: bool = True,
        format_output: Optional[type[BaseModel]] = None,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "orchestrator",
    ):
        provider = provider or "gemini"
        model = model or "gemini-3-pro-preview"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.task = task
        self.format_output = format_output
        self.notebook = Notebook()

        self.plan_first = plan_first
        self.plan: Optional[Plan] = None

        # Attributes required by ExecutionLoop and ToolHandler (duck typing)
        self.chat_callback = chat_callback if chat_callback is not None else NoOpChatCallback()
        self.session_id = session_id
        self.simulation_date = None
        self.note_titles: List[str] = []
        self.output_dir = None

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(
            self, self.printer, chat_callback=self.chat_callback
        )
        self.execution_loop = ExecutionLoop(self)

        #----- Register the Tools specific to the orchestrator agent -----#
        # Reason: partial pre-binds notebook + callback so the LLM only sees task + tools.
        self.add_tool(
            **DEPLOY_WORKER_TOOL,
            function=partial(_resolve_and_deploy, self.notebook, self.chat_callback),
        )
        self.add_tool(
            **RETRIEVE_NOTES_TOOL,
            function=partial(retrieve_notes, self.notebook),
        )
        self.add_tool(**LLM_WEB_SEARCH_TOOL)

    def run(self) -> AgentResponse:
        """Execute the orchestrator's task decomposition and delegation loop."""
        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="orchestrator_agent.run",
            input=self.task,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:
        
            self.langfuse.update_current_trace(
                name="OrchestratorAgent",
                input=self.task,
                metadata={
                    "provider": self.provider,
                    "model": self.model,
                    "max_iterations": str(self.max_iterations),
                },
            )

            # ----- Keep the planner agent inside the orchestrator span ----- #
            if self.plan_first:
                print("Plan-first mode enabled. Generating plan...")

                planner = PlannerAgent(
                    task=self.task, 
                    print_mode=PrintMode.PRODUCTION,
                    provider="gemini", 
                    model="gemini-3-pro-preview"
                )

                self.plan = planner.run()

                self.add_tool(**{
                    **UPDATE_PLAN_TOOL,
                    "function": partial(update_plan, self.plan, self.chat_callback),
                })

                self.chat_callback.on_plan_created(self.plan) # notify the callback when the plan is generated
                
                print(f"Plan generated: {self.plan}")
                print("="*100)

            system_prompt = build_plan_prompt(self.plan) if self.plan else ORCHESTRATOR_SYSTEM_PROMPT

            self.messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self.task},
            ]

            with propagate_attributes(
                session_id=self.session_id,
                tags=["OrchestratorAgent", self.provider],
                metadata={"model": self.model}
            ):
                result = self.execution_loop.execute()

            self.langfuse.update_current_trace(output=result["answer"])
            run_span.update(output=result["answer"])

            parsed_output = None
            if result["stop_reason"] == "answer_ready" and self.format_output:
                try:
                    parsed_output = parse_with_gpt(
                        query=result["answer"],
                        target_model=self.format_output,
                    )
                except Exception as e:
                    print(f"Error parsing output: {e}")
                    parsed_output = None

            return AgentResponse(
                answer=result["answer"],
                tool_calls_made=result["tool_calls"],
                tokens_used=result["total_tokens"],
                iterations=result["iterations"],
                stop_reason=result["stop_reason"],
                plan=self.plan if self.plan else None,
                parsed_output=parsed_output if parsed_output else None,
            )

if __name__ == "__main__":
    x="""
    Task: Read through your last message, and build me an options strategy that heavily bets on Nvidia hitting earnings.
    Put the trade on and maximize the upside while trying to minimize the downside. Clear out some of the old nvidia options and any underperforming 
    positions to clear up some space for this new trade. 

    This was your last message:
    Now I have all the data I need to deliver the most comprehensive NVIDIA earnings analysis possible. Let me compose the final answer.

🟢 NVIDIA (NVDA) Earnings Deep Dive — February 25, 2026
Analyst Opinion: BEAT & BULLISH — with nuance
Current Price: $188.77 | Market Cap: $4.60T | Earnings Date: February 25, 2026 (After Market Close)

📋 PART 1: THE SETUP — Key Facts
Item	Detail
Earnings Date	Wednesday, February 25, 2026 — After Market Close
Quarter Reporting	Q4 FY2026 (Fiscal quarter ending January 26, 2026)
Management Q4 Guide (from Q3 call, Nov 19, 2025)	~$65B revenue | ~74.8% GAAP / 75.0% non-GAAP gross margin
Q4 Revenue Consensus	$65.62B avg (range: $64.72B–$67.03B, 28 analysts)
Q4 EPS Consensus	$1.52 avg (range: $1.49–$1.55, 29 analysts)
Q1 FY2027 Revenue Consensus (next guide)	$71.63B avg (range: $65.97B–$76.75B, 27 analysts)
Q3 FY2026 Actual	$57.006B revenue (+22% sequential, beat $54B guide by ~5.6%)
Critical observation: Management guided Q4 at ~$65B. Consensus at $65.62B sits only slightly above that guidance — building in almost no cushion for upside. Yet NVIDIA's recent beat magnitude is accelerating: Q1 +2%, Q2 +1.3%, Q3 +5.6%. The bar is lower than it looks.

📈 PART 2: REVENUE TRAJECTORY — The Runway Is Accelerating
Quarter	Revenue	Sequential Growth	YoY Growth
Q2 FY2025 (Jul 2024)	$30.040B	—	—
Q3 FY2025 (Oct 2024)	$35.082B	+16.8%	—
Q4 FY2025 (Jan 2025)	$39.331B	+12.1%	—
Q1 FY2026 (Apr 2025)	$44.062B	+12.0%	+69.2%
Q2 FY2026 (Jul 2025)	$46.743B	+6.1% ⚠️	+55.6%
Q3 FY2026 (Oct 2025)	$57.006B	+22.0% 🚀	+62.5%
Q4 FY2026 Consensus	$65.62B	+15.1%	+66.8%
The Q3 acceleration (+22% sequential) was Blackwell igniting. The consensus +15.1% sequential for Q4 may prove conservative if Blackwell GB200 rack systems continue shipping at pace.

Data Center remains the engine at 88–90% of total revenue ($51.2B in Q3 FY2026). Gross margins have recovered strongly from the Q1 FY2026 dip (caused by a $4.5B H20 export-control inventory charge) — Q3 GM was 73.4%, and management guided Q4 to ~75% non-GAAP — a meaningful step up that signals Blackwell cost curves are normalizing.

🌍 PART 3: BUSINESS DRIVERS — What's ACTUALLY Moving the Needle
✅ Powerful Tailwinds
1. Hyperscaler Capex Is DOUBLING in 2026 — The Single Biggest Tailwind

Hyperscaler	2025 Capex	2026 Capex Guide	Change
Alphabet/Google	~$91B	$175B–$185B	~+95% 🔥
Meta	~$66–72B	$115B–$135B	~+73% 🔥
Amazon (AWS)	~$125B (cash capex)	↑ "Will increase"	Accelerating
Microsoft	—	FY26 growth > FY25	Accelerating
JPMorgan estimates: ~54% aggregate capex growth for the top 5 hyperscalers in 2026. Company midpoints for Amazon/Alphabet/Meta imply ~60% increase. Global AI infra spend could reach ~$715B.

2. Meta "Millions of NVIDIA Chips" Multiyear Deal (Announced Feb 17, 2026 — Just Before Earnings)
Reuters/CNBC confirmed NVIDIA signed a multiyear deal to supply Meta with "millions" of current AND future AI processors, including Blackwell/Rubin GPUs, NVIDIA CPUs, and networking hardware (Vera Rubin rack-scale systems). This is the single most important near-term demand signal — it confirms NVIDIA's pipeline is booked deep into the future and customer concentration in Meta (~9% of NVDA revenue) is strengthening, not diversifying away.

3. Sovereign AI / Regional Buildouts Expanding
India's Yotta Data Services is building a $2B AI hub using NVIDIA Blackwell Ultra chips (announced Feb 17, 2026). This illustrates demand is broadening well beyond the Big 4 US hyperscalers to "AI factory" customers globally.

4. DeepSeek Efficiency → Accelerates, Not Kills, GPU Demand
The DeepSeek AI efficiency narrative spooked markets earlier in 2026, but the hyperscaler capex numbers tell the real story: Google explicitly stated 78% lower Gemini serving unit costs in 2025 yet simultaneously guided $175–185B in 2026 capex. Efficiency is enabling more deployments, not reducing them — a textbook Jevons Paradox outcome.

⚠️ Headwinds & Risks
1. US Export Controls on China (H20/HGX): The Q1 FY2026 GM crash to 60.5% (from 73%) was caused entirely by a $4.5B inventory/purchase obligation charge on H20 chips blocked by export rules. China headwinds are ongoing and could flare. This is the single biggest wild-card risk.

2. Custom Silicon Competition: Google TPU, Amazon Trainium, and Microsoft's custom chips are scaling. These take some internal AI workloads from NVIDIA. However, given the sheer scale of capex acceleration, NVIDIA can lose share on the margin and still grow absolute revenue explosively.

3. Networking Competition: Arista's CEO noted deployment mix shifted from ~99% NVIDIA networking to ~20–25% AMD in some clusters over the past year. Ethernet ecosystems are gaining vs. InfiniBand in some deployments, which could pressure NVIDIA's networking revenue attach rate.

4. High Expectations Bar / Positioning: Some smart money has been reducing NVDA exposure — SoftBank dissolved its stake (Feb 17, 2026 SEC filing), and David Tepper's Appaloosa trimmed its position. Seeking Alpha published "Nvidia Q4: Why Even A Record Beat Could Sink the Stock" (Feb 18, 2026). This "sell the news" anxiety is real.

5. Supply Chain (CoWoS/HBM): Blackwell GB200 NVLink rack systems require advanced CoWoS-L packaging and HBM3e memory. Any supply constraint here could cap upside vs the bull case.

🎯 PART 4: SCENARIO ANALYSIS — Bear / Base / Bull
🐻 BEAR CASE — Probability: ~15%
Metric	Bear Case
Q4 Revenue	$63.5B–$65.5B (miss to in-line)
Q4 EPS	$1.44–$1.50
Gross Margin (non-GAAP)	72–74% (flat/worse vs. guide)
Q1 FY2027 Guide	$68–71B (at/below $71.63B consensus)
Expected Stock Reaction	–8% to –15%
What causes it: Supply chain bottleneck in CoWoS packaging or HBM3e limits Blackwell shipments. New export control actions on China hurt revenue. Hyperscaler digestion/inventory pause (similar to the June 2025 deceleration that caused Q2's slower +6.1% sequential). Gross margin pressured by Blackwell ramp costs or incremental charges. Q1 guide at/below consensus kills the growth narrative.

📊 BASE CASE — Probability: ~55% (My Call)
Metric	Base Case
Q4 Revenue	$68B–$70B (~3–7% beat)
Q4 EPS	$1.60–$1.65 (~5–8% beat)
Gross Margin (non-GAAP)	74.5%–75.5% (at/above guide, expanding)
Q1 FY2027 Guide	$73B–$77B (+2–8% above consensus)
Full Year FY2027 Trajectory	$303B+ NTM revenue
Expected Stock Reaction	+5% to +10%
What causes it: Blackwell GB200 NVL rack systems shipping at plan. Hyperscaler pulls accelerating on the back of confirmed 2026 capex ramps. Meta multiyear deal begins translating to recognized revenue. Gaming RTX 50 series provides modest additional upside. Gross margin benefits from Blackwell cost curve normalization (consistent with management's ~75% non-GAAP guide). Q1 guide comes in meaningfully above consensus, reassuring investors that the revenue ramp continues sequentially.

🐂 BULL CASE — Probability: ~30%
Metric	Bull Case
Q4 Revenue	$70B–$73B (7–11% beat)
Q4 EPS	$1.68–$1.78 (~10–17% beat)
Gross Margin (non-GAAP)	75.5%–77% (upside surprise)
Q1 FY2027 Guide	$78B–$85B (8–19% above consensus)
Expected Stock Reaction	+12% to +20%+
What causes it: Blackwell Ultra (B300/GB300) pulls forward into Q4 alongside GB200 ramp. Spectrum-X Ethernet networking sees a step-function increase in attach rate. Multiple large customers (not just Meta) announce significant forward purchase commitments. Management delivers a "jaw-dropping" Q1 guide that resets the entire forward model. This would push NVDA toward $210–230 and could trigger analyst price target upgrades toward the $300+ range.

🎯 PART 5: MY VERDICT — BEAT IS THE MOST PROBABLE OUTCOME
I expect NVIDIA to BEAT Q4 FY2026 consensus. Here's why:
The 5 Pillars of My Beat Call:

The Guide Was Conservative — Pattern Says So. Management guided Q4 at ~$65B. Consensus is $65.62B. NVIDIA has beaten its own guide in every recent quarter: Q1 (+2%), Q2 (+1.3%), Q3 (+5.6%). The beat magnitude is growing as Blackwell ramps. Extrapolating this pattern gets you to $68–70B easily.

The Sequential Math Favors Upside. Q3 produced a monster +22% sequential leap (the biggest in recent quarters) as Blackwell shipped in volume. Consensus assumes only +15.1% sequential for Q4. If Blackwell is still ramping — and there's no evidence it's slowing — +15% is a conservative baseline.

Hyperscaler Demand Is Locked In, Not Speculative. Google is doubling capex to $175–185B. Meta is near-doubling to $115–135B. Amazon says 2026 capex exceeds 2025's $125B. This is committed capex, not wishful thinking. NVIDIA is the primary beneficiary. The Meta multiyear deal announced days before earnings further validates the backlog.

Gross Margins Are EXPANDING, Not Compressing. Management guided Q4 gross margins to ~75% non-GAAP — materially above Q3's 73.6%. This signals that Blackwell ramp costs (which temporarily squeezed margins) are normalizing. Expanding margins on growing revenues = explosive earnings upside. EPS beat could be even larger than the revenue beat in percentage terms.

The Beat Pattern Is Structural, Not Accidental. NVDA builds guidance conservatively. They manage supply expectations tightly, then over-deliver as manufacturing yields improve and shipments accelerate through the quarter. This is their playbook and it's been working every single quarter.

The KEY Line Items Most Likely to Surprise:
Q1 FY2027 Revenue Guide — This is THE most important number. A guide of $74B+ beats consensus ($71.63B). A guide of $78B+ is a blowout.
Gross Margin — If Q4 non-GAAP GM hits 75%+, it confirms the Blackwell cost curve thesis and accelerates EPS estimates.
Data Center Revenue — Watch for absolute number vs. the implied ~$58–59B consensus. A $62–63B DC print would be a significant positive surprise.
📉 PART 6: WILL WALL STREET BE HAPPY OR DISAPPOINTED?
Valuation Context
Metric	Current	Interpretation
Stock Price	$188.77	Flat 6-month, +32.7% 1-year
Trailing P/E (TTM)	46.1x	Elevated but justified by growth
Forward P/E (FY2026E ~$4.68 EPS)	~40.3x	Still premium
Forward P/E (FY2027E ~$7.84 EPS)	~24.1x	🔑 Remarkably reasonable for 70%+ growth
Forward P/S (NTM)	~15.1x	Premium but in-line with AI leader status
FCF TTM	$77.3B	One of the most profitable companies in history
Consensus Price Target	$267 (median $273.50)	41% upside to consensus target
Analyst Distribution	60 Buy/Strong Buy, 3 Hold, 1 Sell	94% bullish (of 64 analysts)
The valuation paradox: At a 24x forward P/E on FY2027 estimates for a company growing revenue 70%+ YoY and generating $77B in annual free cash flow, NVDA is arguably not expensive on the numbers. The concern is not valuation — it's expectations.

Why the Stock Has Been Flat Despite a Phenomenal Business
The stock is essentially flat over 3–6 months because:

Expectations pricing: Investors already "know" NVIDIA is beating — the question is by how much
AI narrative fatigue & DeepSeek scare: Efficiency concerns created doubt about GPU demand longevity
Institutional repositioning: Large holders (SoftBank, Appaloosa) reducing exposure signals caution at current levels
"Show me" mentality: Wall Street wants to see sustained revenue ramps into 2026, not just one-quarter beats
What Wall Street NEEDS to Be Happy (Positive Reaction):
Threshold	Revenue	Q1 Guide	GM	Stock Reaction
🔴 Disappointing	≤$65.5B	≤$71.6B	<73%	–8% to –15%
🟡 Muted / Mixed	$66–68B	$72–74B	73–75%	Flat to –3%
🟢 Solid Beat	$68–70B	$74–77B	75–76%	+5% to +10%
🚀 Blowout	$70B+	$78B+	76%+	+12% to +20%+
The "implied bar" from the stock's flat behavior and the SA "beat could sink the stock" narrative suggests the MARKET's real bar is probably $68–70B revenue and a $74B+ Q1 guide — not just the $65.62B consensus. This matters enormously.

⚡ PART 7: ACTIONABLE OPINION INTO/THROUGH EARNINGS
My Call: BULLISH — Lean Long into Earnings
Expected Outcome: Beat consensus on revenue ($68–70B), beat on EPS ($1.62), confirm gross margin expansion (~75% non-GAAP), guide Q1 FY2027 above consensus ($74–78B). Wall Street will be modestly satisfied to pleased — not euphoric, but not disappointed.

Expected Market Reaction: +5% to +10% in after-hours/next day. The reaction will be governed almost entirely by the Q1 revenue guide. If the guide is merely $73B (only ~2% above consensus), the stock may only be +2–3% or go flat. If the guide is $78B+, you're looking at a +10–15% move.

🔑 Key Risks That Could Flip the Bullish Call:
Risk	Probability	Impact
New China export restrictions (surprise announcement)	Medium	–10 to –20% on stock
Blackwell supply chain issue (CoWoS yield miss, HBM shortage)	Low-Medium	–8 to –15%
Q1 Guide at/below $71.63B consensus	Low	–5 to –12% (sell-the-fact despite revenue beat)
Gross margin miss (below 73% non-GAAP)	Low	–5 to –8% (margin compression thesis fears return)
Key customer (hyperscaler) signals slower near-term pulls	Very Low	–8 to –15%
📍 Post-Earnings Signals to Watch (What Confirms vs. Invalidates the Thesis):
✅ CONFIRMS the bull thesis:

Q1 revenue guide ≥ $75B
Data center revenue > $60B in Q4 (vs ~$51.2B in Q3)
Non-GAAP gross margin ≥ 75% for Q4 and guided higher for Q1
Management provides explicit Blackwell Ultra / Rubin roadmap update showing 2026+ demand visibility
Positive commentary on networking revenue (Spectrum-X wins accelerating)
No new China/export control concerns raised
❌ INVALIDATES or weakens the thesis:

Q1 guide ≤ $72B (Wall Street will read this as growth deceleration)
Gross margin guidance guided DOWN for Q1 (would suggest supply chain issues)
Management language turns cautious on hyperscaler order visibility
New export control restrictions announced or telegraphed
Gaming segment disappoints materially (signals demand outside DC is weakening)
🧭 THE BOTTOM LINE
NVIDIA will almost certainly beat Q4 FY2026 consensus estimates. The combination of management's conservative $65B guide (vs $65.62B consensus), an accelerating beat pattern, Blackwell ramp momentum, and the most powerful AI infrastructure capex cycle in history (Google doubling to $175–185B, Meta near-doubling to $115–135B) makes a revenue beat to $68–70B the most likely outcome. EPS will outperform even more due to expanding gross margins guided to ~75% non-GAAP.

Wall Street's reaction will depend almost entirely on the Q1 FY2027 guide. This is the make-or-break number. A $74B+ guide means +5–10% pop. A $78B+ guide means a potential +15–20% rip. A guide at/below consensus ($71.63B) could perversely cause a sell-off even on a revenue beat.

The stock is attractively valued at ~24x FY2027 earnings estimates for a company growing 70%+ YoY with $77B in annual free cash flow — one of the most powerful free cash flow machines in corporate history. The consensus price target of $267 implies 41% upside from current levels. The 94% analyst bullish rating reflects genuine fundamental conviction, not just hype.

My actionable opinion: Bullish into and through earnings. Position for the base/bull case outcome. The asymmetry favors longs — if NVDA delivers a blowout Q4 and guides Q1 to $78B+, the stock tests $210–235 quickly. A bear-case miss scenario (15% probability) risks a pullback to $165–175. Given hyperscaler capex commitment visibility and the Blackwell ramp trajectory, that bear case requires multiple things to go wrong simultaneously. The bull case requires only the continuation of already-established trends.

⚠️ The #1 tail risk remains geopolitical: any surprise escalation in US-China export controls targeting NVIDIA's remaining China-eligible products could materially disrupt the thesis regardless of how well the underlying business is executing. This is an external, binary risk that cannot be hedged through fundamental analysis alone.

Analysis as of February 18, 2026. Earnings February 25, 2026 after market close. This is analytical research, not financial advice.
    """
    orchestrator = OrchestratorAgent(
        task = x,
        print_mode=PrintMode.PRODUCTION,
        provider="anthropic",
        model="claude-sonnet-4-6",
    )
    result = orchestrator.run()
    print(result.answer)