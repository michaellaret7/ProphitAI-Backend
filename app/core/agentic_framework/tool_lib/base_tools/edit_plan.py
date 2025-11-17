from typing import Optional, Literal
import re
from app.core.agentic_framework.base_agent.utils.models import Plan, TaskStatus, PlanTask, PlanSubtask

TaskAction = Literal["add", "drop", "edit"]
TaskType = Literal["main_task", "subtask"]


def _parse_task_id(task_id: str) -> tuple[str, str, str]:
    """
    Parse a task ID into prefix, suffix, and suffix type.

    Examples:
        "2a" -> ("2", "a", "letter")
        "2b" -> ("2", "b", "letter")
        "task_1" -> ("task_", "1", "number")
        "3" -> ("", "3", "number")

    Returns:
        tuple of (prefix, suffix, suffix_type)
    """
    # Try to match pattern: prefix + letter/number suffix
    match = re.match(r'^(.*)([a-z])$', task_id, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2), "letter"

    match = re.match(r'^(.*)(\d+)$', task_id)
    if match:
        return match.group(1), match.group(2), "number"

    # If no pattern found, treat entire string as suffix
    return "", task_id, "unknown"


def _increment_suffix(suffix: str, suffix_type: str) -> str:
    """
    Increment a task suffix.

    Examples:
        "a" (letter) -> "b"
        "z" (letter) -> "aa"
        "1" (number) -> "2"
    """
    if suffix_type == "letter":
        # Handle letter incrementation
        if len(suffix) == 1:
            if suffix.lower() == 'z':
                return 'aa' if suffix.islower() else 'AA'
            return chr(ord(suffix) + 1)
        else:
            # Multi-letter case (aa -> ab, az -> ba, etc.)
            # Simple implementation: just add one to the last char
            return suffix[:-1] + chr(ord(suffix[-1]) + 1)
    elif suffix_type == "number":
        return str(int(suffix) + 1)
    else:
        # Unknown type, append "_1" or increment existing number
        return suffix + "_1"


def _rename_subsequent_tasks(subtasks: list[PlanSubtask], start_index: int, new_task_id: str) -> None:
    """
    Rename all subtasks from start_index onwards by incrementing their suffixes.

    Args:
        subtasks: List of subtasks to modify in place
        start_index: Index to start renaming from
        new_task_id: The task ID being inserted (used to determine naming pattern)
    """
    if start_index >= len(subtasks):
        return

    # Parse the new task ID to understand the naming pattern
    prefix, suffix, suffix_type = _parse_task_id(new_task_id)

    # Check if existing tasks follow the same pattern
    current_suffix = suffix
    for i in range(start_index, len(subtasks)):
        existing_prefix, _, existing_type = _parse_task_id(subtasks[i].id)

        # Only rename if the pattern matches
        if existing_prefix == prefix and existing_type == suffix_type:
            current_suffix = _increment_suffix(current_suffix, suffix_type)
            subtasks[i].id = prefix + current_suffix
        else:
            # Pattern doesn't match, stop renaming
            break


