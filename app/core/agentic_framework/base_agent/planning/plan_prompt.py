plan_prompt = """
🚨 CRITICAL INSTRUCTION - READ CAREFULLY 🚨

YOU MUST CREATE A PLAN BEFORE DOING ANY WORK.

⛔ DO NOT call any tools right now
⛔ DO NOT analyze anything yet
⛔ DO NOT execute any tasks yet
⛔ DO NOT gather data yet

YOUR ONLY JOB IN THIS ITERATION: Output a JSON plan that describes the work you will do in FUTURE iterations.

WHEN BUILDING A PLAN, THINK THROUGH THE PLAN STEP BY STEP AND BREAK IT DOWN. FOR EXAMPLE, THESE ARE IMPORTANT QUESTIONS TO ASK YOURSELF:
- What is the task/goal?
- How can I break this down into a high level plan?
- What tools are at my disposal?
- When and where should I take reasoning steps?
etc...

This is the PLANNING phase. Execution comes later.

================================================================================

Based on the system prompt, user prompt, available tools, and any other relevant context, create a structured plan. The format of the plan should be in the following JSON format:
{
    "tasks": [
        {
            "id": "1",
            "description": "Task 1",
            "subtasks": [
                {
                    "id": "1a",
                    "description": "Subtask 1a"
                },
                {
                    "id": "1b",
                    "description": "Subtask 1b"
                }
            ]
        },
        {
            "id": "2",
            "description": "Task 2",
            "subtasks": [
                {
                    "id": "2a",
                    "description": "Subtask 2a"
                }
            ]
        }
    ]
}

Example of a good plan:
{
    "tasks": [
        {
            "id": "1",
            "description": "Analyze the portfolio's performance and risk metrics",
            "subtasks": [
                {
                    "id": "1a",
                    "description": "Get performance metrics for each ticker in the portfolio"
                },
                {
                    "id": "1b",
                    "description": "Get risk metrics for each ticker in the portfolio"
                },
                {
                    "id": "1c",
                    "description": "Analyze and observe the performance and risk metrics"
                }
            ]
        },
        {
            "id": "2",
            "description": "Generate final recommendations",
            "subtasks": [
                {
                    "id": "2a",
                    "description": "Summarize key findings"
                },
                {
                    "id": "2b",
                    "description": "Propose specific trade ideas with evidence"
                }
            ]
        }
    ]
}

**IMPORTANT WORKFLOW INSTRUCTIONS:**

After planning, you will execute tasks following this pattern for EACH iteration:

1. **Thinking**: In 1-3 sentences state what you will do next and why
2. **Identify** the next required task/subtask (strict sequential order: 1a, 1b, 1c, then 2a, 2b, etc.) and mark it in progress using `update_tasks`
3. **Execute** the work for that subtask using available tools
4. **Analyze** tool result(s) in 1-3 sentences: key findings → implications → next step
5. **Mark complete** using `update_tasks` AFTER finishing the work (include brief evidence)
6. **Move** to the next task/subtask and repeat
7. **Before finalizing**: perform a brief reflection (2-4 sentences) and then provide the Final Answer

**Example iteration workflow:**
- Iteration 5: Work on subtask 2a → Use tools → Mark 2a complete
- Iteration 6: Work on subtask 2b → Use tools → Mark 2b complete

**When ALL tasks are complete:** You MUST provide your final answer by starting with "Final Answer:" followed by your comprehensive response.

**Do NOT create a final task like "Return final answer" - this happens automatically when all tasks are complete.**

**NON-SKIPPING RULE:** You MUST NOT skip any main tasks or subtasks. Always follow the plan's sequential order exactly.

================================================================================

🚨 REMINDER: THIS IS THE PLANNING PHASE 🚨

You are in iteration 1. Your output should be ONLY the JSON plan above.

DO NOT:
❌ Call any tools (you'll do this in later iterations)
❌ Provide analysis (you'll do this after planning)
❌ Execute tasks (execution comes after planning)

DO:
✅ Output ONLY the JSON plan in the format shown above
✅ Make the plan comprehensive and detailed
✅ Ensure subtasks are specific and actionable

Now, output your plan in the JSON format shown above. Begin your response with the opening brace {
"""
