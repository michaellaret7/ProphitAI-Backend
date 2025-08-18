"""Task validation system for automatic completion detection."""

from typing import List, Dict, Any, Tuple, Optional, Callable
import re
import json

from .models import Task, TaskStatus, TaskValidation


class TaskValidator:
    """Validates task completion based on evidence and criteria."""
    
    def __init__(self, verbose: bool = False):
        """Initialize task validator.
        
        Args:
            verbose: Whether to print validation messages
        """
        self.verbose = verbose
        self.validators: Dict[str, Callable] = {}
        self._register_default_validators()
    
    def _register_default_validators(self) -> None:
        """Register built-in validation functions."""
        # The validators dictionary is for custom validators that can be called
        # with the signature: (task, tool_executions, observations) -> Tuple[bool, float, str]
        # Built-in validators are called directly in validate_task_completion
        pass
    
    def validate_task_completion(
        self, 
        task: Task, 
        tool_executions: List[Dict] = None,
        observations: List[Any] = None
    ) -> Tuple[bool, float, str]:
        """Validate if a task is complete based on evidence.
        
        Args:
            task: The task to validate
            tool_executions: List of tool execution records
            observations: List of observations/results
            
        Returns:
            Tuple of (is_complete, confidence, explanation)
        """
        tool_executions = tool_executions or []
        observations = observations or []
        
        # If task has no validation criteria, check basic completion
        if not task.validation:
            return self._basic_validation(task)
        
        validation_results = []
        
        # Check required outputs
        if task.validation.required_outputs:
            result = self._validate_outputs(task, task.validation.required_outputs)
            validation_results.append(result)
            if not result[0]:  # If failed, return early
                return result
        
        # Check tool execution sequence
        if task.expected_tool_sequence:
            result = self._validate_tool_sequence(task, tool_executions)
            validation_results.append(result)
        
        # Check success indicators in observations
        if task.validation.success_indicators:
            result = self._validate_indicators(
                task,
                task.validation.success_indicators,
                observations
            )
            validation_results.append(result)
        
        # Run custom validator if specified
        if task.validation.validation_function:
            validator = self.validators.get(task.validation.validation_function)
            if validator:
                result = validator(task, tool_executions, observations)
                validation_results.append(result)
        
        # Aggregate results
        if not validation_results:
            return self._basic_validation(task)
        
        # Calculate overall confidence
        total_confidence = sum(r[1] for r in validation_results) / len(validation_results)
        all_passed = all(r[0] for r in validation_results)
        
        # Check against minimum confidence threshold
        is_complete = all_passed and total_confidence >= task.validation.min_confidence
        
        explanations = [r[2] for r in validation_results if r[2]]
        explanation = "; ".join(explanations) if explanations else "Validation passed"
        
        if self.verbose and is_complete:
            print(f"✅ Task '{task.id}' validated (confidence: {total_confidence:.2f})")
        
        return is_complete, total_confidence, explanation
    
    def _basic_validation(self, task: Task) -> Tuple[bool, float, str]:
        """Basic validation when no criteria specified.
        
        Args:
            task: The task to validate
            
        Returns:
            Validation result tuple
        """
        # Check if task has any outputs or evidence
        has_outputs = bool(task.outputs)
        has_evidence = bool(task.completion_evidence)
        
        if has_outputs or has_evidence:
            return True, 1.0, "Task has outputs/evidence"
        
        # Check if task status indicates completion
        if task.status == TaskStatus.COMPLETED:
            return True, 0.8, "Task marked as completed"
        
        return False, 0.0, "No completion evidence found"
    
    def _validate_outputs(self, task: Task, required_outputs: List[str]) -> Tuple[bool, float, str]:
        """Validate that required outputs exist.
        
        Args:
            task: The task to validate
            required_outputs: List of required output keys
            
        Returns:
            Validation result tuple
        """
        missing = []
        for required in required_outputs:
            if required not in task.outputs:
                missing.append(required)
        
        if missing:
            return False, 0.0, f"Missing required outputs: {', '.join(missing)}"
        
        return True, 1.0, "All required outputs present"
    
    def _validate_tool_sequence(
        self, 
        task: Task, 
        tool_executions: List[Dict]
    ) -> Tuple[bool, float, str]:
        """Validate tool execution sequence.
        
        Args:
            task: The task to validate
            tool_executions: List of tool execution records
            
        Returns:
            Validation result tuple
        """
        if not task.expected_tool_sequence:
            return True, 1.0, "No tool sequence required"
        
        executed_tools = [exec.get('tool_name', '') for exec in tool_executions]
        
        # Check if expected tools were executed in order
        expected_idx = 0
        for tool in executed_tools:
            if expected_idx < len(task.expected_tool_sequence):
                if tool == task.expected_tool_sequence[expected_idx]:
                    expected_idx += 1
        
        if expected_idx == len(task.expected_tool_sequence):
            return True, 1.0, "Tool sequence matched"
        
        completed_ratio = expected_idx / len(task.expected_tool_sequence)
        return False, completed_ratio, f"Tool sequence partially matched ({expected_idx}/{len(task.expected_tool_sequence)})"
    
    def _validate_indicators(
        self,
        task: Task,
        indicators: List[str],
        observations: List[Any]
    ) -> Tuple[bool, float, str]:
        """Check for success indicators in observations.
        
        Args:
            task: The task to validate
            indicators: List of success indicator patterns
            observations: List of observations to check
            
        Returns:
            Validation result tuple
        """
        if not indicators or not observations:
            return True, 0.5, "No indicators to check"
        
        # Convert observations to searchable text
        obs_text = ""
        for obs in observations:
            if isinstance(obs, str):
                obs_text += obs + " "
            elif isinstance(obs, dict):
                obs_text += json.dumps(obs) + " "
            else:
                obs_text += str(obs) + " "
        
        obs_text = obs_text.lower()
        
        # Check how many indicators are present
        found_count = 0
        for indicator in indicators:
            # Treat indicator as regex pattern or literal string
            try:
                if re.search(indicator.lower(), obs_text):
                    found_count += 1
            except re.error:
                # If not valid regex, check as literal
                if indicator.lower() in obs_text:
                    found_count += 1
        
        if found_count == 0:
            return False, 0.0, "No success indicators found"
        
        confidence = found_count / len(indicators)
        
        if confidence >= 0.8:  # Most indicators found
            return True, confidence, f"Found {found_count}/{len(indicators)} success indicators"
        
        return False, confidence, f"Only found {found_count}/{len(indicators)} indicators"
    
    def register_validator(self, name: str, validator_func: Callable) -> None:
        """Register a custom validation function.
        
        Args:
            name: Name of the validator
            validator_func: Function that validates a task
        """
        self.validators[name] = validator_func
        
        if self.verbose:
            print(f"📝 Registered validator: {name}")
    
    def validate_from_tool_result(
        self,
        task: Task,
        tool_name: str,
        tool_result: Any
    ) -> Tuple[bool, float, str]:
        """Quick validation based on a single tool result.
        
        Args:
            task: The task to validate
            tool_name: Name of the tool executed
            tool_result: Result from the tool
            
        Returns:
            Validation result tuple
        """
        # Check if this tool is in the required tools
        if task.required_tools and tool_name in task.required_tools:
            # Store the result
            task.outputs[tool_name] = tool_result
            
            # Check if all required tools have been executed
            if all(tool in task.outputs for tool in task.required_tools):
                return True, 0.9, f"All required tools executed"
        
        # Check for error results
        if isinstance(tool_result, str) and 'error' in tool_result.lower():
            return False, 0.0, f"Tool {tool_name} returned error"
        
        # Check if result contains success indicators
        if task.validation and task.validation.success_indicators:
            result_text = str(tool_result).lower()
            for indicator in task.validation.success_indicators:
                if indicator.lower() in result_text:
                    return True, 0.8, f"Found success indicator: {indicator}"
        
        # Default: not enough evidence yet
        return False, 0.3, "Awaiting more evidence"