def edit_plan(
    plan: Plan,
    action: TaskAction,
    task_type: TaskType,
    task_id: str,
    parent_task_id: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[int] = None,
    insert_position: Optional[int] = None
) -> Plan:
    """
    Edit the plan by adding, dropping, or modifying tasks.

    Args:
        plan: The Plan object to edit
        action: The action to perform (add, drop, edit)
        task_type: Whether to operate on main_task or subtask
        task_id: The ID of the task to operate on
        parent_task_id: Required when adding a subtask - the ID of the parent main task
        description: New or updated description (used for add and edit)
        status: New status (used for edit)
        priority: New priority (used for edit)
        insert_position: Position to insert the task (0-indexed). If None, appends to end.
                        If position > list length, appends to end. Used only for add action.

    Returns:
        The updated Plan object
    """

    if not plan or not getattr(plan, "tasks", None):
        raise ValueError("No plan available")

    # Handle add action
    if action == "add":
        if not description:
            raise ValueError("description is required when adding a task")

        if task_type == "main_task":
            # Add a new main task
            new_task = PlanTask(
                id=task_id,
                description=description,
                priority=priority or 0,
                subtasks=[]
            )

            # Insert at specified position or append to end
            if insert_position is not None and 0 <= insert_position <= len(plan.tasks):
                plan.tasks.insert(insert_position, new_task)
            else:
                plan.tasks.append(new_task)

        elif task_type == "subtask":
            # Add a new subtask to a parent task
            if not parent_task_id:
                raise ValueError("parent_task_id is required when adding a subtask")

            # Find the parent task
            parent_task = next((t for t in plan.tasks if t.id == parent_task_id), None)
            if not parent_task:
                raise ValueError(f"Parent task with id '{parent_task_id}' not found")

            # Add the subtask
            new_subtask = PlanSubtask(
                id=task_id,
                description=description,
                status=status or TaskStatus.NOT_STARTED
            )

            # Insert at specified position or append to end
            if insert_position is not None and 0 <= insert_position <= len(parent_task.subtasks):
                parent_task.subtasks.insert(insert_position, new_subtask)
                # Rename all subsequent subtasks to maintain sequential numbering
                _rename_subsequent_tasks(parent_task.subtasks, insert_position + 1, task_id)
            else:
                parent_task.subtasks.append(new_subtask)

    # Handle drop action
    elif action == "drop":
        if task_type == "main_task":
            # Remove the main task
            plan.tasks = [t for t in plan.tasks if t.id != task_id]

        elif task_type == "subtask":
            # Find and remove the subtask from its parent
            for main_task in plan.tasks:
                original_count = len(main_task.subtasks)
                main_task.subtasks = [st for st in main_task.subtasks if st.id != task_id]
                if len(main_task.subtasks) < original_count:
                    break  # Subtask found and removed

    # Handle edit action
    elif action == "edit":
        if task_type == "main_task":
            # Find and edit the main task
            main_task = next((t for t in plan.tasks if t.id == task_id), None)
            if not main_task:
                raise ValueError(f"Main task with id '{task_id}' not found")

            # Update fields if provided
            if description is not None:
                main_task.description = description
            if priority is not None:
                main_task.priority = priority

        elif task_type == "subtask":
            # Find and edit the subtask
            subtask_found = False
            for main_task in plan.tasks:
                for subtask in main_task.subtasks:
                    if subtask.id == task_id:
                        # Update fields if provided
                        if description is not None:
                            subtask.description = description
                        if status is not None:
                            subtask.status = status
                        subtask_found = True
                        break
                if subtask_found:
                    break

            if not subtask_found:
                raise ValueError(f"Subtask with id '{task_id}' not found")

    return plan

def create_edit_plan_wrapper(agent):
    """
    Create a wrapper function for edit_plan that injects agent.plan.

    This wrapper:
    - Injects the agent's plan object
    - Updates agent.plan with the modified version
    - Logs the updated plan to task_state.yaml
    - Returns YAML-formatted success/error response

    Args:
        agent: The BaseAgent instance

    Returns:
        Wrapped function that can be registered as a tool
    """
    from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
    from app.core.agentic_framework.base_agent.logging.task_state_logger import write_task_state_to_file


    def _edit_plan_wrapper(action, task_type, task_id, parent_task_id=None, description=None, status=None, priority=None, insert_position=None, **_kwargs):
        """Wrapper to handle edit_plan execution and return proper response."""
        try:
            # Call edit_plan and update agent.plan with the result
            updated_plan = edit_plan(
                plan=agent.plan,
                action=action,
                task_type=task_type,
                task_id=task_id,
                parent_task_id=parent_task_id,
                description=description,
                status=status,
                priority=priority,
                insert_position=insert_position
            )
            # Update the agent's plan with the modified version
            agent.plan = updated_plan

            # Log the updated plan state to file
            try:
                write_task_state_to_file(updated_plan, output_dir=getattr(agent, "output_dir", None))
            except Exception as e:
                print(f"⚠️  Warning: Failed to write task state to file: {e}")

            # Build success message
            action_messages = {
                "add": f"Added {task_type} '{task_id}'",
                "drop": f"Removed {task_type} '{task_id}'",
                "edit": f"Updated {task_type} '{task_id}'"
            }
            message = action_messages.get(action, f"Performed {action} on {task_type} '{task_id}'")

            if action == "add" and insert_position is not None and task_type == "subtask":
                message += f" at position {insert_position} (subsequent tasks auto-renamed)"

            return success_response( {
                    "message": message,
                    "action": action,
                    "task_id": task_id
                })
        except Exception as e:
            return error_response(e)

    return _edit_plan_wrapper

