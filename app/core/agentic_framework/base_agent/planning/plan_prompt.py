plan_prompt = """
🚨 CRITICAL INSTRUCTION - READ CAREFULLY 🚨

YOU MUST CREATE A PLAN BEFORE DOING ANY WORK.

⛔ DO NOT call any tools right now
⛔ DO NOT analyze anything yet
⛔ DO NOT execute any tasks yet
⛔ DO NOT gather data yet

YOUR ONLY JOB IN THIS ITERATION: Output a JSON plan that describes the work you will do in FUTURE iterations.

================================================================================
PLANNING PRINCIPLES
================================================================================

**KEEP PLANS MINIMAL AND PROPORTIONAL TO TASK COMPLEXITY.**

- Simple research query → 1-2 main tasks, 1-3 subtasks each
- Multi-step analysis → 2-3 main tasks with relevant subtasks
- Complex portfolio construction → 3-5 main tasks as needed

Ask yourself:
1. What is the core goal? (Don't overcomplicate it)
2. What's the minimum number of steps to achieve it?
3. What tools do I need?

**AVOID OVER-PLANNING.** If the task is "research X and write a summary", you don't need 5 main tasks. You need: (1) Search/gather information, (2) Synthesize and output.

================================================================================
PLAN FORMAT
================================================================================

Output your plan in this JSON format:
{
    "tasks": [
        {
            "id": "1",
            "description": "Task 1",
            "subtasks": [
                {"id": "1a", "description": "Subtask 1a"},
                {"id": "1b", "description": "Subtask 1b"}
            ]
        },
        {
            "id": "2",
            "description": "Task 2",
            "subtasks": [
                {"id": "2a", "description": "Subtask 2a"}
            ]
        }
    ]
}

================================================================================
EXAMPLES
================================================================================

**Example 1: Simple research query**
User: "What is the outlook for interest rates? Write a research summary."

GOOD plan (minimal, focused):
{
    "tasks": [
        {
            "id": "1",
            "description": "Research interest rate outlook",
            "subtasks": [
                {"id": "1a", "description": "Search macro research for interest rate analysis and Fed outlook"},
                {"id": "1b", "description": "Analyze findings and identify key themes"}
            ]
        },
        {
            "id": "2",
            "description": "Write research output",
            "subtasks": [
                {"id": "2a", "description": "Synthesize findings into formatted research piece with citations"}
            ]
        }
    ]
}

BAD plan (over-engineered for a simple query):
{
    "tasks": [
        {"id": "1", "description": "Understand the research question", "subtasks": [...]},
        {"id": "2", "description": "Gather macro data", "subtasks": [...]},
        {"id": "3", "description": "Analyze historical trends", "subtasks": [...]},
        {"id": "4", "description": "Compare multiple sources", "subtasks": [...]},
        {"id": "5", "description": "Generate final output", "subtasks": [...]}
    ]
}
^ This is too many tasks for a simple research query!

**Example 2: Portfolio analysis (more complex, warrants more tasks)**
User: "Analyze this portfolio's risk and recommend improvements."

Appropriate plan:
{
    "tasks": [
        {
            "id": "1",
            "description": "Analyze portfolio risk metrics",
            "subtasks": [
                {"id": "1a", "description": "Calculate VaR and stress test results"},
                {"id": "1b", "description": "Assess concentration and correlation risk"}
            ]
        },
        {
            "id": "2",
            "description": "Identify improvement opportunities",
            "subtasks": [
                {"id": "2a", "description": "Identify overweight/underweight positions"},
                {"id": "2b", "description": "Research potential diversifying additions"}
            ]
        },
        {
            "id": "3",
            "description": "Generate recommendations",
            "subtasks": [
                {"id": "3a", "description": "Propose specific changes with rationale"}
            ]
        }
    ]
}

================================================================================
EXECUTION WORKFLOW (after planning)
================================================================================

After planning, execute tasks following this pattern for EACH iteration:

1. **Thinking**: In 1-3 sentences state what you will do next and why
2. **Identify** the next required task/subtask (sequential order: 1a, 1b, then 2a, etc.) and mark it in progress using `update_tasks`
3. **Execute** the work for that subtask using available tools
4. **Analyze** tool result(s) in 1-3 sentences: key findings → implications → next step
5. **Mark complete** using `update_tasks` AFTER finishing the work
6. **Move** to the next task/subtask and repeat
7. **Before finalizing**: provide the Final Answer

**When ALL tasks are complete:** Start with "Final Answer:" followed by your response.

**Do NOT create a "Return final answer" task - this happens automatically.**

**NON-SKIPPING RULE:** Follow the plan's sequential order exactly.

================================================================================

🚨 REMINDER: THIS IS THE PLANNING PHASE 🚨

You are in iteration 1. Your output should be ONLY the JSON plan.

DO NOT:
❌ Call any tools
❌ Provide analysis
❌ Execute tasks

DO:
✅ Output ONLY the JSON plan
✅ Keep the plan minimal and proportional to task complexity
✅ Ensure subtasks are specific and actionable

Now, output your plan in the JSON format shown above. Begin your response with the opening brace {
"""
