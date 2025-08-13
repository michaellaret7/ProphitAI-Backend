"""Checklist management functionality for BaseAgent."""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class ChecklistManager:
    """Manages checklist tracking for agent task planning and progress."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.checklist_path = Path(__file__).parent.parent / "agent_output" / "agent_checklist.json"
        self.checklist_items: List[Dict[str, Any]] = []
        self.checklist_enabled = False
        
        # Clear the checklist file at start
        try:
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception:
            pass
    
    def parse_plan_to_checklist(self, content: str, trace_length: int) -> bool:
        """Parse the agent's JSON plan into checklist items."""
        try:
            # Look for JSON object in the content
            import re
            json_match = re.search(r'\{.*"plan".*\}', content, re.DOTALL)
            if not json_match:
                return False
            
            plan_data = json.loads(json_match.group(0))
            if "plan" not in plan_data:
                return False
            
            # Convert plan to checklist items
            self.checklist_items = []
            for item in plan_data["plan"]:
                self.checklist_items.append({
                    "step": item.get("step", len(self.checklist_items) + 1),
                    "description": item.get("desc", ""),
                    "status": "pending",
                    "started_at_iteration": None,
                    "completed_at_iteration": None
                })
            
            self.checklist_enabled = True
            self.save_checklist(trace_length)
            
            if self.verbose:
                print(f"📋 Checklist created with {len(self.checklist_items)} items")
            
            return True
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to parse plan: {e}")
            return False
    
    def save_checklist(self, trace_length: int) -> None:
        """Save current checklist to JSON file."""
        if not self.checklist_enabled:
            return
        
        try:
            checklist_data = {
                "created_at": datetime.now().isoformat(),
                "current_iteration": trace_length,
                "items": self.checklist_items
            }
            
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump(checklist_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save checklist: {e}")
    
    def load_checklist(self) -> None:
        """Load checklist from JSON file if it exists."""
        try:
            if self.checklist_path.exists():
                with open(self.checklist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.checklist_items = data.get("items", [])
                    self.checklist_enabled = len(self.checklist_items) > 0
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load checklist: {e}")
    
    def update_checklist_progress(self, iteration: int, trace_length: int) -> None:
        """Update checklist based on recent tool calls."""
        if not self.checklist_enabled or not self.checklist_items:
            return
        
        # If no task is in progress, start the first pending one
        has_in_progress = any(item["status"] == "in_progress" for item in self.checklist_items)
        if not has_in_progress:
            for item in self.checklist_items:
                if item["status"] == "pending":
                    item["status"] = "in_progress"
                    item["started_at_iteration"] = iteration
                    break
        
        self.save_checklist(trace_length)
    
    def parse_progress_from_response(self, content: str, iteration: int, trace_length: int) -> bool:
        """Parse agent response for task completion indicators."""
        if not self.checklist_enabled or not self.checklist_items or not content:
            return False
        
        content_lower = content.lower()
        updated = False
        
        # More flexible patterns for task completion
        completion_patterns = [
            # Direct completion statements
            r"task\s+(\d+)\s+(?:is\s+)?(?:complete|completed|done|finished)",
            r"step\s+(\d+)\s+(?:is\s+)?(?:complete|completed|done|finished)",
            r"completed?\s+(?:task|step)\s+(\d+)",
            r"finished\s+(?:task|step)\s+(\d+)",
            r"✓\s*(?:task|step)\s+(\d+)",  # Checkmark patterns
            r"(?:task|step)\s+(\d+)\s*✓",
            
            # Moving/proceeding patterns (mark previous as complete)
            r"moving\s+(?:on\s+)?to\s+(?:task|step)\s+(\d+)",
            r"proceeding\s+to\s+(?:task|step)\s+(\d+)",
            r"now\s+(?:on|at|working\s+on)\s+(?:task|step)\s+(\d+)",
            r"starting\s+(?:task|step)\s+(\d+)",
        ]
        
        import re
        for pattern in completion_patterns:
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                task_num = int(match.group(1))
                
                # Handle transition patterns - mark previous task as complete
                if any(keyword in pattern for keyword in ["moving", "proceeding", "now", "starting"]):
                    # Find the current in-progress task
                    for item in self.checklist_items:
                        if item["status"] == "in_progress":
                            item["status"] = "completed"
                            item["completed_at_iteration"] = iteration
                            updated = True
                            break
                    
                    # Start the specified task
                    for item in self.checklist_items:
                        if item.get("step") == task_num and item["status"] == "pending":
                            item["status"] = "in_progress"
                            item["started_at_iteration"] = iteration
                            break
                else:
                    # Direct completion - mark specified task as complete
                    for item in self.checklist_items:
                        if item.get("step") == task_num and item["status"] == "in_progress":
                            item["status"] = "completed"
                            item["completed_at_iteration"] = iteration
                            updated = True
                            
                            # Start the next pending task
                            for next_item in self.checklist_items:
                                if next_item["status"] == "pending":
                                    next_item["status"] = "in_progress"
                                    next_item["started_at_iteration"] = iteration
                                    break
                            break
        
        # Log if no patterns matched but verbose mode is on
        if not updated and self.verbose and any(word in content_lower for word in ["complete", "done", "finished", "task", "step"]):
            print(f"⚠️ Potential task completion not detected in: {content[:100]}...")
        
        if updated:
            self.save_checklist(trace_length)
            
        return updated
    
    def is_checklist_complete(self) -> bool:
        """Check if all checklist items are completed."""
        if not self.checklist_enabled or not self.checklist_items:
            return True  # No checklist means nothing to block
        
        # All items must be completed
        return all(item.get("status") == "completed" for item in self.checklist_items)
    
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending or in-progress tasks."""
        if not self.checklist_enabled or not self.checklist_items:
            return []
        
        incomplete = []
        for item in self.checklist_items:
            if item.get("status") != "completed":
                incomplete.append({
                    "step": item.get("step", "?"),
                    "description": item.get("description", ""),
                    "status": item.get("status", "pending")
                })
        return incomplete
    
    def get_stuck_tasks(self, current_iteration: int, threshold: int = 5) -> List[Dict[str, Any]]:
        """Get tasks stuck in-progress for too long."""
        if not self.checklist_enabled or not self.checklist_items:
            return []
        
        stuck = []
        for item in self.checklist_items:
            if (item.get("status") == "in_progress" and 
                item.get("started_at_iteration") and 
                current_iteration - item["started_at_iteration"] >= threshold):
                stuck.append({
                    "step": item.get("step", "?"),
                    "description": item.get("description", ""),
                    "iterations_stuck": current_iteration - item["started_at_iteration"]
                })
        return stuck
    
    def get_checklist_prompt(self, iteration: int) -> str:
        """Generate combined analysis direction + checklist status prompt."""
        # Check if checklist is complete
        checklist_complete = self.is_checklist_complete()
        
        # Base analysis direction changes based on checklist status
        if checklist_complete:
            base_prompt = (
                "Analyze the latest tool observations. Based on your analysis, either: "
                "(a) call another tool to continue iterating, or "
                "(b) produce a FINAL ANSWER preceded by 'Final Answer:' (all checklist items are complete)."
            )
        else:
            base_prompt = (
                "Analyze the latest tool observations and continue working through your checklist. "
                "You MUST complete all checklist items before producing a Final Answer. "
                "Call the appropriate tool to continue your task."
            )
        
        # If no checklist, return just the base prompt
        if not self.checklist_enabled or not self.checklist_items:
            return base_prompt
        
        # Build checklist status display
        status_lines = ["\n\n📋 Checklist Progress (Iteration {}):".format(iteration)]
        
        current_task = None
        for item in self.checklist_items:
            step_num = item.get("step", "?")
            desc = item.get("description", "")
            status = item.get("status", "pending")
            
            if status == "completed":
                status_lines.append(f"[✓ DONE] Step {step_num}: {desc}")
            elif status == "in_progress":
                status_lines.append(f"→ Step {step_num}: {desc} (IN PROGRESS)")
                current_task = step_num
            else:
                status_lines.append(f"  Step {step_num}: {desc}")
        
        # Count progress
        completed = sum(1 for item in self.checklist_items if item["status"] == "completed")
        total = len(self.checklist_items)
        status_lines.append(f"\nProgress: {completed}/{total} steps completed")
        
        # Add task completion instructions
        if current_task:
            status_lines.append(
                f"\n📌 When you complete Step {current_task}, indicate this by saying "
                f"'Step {current_task} complete' or 'Task {current_task} done' in your response."
            )
        
        # Add reminder based on completion status
        if checklist_complete:
            status_lines.append("\n✅ All tasks complete! You may now produce your Final Answer.")
        else:
            remaining = len(self.get_incomplete_tasks())
            status_lines.append(f"\n⚠️ {remaining} tasks remaining. Continue working through your checklist.")
            status_lines.append("Remember: You CANNOT produce a Final Answer until ALL tasks are complete.")
        
        # Combine base prompt with checklist status
        return base_prompt + "\n".join(status_lines)