# Tool schema for agent registration
EDIT_PLAN_DESCRIPTION = """Dynamically modify your execution plan by adding, removing, or editing tasks and subtasks.

Use this tool to adapt your plan as you gain new information or encounter unexpected situations:
- **ADD tasks**: Insert new main tasks or subtasks into your plan at any position
- **DROP tasks**: Remove tasks that are no longer relevant or necessary
- **EDIT tasks**: Update task descriptions, priorities, or statuses

**INTELLIGENT TASK INSERTION:**
When adding a subtask with insert_position, the tool AUTOMATICALLY renames all subsequent subtasks to maintain
sequential numbering. For example, if Task 2 has subtasks ["2a", "2b", "2c"] and you insert a new "2b" at
position 1, the tool will:
  - Insert your new "2b" at position 1
  - Automatically rename old "2b" → "2c"
  - Automatically rename old "2c" → "2d"
  Result: ["2a", "2b (new)", "2c", "2d"]

**WHEN TO USE:**
- Discovered a new subtask needed for a complex main task → ADD it at the right position
- Realized a task is no longer relevant to the goal → DROP it
- Need to update task details or priority → EDIT it
- Found a critical subtask that should come before existing ones → ADD with insert_position=0

**KEY PARAMETERS:**
- action: "add", "drop", or "edit"
- task_type: "main_task" or "subtask"
- task_id: The ID of the task (e.g., "2", "2b", "task_3")
- insert_position: (Optional) 0-indexed position for ADD operations. Triggers automatic renaming of subsequent tasks.

**EXAMPLES:**

# Add a new main task at the end
edit_plan(plan, action="add", task_type="main_task", task_id="4",
         description="Perform final validation", priority=1)

# Add a critical subtask at the beginning of Task 2
edit_plan(plan, action="add", task_type="subtask", parent_task_id="2",
         task_id="2a", description="Validate data inputs first", insert_position=0)
# Result: Existing "2a", "2b", "2c" become "2b", "2c", "2d"

# Insert a new subtask between existing ones
edit_plan(plan, action="add", task_type="subtask", parent_task_id="3",
         task_id="3c", description="Additional analysis step", insert_position=2)

# Remove an unnecessary subtask
edit_plan(plan, action="drop", task_type="subtask", task_id="5b")

# Update a main task's description and priority
edit_plan(plan, action="edit", task_type="main_task", task_id="1",
         description="Updated task description", priority=3)

# Update a subtask's status
edit_plan(plan, action="edit", task_type="subtask", task_id="2c",
         status="in_progress")"""

EDIT_PLAN_PARAMETERS = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["add", "drop", "edit"],
            "description": "The action to perform: 'add' to create new tasks, 'drop' to remove tasks, 'edit' to modify existing tasks"
        },
        "task_type": {
            "type": "string",
            "enum": ["main_task", "subtask"],
            "description": "Whether to operate on a main_task or subtask"
        },
        "task_id": {
            "type": "string",
            "description": "The ID of the task to operate on (e.g., '2', '2b', 'task_3'). For add operations, this is the ID for the new task."
        },
        "parent_task_id": {
            "type": "string",
            "description": "REQUIRED when adding a subtask - the ID of the parent main task (e.g., '2' for adding subtask '2b')"
        },
        "description": {
            "type": "string",
            "description": "Task description. REQUIRED for action='add'. Optional for action='edit' to update description."
        },
        "status": {
            "type": "string",
            "enum": ["not_started", "in_progress", "complete"],
            "description": "Status for subtasks. Only used with action='edit' on task_type='subtask'."
        },
        "priority": {
            "type": "integer",
            "description": "Priority level for main tasks (higher = more important). Used with action='add' or action='edit' on task_type='main_task'."
        },
        "insert_position": {
            "type": "integer",
            "description": "0-indexed position to insert the task. Only used with action='add'. If omitted, appends to end. When specified for subtasks, automatically renames all subsequent subtasks to maintain sequential numbering (e.g., inserting '2b' at position 1 renames old '2b'→'2c', '2c'→'2d')."
        }
    },
    "required": ["action", "task_type", "task_id"]
}

# Tool export for agent registration
EDIT_PLAN_TOOL = {
    "name": "edit_plan",
    "description": EDIT_PLAN_DESCRIPTION,
    "parameters": EDIT_PLAN_PARAMETERS,
    "function": edit_plan
}