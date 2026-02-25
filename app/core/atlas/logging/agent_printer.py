"""AgentPrinter - Centralized output formatting for agent execution.

This module consolidates all printing logic from tool_handler.py and execution loops.
Single responsibility: format and display agent execution output based on PrintMode.
"""

from typing import Any, Dict, Optional

from app.core.atlas.models import PrintMode


class AgentPrinter:
    """Centralized output handler for agent execution.

    All print mode conditional logic lives here instead of being scattered
    across tool handlers and execution loops.

    Attributes:
        mode: The current PrintMode controlling output verbosity.
    """

    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    def __init__(self, mode: PrintMode = PrintMode.PRODUCTION):
        self.mode = mode

    @property
    def is_verbose(self) -> bool:
        """Returns True if mode is not PRODUCTION (for functions needing a bool flag)."""
        return self.mode != PrintMode.PRODUCTION

    # -------------------------------------------------------------------------
    # Tool Execution
    # -------------------------------------------------------------------------

    def tool_call_start(self, name: str) -> None:
        """Print when a tool call begins."""
        if self.mode == PrintMode.PRODUCTION:
            print(f"  → {name}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"\n[Sub-agent] Calling tool: {self.GREEN}{name}{self.RESET}")
        elif self.mode in (PrintMode.VERBOSE, PrintMode.DEBUG):
            print(f"\n[Agent] Calling tool: {self.GREEN}{name}{self.RESET}")

    def tool_arguments(self, args: Dict[str, Any]) -> None:
        """Print tool arguments."""
        if self.mode == PrintMode.PRODUCTION:
            return

        display_args = args

        if self.mode == PrintMode.SUBAGENT:
            print(f"   [Sub-agent] Arguments: {self.YELLOW}SUCCESSFULLY PARSED{self.RESET}")
        elif display_args:
            print("   Arguments:")
            for key, value in display_args.items():
                print(f"     - {self.YELLOW}{key}: {value}{self.RESET}")
        else:
            print(f"   Arguments: {self.YELLOW}(none){self.RESET}")

    def tool_result(self, name: str, result: Any, success: bool) -> None:
        """Print tool execution result."""
        if self.mode == PrintMode.DEBUG:
            print(f"  ← Result: {result}")
        elif self.mode == PrintMode.VERBOSE:
            result_str = str(result)
            truncated = f"{result_str[:200]}... (truncated)" if len(result_str) > 200 else result_str
            print(f"   ✓ Result: {truncated}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"[Sub-agent] {name} tool call successful: {success}")

    def tool_error(self, message: str) -> None:
        """Print tool execution error."""
        print(f"  ⚠️ {message}")

    def parse_error(self, args_json: str) -> None:
        """Print argument parse failure."""
        if self.mode == PrintMode.PRODUCTION:
            return
        display = args_json[:200] + "..." if len(args_json) > 200 else args_json
        print(f" Could not parse args: {display}")
        print("   ⚠️ Argument parse failed - skipping tool execution")

    # -------------------------------------------------------------------------
    # Parallel Tool Execution
    # -------------------------------------------------------------------------

    def parallel_start(self, num_tools: int) -> None:
        """Print when parallel execution begins."""
        if self.mode in (PrintMode.VERBOSE, PrintMode.DEBUG):
            print(f"\n{self.CYAN}🔀 Parallel execution: {num_tools} tools{self.RESET}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"\n[Sub-agent] 🔀 Parallel execution: {num_tools} tools")
        elif self.mode == PrintMode.PRODUCTION:
            print(f"  🔀 {num_tools} tools (parallel)")

    def parallel_tool_queued(self, name: str) -> None:
        """Print when a tool is queued for parallel execution."""
        if self.mode in (PrintMode.VERBOSE, PrintMode.DEBUG, PrintMode.SUBAGENT):
            print(f"   → {self.GREEN}{name}{self.RESET}")
        elif self.mode == PrintMode.PRODUCTION:
            print(f"    → {name}")

    def parallel_tool_result(self, name: str, result: Any, success: bool) -> None:
        """Print result of a parallel tool execution."""
        status = "✓" if success else "✗"
        if self.mode == PrintMode.DEBUG:
            print(f"   {self.GREEN}{name}{self.RESET} ← {result}")
        elif self.mode == PrintMode.VERBOSE:
            result_str = str(result)
            truncated = f"{result_str[:100]}..." if len(result_str) > 100 else result_str
            print(f"   {status} {self.GREEN}{name}{self.RESET}: {truncated}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"   {status} {self.GREEN}{name}{self.RESET}")
        elif self.mode == PrintMode.PRODUCTION:
            print(f"    {status} {name}")

    # -------------------------------------------------------------------------
    # Iteration
    # -------------------------------------------------------------------------

    def iteration_start(self, iteration: int, max_iterations: Optional[int] = None) -> None:
        """Print iteration header."""
        if self.mode == PrintMode.PRODUCTION:
            print(f"\n[{iteration}]", end=" ", flush=True)
        elif max_iterations is not None:
            print(f"\n{self.CYAN}[Chat] Iteration {iteration}/{max_iterations}{self.RESET}")
        else:
            print(f"\n--- Iteration {iteration} ---")

    def iteration_complete(self, iteration: int, reason: str) -> None:
        """Print when iteration completes."""
        if self.mode == PrintMode.VERBOSE and reason == "answer_ready":
            print(f"\n{self.GREEN}[Chat] Answer ready after {iteration} iteration(s){self.RESET}")
        elif reason == "max_iterations":
            print(f"\n{self.CYAN}[Chat] Max iterations reached{self.RESET}")

    # -------------------------------------------------------------------------
    # General
    # -------------------------------------------------------------------------

    def assistant_response(self, text: str) -> None:
        """Print assistant's text response."""
        if text and self.mode != PrintMode.PRODUCTION:
            print(f"Assistant: {text}")

    def token_usage(self, tokens: int) -> None:
        """Print token usage."""
        print(f"Token Usage: {tokens}")

    def note_added(self, title: str) -> None:
        """Print when note is added."""
        if self.mode != PrintMode.PRODUCTION:
            print(f"📝 Added note title to notebook: '{title}'")

    def warning(self, message: str) -> None:
        """Print warning message (DEBUG mode only)."""
        if self.mode == PrintMode.DEBUG:
            print(f"⚠️  Warning: {message}")

    def error(self, message: str) -> None:
        """Print error message."""
        print(f"⚠️ {message}")

    def debug_response(self, response: Any) -> None:
        """Print raw LLM response (DEBUG mode only)."""
        if self.mode != PrintMode.DEBUG:
            return
        try:
            print("\nLLM raw response JSON:")
            print(response.model_dump_json(indent=2))
        except Exception:
            try:
                import json
                print("\nLLM raw response dict:")
                print(json.dumps(response.model_dump(), indent=2, default=str))
            except Exception:
                print(f"\nLLM raw response (repr): {response!r}")
