"""Task Management Tool - Update plan task statuses during execution."""

import yaml
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from typing import List, Optional
from app.core.agentic_framework.base_agent.utils.models import TaskStatus
from app.core.agentic_framework.base_agent.logging.task_state_logger import write_task_state_to_file


def update_tasks(
    plan,
    main_task: str,
    subtasks: Optional[List[str]] = None,
    status: str = "in_progress",
    work_summary: Optional[str] = None,
    *,
    output_dir: Optional[str] = None
) -> str:
    """Update the status of tasks and subtasks in the plan.

    Args:
        plan: The agent's plan object
        main_task: The main task ID to update (e.g., "1", "2", "3")
        subtasks: Optional list of subtask IDs to update (e.g., ["1a", "1b"])
        status: New status - "not_started", "in_progress", or "complete"
        work_summary: **CRITICAL WHEN MARKING COMPLETE** - This is the "Work:" section where ALL your
                     reasoning, thinking, analysis, decisions, observations, and conclusions MUST go.
                     This is not just a summary - it's the primary record of your cognitive work. Include:
                     - Your analytical reasoning and thought process
                     - The specific data/tools you used and why
                     - ALL observations made during the analysis
                     - Key findings, insights, and patterns discovered
                     - Decisions made and their rationale
                     - Quantitative results and their interpretation
                     - Conclusions drawn from the analysis
                     Minimum 100 characters required.

    Returns:
        YAML string with success status and updated tasks

    Examples:
        update_tasks(plan, main_task="4", subtasks=["4a", "4b"], status="complete",
                    work_summary="Analyzed portfolio concentration using portfolio_industry_concentration tool. "
                                "Reasoning: Examined sector distribution to identify concentration risks. "
                                "Observations: Noted clustering in technology sector with multiple semiconductor holdings. "
                                "Key findings: Semiconductors represent 32% (NVDA 15%, INTC 10%, AVGO 7%), "
                                "Software 20% (MSFT 12%, PLTR 8%), combined Technology exposure 64%. "
                                "Decision: This extreme concentration creates significant sector-specific risk. "
                                "Conclusion: Portfolio requires diversification into Healthcare and Financials.")
        update_tasks(plan, main_task="5", status="in_progress")
    """
    if not plan or not plan.tasks:
        return error_response("No plan available to update")

    # Normalize status string to enum
    status_map = {
        "not_started": TaskStatus.NOT_STARTED,
        "not started": TaskStatus.NOT_STARTED,
        "in_progress": TaskStatus.IN_PROGRESS,
        "in progress": TaskStatus.IN_PROGRESS,
        "complete": TaskStatus.COMPLETE,
        "completed": TaskStatus.COMPLETE
    }

    status_enum = status_map.get(status.lower())
    if not status_enum:
        return error_response(f"Invalid status: {status}. Must be one of: not_started, in_progress, complete")

    # Validate work_summary when marking complete
    MIN_WORK_SUMMARY_LENGTH = 100
    if status_enum == TaskStatus.COMPLETE:
        if not work_summary or work_summary.strip() == "":
            return error_response("WORK EVIDENCE REQUIRED: You must provide a 'work_summary' parameter when marking tasks as complete. "
                       "This is the 'Work:' section - the PRIMARY record of your reasoning, thinking, observations, analysis, "
                       "decisions, and conclusions. This is where ALL your cognitive work must be documented.")

        if len(work_summary.strip()) < MIN_WORK_SUMMARY_LENGTH:
            return error_response(
                f"INSUFFICIENT WORK EVIDENCE: work_summary must be at least {MIN_WORK_SUMMARY_LENGTH} characters. "
                f"You provided {len(work_summary.strip())} characters. The 'Work:' section is where your ENTIRE "
                f"analytical process goes - reasoning, observations, findings, decisions, conclusions. Provide a "
                f"comprehensive record of your cognitive work, not just a brief note."
            )

        # Check for lazy/gaming attempts
        lazy_phrases = ["done", "completed", "finished", "task complete", "all set"]
        if work_summary.strip().lower() in lazy_phrases:
            return error_response("INSUFFICIENT WORK EVIDENCE: work_summary appears to be a placeholder. The 'Work:' section must "
                       "contain your COMPLETE analytical thinking: What reasoning did you apply? What observations did you "
                       "make? What data did you examine? What patterns did you discover? What decisions did you make and why? "
                       "What conclusions did you reach? This is the core record of your cognitive work.")

    # Find the main task
    task = next((t for t in plan.tasks if t.id == main_task), None)
    if not task:
        return error_response(f"Task {main_task} not found in plan")

    updated = []

    # WORKFLOW ENFORCEMENT: Prevent starting new subtasks while others are in_progress
    if subtasks and status_enum == TaskStatus.IN_PROGRESS:
        for subtask_id in subtasks:
            # Check if OTHER subtasks in this main task are still in_progress
            in_progress_subtasks = [st.id for st in task.subtasks
                                   if st.status == TaskStatus.IN_PROGRESS
                                   and st.id != subtask_id]

            if in_progress_subtasks:
                return error_response(
                    f"⚠️ WORKFLOW VIOLATION: Cannot start subtask {subtask_id} while {in_progress_subtasks} "
                    f"{'is' if len(in_progress_subtasks) == 1 else 'are'} still in_progress.\n\n"
                    f"You need to mark the in_progress task as finished if it's finished. "
                    f"If it's not finished, please complete the task first.\n\n"
                    f"To fix this, call:\n"
                    f"update_tasks(main_task='{main_task}', subtasks={in_progress_subtasks}, "
                    f"status='complete', work_summary='...')\n\n"
                    f"Remember: Complete each subtask BEFORE moving to the next one."
                )

    # Update subtasks if provided
    if subtasks:
        for subtask_id in subtasks:
            subtask = next((st for st in task.subtasks if st.id == subtask_id), None)
            if subtask:
                old_st_status = subtask.status.value
                subtask.status = status_enum

                # Store work summary if marking complete
                if status_enum == TaskStatus.COMPLETE and work_summary:
                    subtask.work_summary = work_summary.strip()
                    updated.append(f"Subtask {subtask_id}: {old_st_status} → {status_enum.value} (with work evidence)")
                else:
                    updated.append(f"Subtask {subtask_id}: {old_st_status} → {status_enum.value}")
            else:
                updated.append(f"⚠️ Subtask {subtask_id} not found in task {main_task}")

        # Auto-update main task status based on subtasks
        if task.subtasks:
            # If any subtask is in progress, mark main task as in progress
            if status_enum == TaskStatus.IN_PROGRESS and task.status == TaskStatus.NOT_STARTED:
                task.status = TaskStatus.IN_PROGRESS
                updated.append(f"✅ Task {main_task}: not started → in progress (subtask started)")

            # If all subtasks are complete, mark main task as complete
            elif all(st.status == TaskStatus.COMPLETE for st in task.subtasks):
                if task.status != TaskStatus.COMPLETE:
                    old_main_status = task.status.value
                    task.status = TaskStatus.COMPLETE
                    task.work_summary = work_summary.strip() if work_summary else "All subtasks completed"
                    updated.append(f"✅ Task {main_task}: {old_main_status} → complete (all subtasks complete)")

    # Update main task only if no subtasks were specified
    else:
        # If marking main task complete, ensure all subtasks are complete
        if status_enum == TaskStatus.COMPLETE and task.subtasks:
            incomplete_subtasks = [st for st in task.subtasks if st.status != TaskStatus.COMPLETE]
            if incomplete_subtasks:
                incomplete_ids = [st.id for st in incomplete_subtasks]
                return error_response(f"Cannot mark task {main_task} as complete: subtasks {incomplete_ids} are not yet complete. Complete all subtasks first.")

        old_status = task.status.value
        task.status = status_enum

        # Store work summary if marking complete
        if status_enum == TaskStatus.COMPLETE and work_summary:
            task.work_summary = work_summary.strip()
            updated.append(f"Task {main_task}: {old_status} → {status_enum.value} (with work evidence)")
        else:
            updated.append(f"Task {main_task}: {old_status} → {status_enum.value}")

    # Log the updated plan state to file
    try:
        write_task_state_to_file(plan, output_dir=output_dir)
    except Exception as e:
        print(f"⚠️  Warning: Failed to write task state to file: {e}")

    return success_response({
        "updated": updated,
        "message": f"Successfully updated {len(updated)} item(s)"
    })


