"""Utility for injecting plan tasks into any system prompt."""

from __future__ import annotations

from itertools import groupby
from typing import Any

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

A structured plan has been created for this task. You are an ACTIVE PARTICIPANT —
you call tools directly, do work yourself, and only delegate to workers when it pays off.

For each task, decide how to execute it:
- **Do it yourself** (default): If the task is 1-3 tool calls, if you need the raw output
  for your next step, or if it involves context gathering (memory, past work, notes).
  Call the tools directly, then IMMEDIATELY mark the task complete with update_plan
  before starting the next task. Never batch update_plan calls.
- **Deploy a worker**: Only when the task requires deep multi-step research (4+ tool calls)
  and you only need the conclusion, not the raw data. Workers run in a separate context —
  their intermediate work is discarded, only the final answer comes back.

**CRITICAL: Mark each task complete with `update_plan(task_id)` as soon as it finishes —
do NOT accumulate multiple tasks and mark them all at once.**

Tasks within the same step are independent and can be run in parallel.
After ALL tasks are marked complete, synthesize everything into your final answer.

### Tasks
{task_block}
"""


def inject_plan_tasks_blocks(base_blocks: list[dict[str, Any]], plan: Plan) -> list[dict[str, Any]]:
    """Append a dynamic plan block to Anthropic-friendly system blocks."""
    sorted_tasks = sorted(plan.tasks, key=lambda t: t.step)
    step_groups = []
    for step_num, tasks in groupby(sorted_tasks, key=lambda t: t.step):
        task_list = list(tasks)
        if len(task_list) == 1:
            step_groups.append(f"Step {step_num}: {task_list[0].id}. {task_list[0].description}")
        else:
            lines = [f"Step {step_num} (parallel):"]
            for task in task_list:
                lines.append(f"  {task.id}. {task.description}")
            step_groups.append("\n".join(lines))

    task_block = "\n".join(step_groups)

    return [
        *base_blocks,
        {
            "type": "text",
            "text": f"""## Your Plan

A structured plan has been created for this task. You are an ACTIVE PARTICIPANT —
you call tools directly, do work yourself, and only delegate to workers when it pays off.

For each task, decide how to execute it:
- **Do it yourself** (default): If the task is 1-3 tool calls, if you need the raw output
  for your next step, or if it involves context gathering (memory, past work, notes).
  Call the tools directly, then IMMEDIATELY mark the task complete with update_plan
  before starting the next task. Never batch update_plan calls.
- **Deploy a worker**: Only when the task requires deep multi-step research (4+ tool calls)
  and you only need the conclusion, not the raw data. Workers run in a separate context —
  their intermediate work is discarded, only the final answer comes back.

**CRITICAL: Mark each task complete with `update_plan(task_id)` as soon as it finishes —
do NOT accumulate multiple tasks and mark them all at once.**

Tasks within the same step are independent and can be run in parallel.
After ALL tasks are marked complete, synthesize everything into your final answer.

### Tasks
{task_block}""",
            "cacheable": False,
        },
    ]
