plan_prompt = """
YOUR FIRST STEP IN THIS PROCESS IS TO CREATE A STRUCTURED PLAN FOR THE TASK AT HAND.

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
"""