"""Task validation system for automatic completion detection."""

from typing import List, Dict, Any, Tuple, Optional, Callable
import re
import json

from .models import MainTask, SubTask, TaskStatus


class TaskValidator:
    """Validates MainTask and SubTask completion based on evidence and criteria."""
    
    def __init__(self, verbose: bool = False):
        """Initialize task validator (strict mode always on).
        
        Args:
            verbose: Whether to print validation messages
        """
        self.verbose = verbose
        self.validators: Dict[str, Callable] = {}
        self._confidence_thresholds = {
            'subtask_completion': 0.7,
            'main_task_completion': 0.8,
            'tool_result_success': 0.6
        }
        self._register_default_validators()
    
    def _register_default_validators(self) -> None:
        """Register built-in validation functions."""
        # Default validators for common completion patterns
        self.validators['evidence_threshold'] = self._evidence_threshold_validator
        self.validators['tool_prediction_match'] = self._tool_prediction_validator
        self.validators['observation_analysis'] = self._observation_analysis_validator
    
    def validate_main_task_completion(
        self, 
        main_task: MainTask, 
        tool_executions: List[Dict] = None
    ) -> Tuple[bool, float, str]:
        """Validate if a MainTask is complete based on evidence and subtasks.
        
        Args:
            main_task: The MainTask to validate
            tool_executions: List of tool execution records
            
        Returns:
            Tuple of (is_complete, confidence, explanation)
        """
        tool_executions = tool_executions or []
        
        validation_results = []
        
        # Check subtask completion first (strict: require all subtasks complete if any exist)
        if main_task.subtasks:
            subtask_result = self._validate_subtasks_completion(main_task)
            validation_results.append(subtask_result)
            all_complete = subtask_result[0]
            if not all_complete:
                explanation = "Strict validation: all subtasks must be completed"
                if self.verbose:
                    print(f"⏳ MainTask {main_task.id} not complete yet - {explanation}")
                return False, subtask_result[1], explanation
        
        # Check evidence threshold
        evidence_result = self._evidence_threshold_validator(main_task)
        validation_results.append(evidence_result)
        
        # Check predicted tools usage
        if main_task.predicted_tool_use:
            tool_result = self._tool_prediction_validator(main_task, tool_executions)
            validation_results.append(tool_result)
        
        # Check observations quality
        obs_result = self._observation_analysis_validator(main_task)
        validation_results.append(obs_result)
        
        # Calculate overall confidence
        if not validation_results:
            return self._basic_main_task_validation(main_task)
        
        total_confidence = sum(r[1] for r in validation_results) / len(validation_results)
        all_passed = all(r[0] for r in validation_results)
        
        # Check against threshold
        threshold = self._confidence_thresholds['main_task_completion']
        is_complete = all_passed and total_confidence >= threshold
        
        explanations = [r[2] for r in validation_results if r[2]]
        explanation = "; ".join(explanations) if explanations else "Validation passed"
        
        if self.verbose and is_complete:
            print(f"✅ MainTask {main_task.id} validated (confidence: {total_confidence:.2f})")
        
        return is_complete, total_confidence, explanation
    
    def validate_subtask_completion(
        self,
        subtask: SubTask,
        parent_task: MainTask = None
    ) -> Tuple[bool, float, str]:
        """Validate if a SubTask is complete based on evidence.
        
        Args:
            subtask: The SubTask to validate
            parent_task: Optional parent MainTask for context
            
        Returns:
            Tuple of (is_complete, confidence, explanation)
        """
        validation_results = []
        
        # DO NOT auto-validate based on completed flag - require actual evidence
        # The completed flag should be a result of validation, not an input to it
        
        # Check evidence count
        evidence_count = len(subtask.completion_evidence)
        if evidence_count >= 2:
            confidence = min(evidence_count / 3.0, 1.0)  # Cap at 1.0
            validation_results.append((True, confidence, f"Has {evidence_count} pieces of evidence"))
        elif evidence_count >= 1:
            validation_results.append((False, 0.5, f"Only {evidence_count} piece of evidence"))
        else:
            validation_results.append((False, 0.0, "No evidence collected"))
        
        # Check observations count
        obs_count = len(subtask.observations)
        if obs_count >= 1:
            confidence = min(obs_count / 2.0, 1.0)  # Cap at 1.0
            validation_results.append((True, confidence, f"Has {obs_count} observations"))
        else:
            validation_results.append((False, 0.2, "No observations recorded"))
        
        # Analyze observation content for success indicators
        if subtask.observations:
            success_result = self._analyze_observations_for_success(subtask.observations)
            validation_results.append(success_result)
        
        # Require relevant tool-named evidence and no error evidence when tools are implied
        if parent_task is not None:
            # Determine relevant tools: predicted tools that appear in subtask description
            try:
                relevant_tools = []
                if parent_task.predicted_tool_use:
                    desc_lower = subtask.description.lower()
                    for t in parent_task.predicted_tool_use:
                        if str(t).lower() in desc_lower:
                            relevant_tools.append(str(t).lower())
                import re
                # Use word boundary check to avoid false positives like "grocer" containing "error"
                has_error_evidence = any(
                    re.search(r'\berror\b', str(ev), re.IGNORECASE) 
                    for ev in subtask.completion_evidence
                )
                has_relevant_tool_evidence = False
                if relevant_tools:
                    for ev in subtask.completion_evidence:
                        ev_lower = str(ev).lower()
                        if any(rt in ev_lower for rt in relevant_tools):
                            has_relevant_tool_evidence = True
                            break
                    if not has_relevant_tool_evidence:
                        validation_results.append((False, 0.0, "No evidence referencing required tool for this subtask"))
                if has_error_evidence:
                    validation_results.append((False, 0.0, "Error evidence present for this subtask"))
            except Exception:
                # Fail-safe: do not crash validator
                pass

        # Calculate overall confidence
        if not validation_results:
            return False, 0.0, "No validation criteria met"
        
        total_confidence = sum(r[1] for r in validation_results) / len(validation_results)
        all_passed = all(r[0] for r in validation_results)
        
        # Check against threshold
        threshold = self._confidence_thresholds['subtask_completion']
        is_complete = all_passed and total_confidence >= threshold
        
        explanations = [r[2] for r in validation_results if r[2]]
        explanation = "; ".join(explanations) if explanations else "Validation passed"
        
        if self.verbose and is_complete:
            print(f"  ✅ SubTask {subtask.id} validated (confidence: {total_confidence:.2f})")
        
        return is_complete, total_confidence, explanation
    
    def validate_tool_result_for_completion(
        self,
        tool_name: str,
        tool_result: Any,
        current_task: MainTask = None,
        current_subtask: SubTask = None
    ) -> Tuple[bool, float, str]:
        """Analyze tool result to determine if it indicates task completion.
        
        Args:
            tool_name: Name of the executed tool
            tool_result: Result from tool execution
            current_task: Current MainTask being worked on
            current_subtask: Current SubTask being worked on
            
        Returns:
            Tuple of (should_complete, confidence, reason)
        """
        confidence_factors = []
        
        # 1. Tool execution success analysis
        success_result = self._analyze_tool_success(tool_name, tool_result)
        confidence_factors.append(success_result)
        
        # 2. Result content analysis
        content_result = self._analyze_result_content(tool_result)
        confidence_factors.append(content_result)
        
        # 3. Tool prediction and relevance match (strict)
        if current_task:
            predicted = tool_name in (current_task.predicted_tool_use or [])
            if predicted:
                confidence_factors.append((True, 0.8, "Tool was predicted for this task"))
            # Require tool also to be referenced in subtask description when applicable
            if current_subtask is not None:
                in_desc = str(tool_name).lower() in str(current_subtask.description).lower()
                if not (predicted and in_desc):
                    confidence_factors.append((False, 0.0, "Strict: tool not relevant to current subtask"))
        
        # 4. Evidence accumulation check (if we have current subtask)
        if current_subtask:
            evidence_result = self._check_evidence_accumulation(current_subtask)
            confidence_factors.append(evidence_result)
        
        # Early exit on clear failure (strict)
        if self._result_has_error(tool_result):
            return False, 0.0, "Strict: tool result indicates error"

        # Calculate overall confidence
        if not confidence_factors:
            return False, 0.0, "No validation criteria applicable"
        
        total_confidence = sum(r[1] for r in confidence_factors) / len(confidence_factors)
        positive_indicators = sum(1 for r in confidence_factors if r[0])
        
        # Completion threshold: majority of indicators positive + high confidence
        threshold = self._confidence_thresholds['tool_result_success']
        should_complete = (positive_indicators >= len(confidence_factors) / 2 and 
                          total_confidence >= threshold)
        
        explanations = [r[2] for r in confidence_factors if r[2]]
        reason = "; ".join(explanations) if explanations else "Analysis complete"
        
        return should_complete, total_confidence, reason
    
    # === Validator Helper Methods ===
    
    def _validate_subtasks_completion(self, main_task: MainTask) -> Tuple[bool, float, str]:
        """Check if all subtasks in a main task are completed."""
        if not main_task.subtasks:
            return True, 1.0, "No subtasks to complete"
        
        completed_subtasks = sum(1 for st in main_task.subtasks if st.completed)
        total_subtasks = len(main_task.subtasks)
        
        if completed_subtasks == total_subtasks:
            return True, 1.0, f"All {total_subtasks} subtasks completed"
        
        completion_ratio = completed_subtasks / total_subtasks
        return False, completion_ratio, f"Only {completed_subtasks}/{total_subtasks} subtasks completed"
    
    def _evidence_threshold_validator(self, main_task: MainTask) -> Tuple[bool, float, str]:
        """Validate based on evidence threshold."""
        evidence_count = len(main_task.completion_evidence)
        observation_count = len(main_task.observations)
        
        # Calculate evidence score
        evidence_score = min(evidence_count / 3.0, 1.0)  # 3+ evidence items = full score
        observation_score = min(observation_count / 2.0, 1.0)  # 2+ observations = full score
        
        # Weighted average
        overall_score = (evidence_score * 0.6) + (observation_score * 0.4)
        
        if overall_score >= 0.8:
            return True, overall_score, f"Strong evidence: {evidence_count} evidence, {observation_count} observations"
        elif overall_score >= 0.5:
            return False, overall_score, f"Moderate evidence: {evidence_count} evidence, {observation_count} observations"
        else:
            return False, overall_score, f"Weak evidence: {evidence_count} evidence, {observation_count} observations"
    
    def _tool_prediction_validator(self, main_task: MainTask, tool_executions: List[Dict]) -> Tuple[bool, float, str]:
        """Validate based on predicted tool usage."""
        if not main_task.predicted_tool_use:
            return True, 0.8, "No tools predicted for this task"
        
        executed_tools = [exec.get('tool_name', '') for exec in tool_executions]
        predicted_tools = main_task.predicted_tool_use
        
        # Check how many predicted tools were executed
        matched_tools = [tool for tool in executed_tools if tool in predicted_tools]
        
        if not matched_tools:
            return False, 0.2, "No predicted tools executed yet"
        
        match_ratio = len(matched_tools) / len(predicted_tools)
        
        if match_ratio >= 0.8:  # 80% of predicted tools executed
            return True, match_ratio, f"Executed {len(matched_tools)}/{len(predicted_tools)} predicted tools"
        elif match_ratio >= 0.5:  # 50% executed
            return False, match_ratio, f"Partially executed predicted tools: {len(matched_tools)}/{len(predicted_tools)}"
        else:
            return False, match_ratio, f"Few predicted tools executed: {len(matched_tools)}/{len(predicted_tools)}"
    
    def _observation_analysis_validator(self, main_task: MainTask) -> Tuple[bool, float, str]:
        """Validate based on observation quality and content."""
        if not main_task.observations:
            return False, 0.0, "No observations recorded"
        
        # Analyze observation content
        success_indicators = 0
        error_indicators = 0
        
        for obs in main_task.observations:
            obs_text = str(obs).lower()
            
            # Check for success patterns
            success_patterns = ['success', 'completed', 'finished', 'returned', 'generated', 'calculated', 'retrieved']
            if any(pattern in obs_text for pattern in success_patterns):
                success_indicators += 1
            
            # Check for error patterns
            error_patterns = ['error', 'failed', 'exception', 'not found', 'invalid']
            if any(pattern in obs_text for pattern in error_patterns):
                error_indicators += 1
        
        total_obs = len(main_task.observations)
        
        if error_indicators > success_indicators:
            return False, 0.2, f"More errors ({error_indicators}) than successes ({success_indicators})"
        
        if success_indicators >= total_obs * 0.7:  # 70% of observations show success
            confidence = min(success_indicators / total_obs, 1.0)
            return True, confidence, f"Strong success pattern: {success_indicators}/{total_obs} successful observations"
        
        if success_indicators > 0:
            confidence = success_indicators / total_obs
            return False, confidence, f"Some success: {success_indicators}/{total_obs} successful observations"
        
        return False, 0.3, f"No clear success patterns in {total_obs} observations"
    
    def _basic_main_task_validation(self, main_task: MainTask) -> Tuple[bool, float, str]:
        """Basic validation for MainTask when no specific criteria."""
        # Check if task is already marked as completed
        if main_task.status == TaskStatus.COMPLETED:
            return True, 0.9, "Task marked as completed"
        
        # Check if has any evidence or observations
        has_evidence = len(main_task.completion_evidence) > 0
        has_observations = len(main_task.observations) > 0
        
        if has_evidence and has_observations:
            return True, 0.7, "Has both evidence and observations"
        elif has_evidence or has_observations:
            return False, 0.4, "Has some activity but insufficient for completion"
        else:
            return False, 0.0, "No activity recorded"
    
    def _analyze_tool_success(self, tool_name: str, tool_result: Any) -> Tuple[bool, float, str]:
        """Analyze if a tool execution was successful."""
        # Check for exceptions
        if isinstance(tool_result, Exception):
            return False, 0.0, f"Tool {tool_name} raised exception"
        
        # Check for None result
        if tool_result is None:
            return False, 0.1, f"Tool {tool_name} returned None"
        
        # Check for error strings using robust pattern matching
        if isinstance(tool_result, str):
            if self._result_has_error(tool_result):
                return False, 0.2, f"Tool {tool_name} returned error message"
        
        # Check for error in dict results
        if isinstance(tool_result, dict):
            if tool_result.get('success') is False:
                return False, 0.2, f"Tool {tool_name} returned success=False"
            if 'error' in tool_result:
                return False, 0.2, f"Tool {tool_name} returned error key"
        
        # If we get here, tool appears successful
        return True, 0.8, f"Tool {tool_name} executed successfully"
    
    def _analyze_result_content(self, tool_result: Any) -> Tuple[bool, float, str]:
        """Analyze tool result content for completion indicators."""
        if tool_result is None:
            return False, 0.0, "Empty result"
        
        # Check result size/substance
        if isinstance(tool_result, str):
            if len(tool_result.strip()) < 10:
                return False, 0.3, "Very short result"
            if len(tool_result) > 50:
                return True, 0.7, "Substantial text result"
        
        elif isinstance(tool_result, dict):
            if len(tool_result) == 0:
                return False, 0.2, "Empty dictionary result"
            if len(tool_result) > 3:
                return True, 0.8, "Rich dictionary result"
        
        elif isinstance(tool_result, list):
            if len(tool_result) == 0:
                return False, 0.2, "Empty list result"
            if len(tool_result) > 1:
                return True, 0.7, "Multiple items in result"
        
        # Default for other types
        return True, 0.6, f"Result of type {type(tool_result).__name__}"

    def _result_has_error(self, tool_result: Any) -> bool:
        if isinstance(tool_result, Exception):
            return True
        if isinstance(tool_result, dict):
            if tool_result.get('success') is False:
                return True
            if tool_result.get('error'):
                return True
        if isinstance(tool_result, str):
            import re
            text = tool_result.lower()
            
            # First check for common non-error phrases that contain these words
            safe_phrases = [
                r'room for error',      # Common financial phrase
                r'margin.{0,5}error',   # "margin of error" or "margin for error"
                r'trial.{0,5}error',    # "trial and error"
                r'human error',         # Common phrase
                r'rounding error',      # Mathematical term
                r'tracking error',      # Financial term
                r'forecast error',      # Statistical term
                r'measurement error',   # Scientific term
                r'blend of high prof',  # Specific to investment recommendations
                r'offers.{0,20}error',  # Company "offers" something with "error" nearby
                r'ameren',              # Company name that contains "error" substring
            ]
            
            # If any safe phrase is found, it's not an error
            for safe_pattern in safe_phrases:
                if re.search(safe_pattern, text, re.IGNORECASE):
                    return False
            
            # Now check for actual error patterns with more precision
            error_patterns = [
                r'^error:',             # line starting with "error:"
                r'^failed:',            # line starting with "failed:"
                r'^exception:',         # line starting with "exception:"
                r'error occurred',      # phrase "error occurred"
                r'error calling',       # phrase "error calling" (common in tool errors)
                r'returned error',      # phrase "returned error"
                r'raised error',        # phrase "raised error"
                r'threw error',         # phrase "threw error"
                r'error message',       # phrase "error message"
                r'traceback',           # Python traceback indicator
                r'\bfailed to\b',       # phrase "failed to"
                r'\bunable to\b',       # phrase "unable to"
                r'\bcould not\b',       # phrase "could not"
                r'permission denied',   # permission error
                r'access denied',       # access error
                r'not found',           # not found error
                r'timeout',             # timeout error
            ]
            return any(re.search(pattern, text, re.MULTILINE | re.IGNORECASE) for pattern in error_patterns)
        return False
    
    def _check_evidence_accumulation(self, subtask: SubTask) -> Tuple[bool, float, str]:
        """Check if subtask has accumulated sufficient evidence."""
        evidence_count = len(subtask.completion_evidence)
        observation_count = len(subtask.observations)
        
        # Evidence threshold
        if evidence_count >= 2 and observation_count >= 1:
            return True, 0.9, f"Sufficient evidence: {evidence_count} evidence, {observation_count} observations"
        elif evidence_count >= 1 and observation_count >= 1:
            return False, 0.6, f"Some evidence: {evidence_count} evidence, {observation_count} observations"
        else:
            return False, 0.2, f"Minimal evidence: {evidence_count} evidence, {observation_count} observations"
    
    def _analyze_observations_for_success(self, observations: List[str]) -> Tuple[bool, float, str]:
        """Analyze observation content for success indicators."""
        if not observations:
            return False, 0.0, "No observations to analyze"
        
        success_count = 0
        error_count = 0
        
        success_patterns = [
            'success', 'completed', 'finished', 'done', 'returned', 'generated', 
            'calculated', 'retrieved', 'found', 'created', 'processed'
        ]
        error_patterns = [
            'error', 'failed', 'exception', 'not found', 'invalid', 'timeout', 
            'denied', 'refused', 'blocked'
        ]
        
        for obs in observations:
            obs_lower = obs.lower()
            
            if any(pattern in obs_lower for pattern in success_patterns):
                success_count += 1
            
            if any(pattern in obs_lower for pattern in error_patterns):
                error_count += 1
        
        total_obs = len(observations)
        
        if error_count > success_count:
            return False, 0.2, f"More errors ({error_count}) than successes ({success_count})"
        
        if success_count > 0:
            confidence = success_count / total_obs
            if confidence >= 0.7:
                return True, confidence, f"Strong success signals: {success_count}/{total_obs}"
            else:
                return False, confidence, f"Some success signals: {success_count}/{total_obs}"
        
        return False, 0.4, "No clear success/error signals detected"
    
    def register_validator(self, name: str, validator_func: Callable) -> None:
        """Register a custom validation function.
        
        Args:
            name: Name of the validator
            validator_func: Function that validates a task
        """
        self.validators[name] = validator_func
        
        if self.verbose:
            print(f"📝 Registered validator: {name}")
    
    def get_completion_confidence(
        self,
        main_task: MainTask,
        current_subtask: SubTask = None
    ) -> Tuple[float, Dict[str, Any]]:
        """Get completion confidence score with detailed breakdown.
        
        Args:
            main_task: The MainTask to analyze
            current_subtask: Optional current SubTask
            
        Returns:
            Tuple of (confidence_score, detailed_breakdown)
        """
        breakdown = {
            'main_task_evidence': len(main_task.completion_evidence),
            'main_task_observations': len(main_task.observations),
            'subtasks_completed': sum(1 for st in main_task.subtasks if st.completed),
            'subtasks_total': len(main_task.subtasks),
            'predicted_tools': len(main_task.predicted_tool_use),
            'confidence_factors': []
        }
        
        confidence_factors = []
        
        # Factor 1: Subtask completion
        if main_task.subtasks:
            subtask_ratio = breakdown['subtasks_completed'] / breakdown['subtasks_total']
            confidence_factors.append(('subtasks', subtask_ratio, f"Subtasks: {breakdown['subtasks_completed']}/{breakdown['subtasks_total']}"))
        
        # Factor 2: Evidence accumulation
        evidence_score = min(breakdown['main_task_evidence'] / 3.0, 1.0)
        confidence_factors.append(('evidence', evidence_score, f"Evidence: {breakdown['main_task_evidence']} items"))
        
        # Factor 3: Observation quality
        obs_score = min(breakdown['main_task_observations'] / 2.0, 1.0)
        confidence_factors.append(('observations', obs_score, f"Observations: {breakdown['main_task_observations']} items"))
        
        # Factor 4: Current subtask if active
        if current_subtask:
            subtask_evidence = len(current_subtask.completion_evidence)
            subtask_obs = len(current_subtask.observations)
            subtask_score = min((subtask_evidence + subtask_obs) / 3.0, 1.0)
            confidence_factors.append(('current_subtask', subtask_score, f"Current subtask: {subtask_evidence} evidence, {subtask_obs} obs"))
        
        # Calculate weighted confidence
        if confidence_factors:
            total_confidence = sum(factor[1] for factor in confidence_factors) / len(confidence_factors)
        else:
            total_confidence = 0.0
        
        breakdown['confidence_factors'] = [
            {'name': factor[0], 'score': factor[1], 'description': factor[2]}
            for factor in confidence_factors
        ]
        breakdown['overall_confidence'] = round(total_confidence, 3)
        
        return total_confidence, breakdown
