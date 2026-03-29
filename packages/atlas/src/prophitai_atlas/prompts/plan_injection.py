"""Utility for injecting plan tasks into any system prompt."""

from itertools import groupby

from prophitai_atlas.models.new_plan import Plan


def inject_plan_tasks(base_prompt: str, plan: Plan) -> str:
    """Append plan task block to a system prompt.

    Groups tasks by step number to communicate parallelism,
    then appends the task block with execution instructions.

    Args:
        base_prompt: The system prompt to append to.
        plan: The Plan with tasks to inject.

    Returns:
        The base_prompt with plan tasks appended.
    """
    # Reason: group tasks by step so the orchestrator sees which are parallel
    sorted_tasks = sorted(plan.tasks, key=lambda t: t.step)
    step_groups = []
    for step_num, tasks in groupby(sorted_tasks, key=lambda t: t.step):
        task_list = list(tasks)
        if len(task_list) == 1:
            step_groups.append(f"Step {step_num}: {task_list[0].id}. {task_list[0].description}")
        else:
            lines = [f"Step {step_num} (parallel):"]
            for t in task_list:
                lines.append(f"  {t.id}. {t.description}")
            step_groups.append("\n".join(lines))

    task_block = "\n".join(step_groups)

    return base_prompt + f"""

## Your Plan

A structured plan has been created for this task. Execute each task by deploying
workers with the right tools, then mark it complete with update_plan.

Tasks within the same step are independent — deploy their workers in parallel.
After ALL tasks are marked complete, synthesize all worker results into your final answer.

### Tasks
{task_block}
"""