# Tool schema for agent registration
UPDATE_TASKS_DESCRIPTION = """Update the status of tasks and subtasks in your execution plan.

**CRITICAL WORKFLOW - Follow this pattern for EACH subtask:**
1. When you START a subtask: update_tasks(subtasks=["2a"], status="in_progress")
2. Do the work (call tools, analyze data, think deeply)
3. When you FINISH that subtask: update_tasks(subtasks=["2a"], status="complete", work_summary="...")
4. Move to next subtask: update_tasks(subtasks=["2b"], status="in_progress")
5. Repeat

**IMPORTANT - Complete tasks INDIVIDUALLY as you finish them:**
- Complete subtask 2a → mark it "complete" → then start 2b
- Complete subtask 2b → mark it "complete" → then start 2c
- DO NOT batch multiple subtasks with status="in_progress" and say "Completed 2a, 2b, 2c" in work_summary
- Each subtask gets its own "complete" call when you finish it

**Examples:**
✅ CORRECT - Individual completion:
  update_tasks(main_task="2", subtasks=["2a"], status="in_progress")
  [do work on 2a]
  update_tasks(main_task="2", subtasks=["2a"], status="complete", work_summary="Analyzed X using Y tool...")
  update_tasks(main_task="2", subtasks=["2b"], status="in_progress")
  [do work on 2b]
  update_tasks(main_task="2", subtasks=["2b"], status="complete", work_summary="Evaluated Z...")

❌ WRONG - Batching with in_progress:
  update_tasks(main_task="2", subtasks=["2a","2b","2c"], status="in_progress", work_summary="Completed all subtasks...")

**CRITICAL - THE WORK: SECTION:**
When marking tasks as "complete", the work_summary parameter becomes the "Work:" section - this is THE PRIMARY
PLACE where your reasoning, thinking, observations, analysis, decisions, and conclusions are recorded. Be highly analytical and detailed.

The work_summary is NOT just a brief summary. It is the COMPLETE RECORD of your cognitive work and must include:
  - Your analytical reasoning and thought process throughout the task
  - The specific data/tools you used and WHY you chose them
  - ALL observations you made during the analysis (patterns, anomalies, relationships)
  - Key findings, insights, and discoveries
  - Decisions you made and the rationale behind each decision
  - Quantitative results and how you interpreted them
  - Final conclusions drawn from your analysis

Minimum 100 characters required. This section demonstrates you actually performed the analytical work."""

