"""Tool call error memory system for learning from and fixing tool execution failures."""

import json
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime


class ToolErrorMemory:
    """Manages memory of tool call errors and their solutions."""
    
    def __init__(self, save_memory: bool = True, verbose: bool = False):
        """Initialize the tool error memory system.
        
        Args:
            save_memory: Whether to persist memory to disk
            verbose: Whether to print debug messages
        """
        self.save_memory = save_memory
        self.verbose = verbose
        
        # Memory storage path
        # Resolve the path to ensure it's absolute
        memory_base_dir = Path(__file__).resolve().parent
        self.memory_path = memory_base_dir / "memory_store" / "tool_error_memory.json"
        
        # Ensure the directory exists
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self.error_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Load existing memory
        if self.save_memory:
            self._load_memory()
    
    def _load_memory(self) -> None:
        """Load error memory from disk."""
        try:
            if self.memory_path.exists():
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.error_patterns = data.get('error_patterns', {})
                    if self.verbose:
                        print(f"📚 Loaded {len(self.error_patterns)} error patterns from memory")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load error memory: {e}")
            self.error_patterns = {}
    
    def _save_memory(self) -> None:
        """Save error memory to disk."""
        if not self.save_memory:
            return
            
        try:
            # Ensure directory exists
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'error_patterns': self.error_patterns,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            if self.verbose:
                print(f"💾 Saved {len(self.error_patterns)} error patterns to memory")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save error memory: {e}")
    
    def _create_error_key(self, tool_name: str, error_message: str) -> str:
        """Create a normalized key for an error pattern.
        
        Args:
            tool_name: Name of the tool that failed
            error_message: The error message
            
        Returns:
            Normalized error key
        """
        # Extract key error patterns
        patterns = [
            r"missing.*required.*argument.*['\"](\w+)['\"]",  # Missing required argument 'x'
            r"got an unexpected keyword argument ['\"](\w+)['\"]",  # Unexpected argument
            r"missing \d+ required positional argument",  # Missing positional args
            r"takes.*\d+.*positional.*but.*\d+.*given",  # Wrong number of args
        ]
        
        error_type = "unknown_error"
        for pattern in patterns:
            if match := re.search(pattern, error_message, re.IGNORECASE):
                if match.groups():
                    error_type = f"missing_{match.group(1)}"
                else:
                    error_type = re.sub(r'\d+', 'N', match.group(0))  # Replace numbers with N
                break
        
        return f"{tool_name}:{error_type}"
    
    def record_error(self, tool_name: str, args: Dict[str, Any], error_message: str) -> str:
        """Record a tool call error for learning.
        
        Args:
            tool_name: Name of the tool that failed
            args: Arguments that were passed to the tool
            error_message: The error message
            
        Returns:
            Error key for reference
        """
        error_key = self._create_error_key(tool_name, error_message)
        
        # Initialize or update error pattern
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = {
                'tool_name': tool_name,
                'error_pattern': error_message[:200],  # Store first 200 chars
                'occurrences': [],
                'solutions': [],
                'auto_solution': None
            }
        
        # Record this occurrence
        self.error_patterns[error_key]['occurrences'].append({
            'timestamp': datetime.now().isoformat(),
            'args': args,
            'full_error': error_message
        })
        
        # Keep only last 10 occurrences
        self.error_patterns[error_key]['occurrences'] = \
            self.error_patterns[error_key]['occurrences'][-10:]
        
        self._save_memory()
        
        if self.verbose:
            print(f"📝 Recorded error pattern: {error_key}")
        
        return error_key
    
    def record_solution(self, error_key: str, correct_args: Dict[str, Any], 
                       explanation: str = None) -> None:
        """Record a successful solution to an error.
        
        Args:
            error_key: The error key from record_error
            correct_args: The arguments that worked
            explanation: Optional explanation of the fix
        """
        if error_key not in self.error_patterns:
            return
        
        solution = {
            'correct_args': correct_args,
            'explanation': explanation or "Corrected arguments",
            'timestamp': datetime.now().isoformat(),
            'success_count': 1
        }
        
        # Check if this solution already exists
        for existing in self.error_patterns[error_key]['solutions']:
            if existing['correct_args'] == correct_args:
                existing['success_count'] += 1
                break
        else:
            self.error_patterns[error_key]['solutions'].append(solution)
        
        # Auto-select best solution (most successful)
        best_solution = max(
            self.error_patterns[error_key]['solutions'],
            key=lambda x: x['success_count']
        )
        self.error_patterns[error_key]['auto_solution'] = best_solution
        
        self._save_memory()
        
        if self.verbose:
            print(f"✅ Recorded solution for: {error_key}")
    
    def get_solution(self, tool_name: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Get a solution for a known error pattern.
        
        Args:
            tool_name: Name of the tool that failed
            error_message: The error message
            
        Returns:
            Solution dict with 'guidance' and 'example_args' if found
        """
        error_key = self._create_error_key(tool_name, error_message)
        
        if error_key not in self.error_patterns:
            # Try partial matching for similar errors
            for key, pattern in self.error_patterns.items():
                if pattern['tool_name'] == tool_name:
                    # Check if error messages are similar
                    if self._errors_similar(error_message, pattern['error_pattern']):
                        error_key = key
                        break
            else:
                return None
        
        pattern = self.error_patterns.get(error_key)
        if not pattern or not pattern.get('auto_solution'):
            return None
        
        solution = pattern['auto_solution']
        
        # Build guidance message
        guidance = self._build_guidance(tool_name, error_message, solution)
        
        return {
            'guidance': guidance,
            'example_args': solution['correct_args'],
            'explanation': solution['explanation'],
            'confidence': solution['success_count'] / max(len(pattern['occurrences']), 1)
        }
    
    def _errors_similar(self, error1: str, error2: str) -> bool:
        """Check if two error messages are similar.
        
        Args:
            error1: First error message
            error2: Second error message
            
        Returns:
            True if errors are similar
        """
        # Simple similarity check - can be enhanced
        error1_words = set(error1.lower().split())
        error2_words = set(error2.lower().split())
        
        if not error1_words or not error2_words:
            return False
        
        overlap = len(error1_words & error2_words)
        similarity = overlap / min(len(error1_words), len(error2_words))
        
        return similarity > 0.7
    
    def _build_guidance(self, tool_name: str, error_message: str, 
                       solution: Dict[str, Any]) -> str:
        """Build a guidance message for fixing the error.
        
        Args:
            tool_name: Name of the tool
            error_message: The error message
            solution: The solution dict
            
        Returns:
            Guidance message string
        """
        guidance_parts = [
            f"⚠️ Known issue with '{tool_name}' tool detected.",
            f"Error: {error_message[:100]}...",
            f"Solution: {solution['explanation']}",
            f"Correct format example: {json.dumps(solution['correct_args'], indent=2)}"
        ]
        
        # Add specific guidance for common patterns
        if 'portfolio' in error_message.lower():
            guidance_parts.append(
                "💡 Tip: Extract portfolio data from the <Portfolio Data> section in the prompt, "
                "don't pass an empty dictionary."
            )
        elif 'ticker' in error_message.lower():
            guidance_parts.append(
                "💡 Tip: Ensure ticker is a string symbol like 'AAPL', not a dict or list."
            )
        
        return "\n".join(guidance_parts)
    
    def add_known_solution(self, tool_name: str, error_pattern: str, 
                          correct_args: Dict[str, Any], explanation: str) -> None:
        """Manually add a known solution for an error pattern.
        
        Args:
            tool_name: Name of the tool
            error_pattern: Error message pattern
            correct_args: Example of correct arguments
            explanation: Explanation of the solution
        """
        error_key = self._create_error_key(tool_name, error_pattern)
        
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = {
                'tool_name': tool_name,
                'error_pattern': error_pattern,
                'occurrences': [],
                'solutions': [],
                'auto_solution': None
            }
        
        solution = {
            'correct_args': correct_args,
            'explanation': explanation,
            'timestamp': datetime.now().isoformat(),
            'success_count': 10  # High initial count for manual solutions
        }
        
        self.error_patterns[error_key]['solutions'] = [solution]
        self.error_patterns[error_key]['auto_solution'] = solution
        
        self._save_memory()
        
        if self.verbose:
            print(f"+ Added known solution for: {error_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the error memory.
        
        Returns:
            Dict with memory statistics
        """
        total_patterns = len(self.error_patterns)
        patterns_with_solutions = sum(
            1 for p in self.error_patterns.values() 
            if p.get('auto_solution')
        )
        total_occurrences = sum(
            len(p['occurrences']) 
            for p in self.error_patterns.values()
        )
        
        return {
            'total_patterns': total_patterns,
            'patterns_with_solutions': patterns_with_solutions,
            'total_occurrences': total_occurrences,
            'solution_rate': patterns_with_solutions / max(total_patterns, 1)
        }


# Pre-populate with common portfolio tool errors
def initialize_common_solutions():
    """Initialize memory with common known solutions."""
    memory = ToolErrorMemory(save_memory=True, verbose=False)
    
    # Portfolio analysis tool errors
    memory.add_known_solution(
        tool_name="get_upside_downside_ratios",
        error_pattern="missing required argument 'portfolio'",
        correct_args={
            "portfolio": {"CASY": {"conviction": 0.1, "position": "long"}, "CELH": {"conviction": 0.1, "position": "long"}}
        },
        explanation="Extract portfolio from either from get_final_portfolio_dict() previous tool call if you want to test the initial portfolio but if you want to test a new portfolio you must pass the new portfolio in the correct dict format, don't pass empty dict"
    )
    
    memory.add_known_solution(
        tool_name="stress_test",
        error_pattern="portfolio argument cannot be empty",
        correct_args={
            "portfolio": {"CASY": {"conviction": 0.1, "position": "long"}, "CELH": {"conviction": 0.1, "position": "long"}}
        },
        explanation="Extract portfolio from either from get_final_portfolio_dict() previous tool call if you want to test the initial portfolio but if you want to test a new portfolio you must pass the new portfolio in the correct dict format, don't pass empty dict"
    )
    
    # Add solution for calculate_portfolio_performance
    memory.add_known_solution(
        tool_name="calculate_portfolio_performance",
        error_pattern="missing 1 required positional argument: 'portfolio_dict'",
        correct_args={
            "portfolio_dict": {
                "AAPL": {"position": "long", "allocation": 0.05},
                "MSFT": {"position": "long", "allocation": 0.05}
            }
        },
        explanation="Portfolio dict required with tickers as keys and position/allocation info. Extract from context or use portfolio from previous tool calls."
    )
    
    # Add solution for calculate_portfolio_beta_vs_index
    memory.add_known_solution(
        tool_name="calculate_portfolio_beta_vs_index",
        error_pattern="missing 1 required positional argument: 'portfolio_dict'",
        correct_args={
            "portfolio_dict": {
                "AAPL": {"position": "long", "allocation": 0.05},
                "MSFT": {"position": "long", "allocation": 0.05}
            },
            "index_ticker": "SPY"
        },
        explanation="Both portfolio_dict and index_ticker are required. Extract portfolio from context and specify index like SPY, QQQ, etc."
    )
    
    # Add solution for correlation_matrix
    memory.add_known_solution(
        tool_name="correlation_matrix",
        error_pattern="missing 1 required positional argument: 'portfolio_dict'",
        correct_args={
            "portfolio_dict": {
                "AAPL": {"position": "long", "allocation": 0.05},
                "MSFT": {"position": "long", "allocation": 0.05}
            }
        },
        explanation="Portfolio dict required. Extract from context or use portfolio from previous tool calls."
    )
    
    # Add solution for get_ticker_performance_and_risk  
    memory.add_known_solution(
        tool_name="get_ticker_performance_and_risk",
        error_pattern="missing 1 required positional argument: 'ticker'",
        correct_args={
            "ticker": "AAPL"
        },
        explanation="Ticker must be provided as a single ticker symbol string"
    )
    
    return memory