UPDATE_TASKS_PARAMETERS = {
    "type": "object",
    "properties": {
        "main_task": {
            "type": "string",
            "description": "The main task ID to update (e.g., '1', '2', '3')"
        },
        "subtasks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of subtask IDs to update. IMPORTANT: Update ONE subtask at a time when marking complete. Example: ['2a'] when finishing 2a, then ['2b'] when finishing 2b. Do NOT batch multiple subtasks like ['2a','2b','2c'] with status='in_progress'."
        },
        "status": {
            "type": "string",
            "enum": ["not_started", "in_progress", "complete"],
            "description": "New status: 'in_progress' when STARTING work, 'complete' when FINISHED. Mark each subtask 'complete' individually as you finish it, don't batch them."
        },
        "work_summary": {
            "type": "string",
            "description": "REQUIRED when status='complete'. This becomes the 'Work:' section - THE PRIMARY RECORD of your reasoning, thinking, observations, analysis, decisions, and conclusions (min 100 chars). Must include: (1) Your analytical reasoning/thought process, (2) Tools/data used and WHY, (3) ALL observations made, (4) Key findings and insights, (5) Decisions and their rationale, (6) Quantitative results and interpretation, (7) Final conclusions. Example: 'Analyzed portfolio concentration using portfolio_industry_concentration tool. Reasoning: Needed to identify sector-specific risks. Observations: Noted extreme clustering in tech sector with multiple overlapping semiconductor positions. Findings: 65% exposure to Technology sector (NVDA 15%, AAPL 12%, MSFT 12%, others). Semiconductors alone represent 32%. Decision: This concentration level exceeds prudent risk limits. Conclusion: Must diversify into Healthcare and Financials to reduce tech exposure below 40%.'"
        }
    },
    "required": ["main_task", "status"]
}
