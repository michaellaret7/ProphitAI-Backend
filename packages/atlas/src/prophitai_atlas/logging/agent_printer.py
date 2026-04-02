"""AgentPrinter - Centralized output formatting for agent execution."""

import builtins
import sys
from typing import Any, Dict, Optional

from prophitai_atlas.models import PrintMode


def print(*args: Any, **kwargs: Any) -> None:
    """Print with best-effort encoding fallback for Windows consoles."""
    file = kwargs.get("file", sys.stdout)
    if file in (sys.stdout, sys.stderr):
        encoding = getattr(file, "encoding", None) or "utf-8"
        safe_args = [
            str(arg).encode(encoding, errors="replace").decode(encoding, errors="replace")
            for arg in args
        ]
        builtins.print(*safe_args, **kwargs)
        return
    builtins.print(*args, **kwargs)


class AgentPrinter:
    """Centralized output handler for agent execution."""

    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    def __init__(self, mode: PrintMode = PrintMode.PRODUCTION):
        self.mode = mode

    @property
    def is_verbose(self) -> bool:
        return self.mode != PrintMode.PRODUCTION

    def tool_call_start(self, name: str) -> None:
        if self.mode == PrintMode.PRODUCTION:
            print(f"  -> {name}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"\n[Sub-agent] Calling tool: {self.GREEN}{name}{self.RESET}")
        elif self.mode in (PrintMode.VERBOSE, PrintMode.DEBUG):
            print(f"\n[Agent] Calling tool: {self.GREEN}{name}{self.RESET}")

    def tool_arguments(self, args: Dict[str, Any]) -> None:
        if self.mode == PrintMode.PRODUCTION:
            return
        if self.mode == PrintMode.SUBAGENT:
            print(f"   [Sub-agent] Arguments: {self.YELLOW}SUCCESSFULLY PARSED{self.RESET}")
        elif args:
            print("   Arguments:")
            for key, value in args.items():
                print(f"     - {self.YELLOW}{key}: {value}{self.RESET}")
        else:
            print(f"   Arguments: {self.YELLOW}(none){self.RESET}")

    def tool_result(self, name: str, result: Any, success: bool) -> None:
        if self.mode == PrintMode.DEBUG:
            print(f"  <- Result: {result}")
        elif self.mode == PrintMode.VERBOSE:
            result_str = str(result)
            truncated = f"{result_str[:200]}... (truncated)" if len(result_str) > 200 else result_str
            print(f"   OK Result: {truncated}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"[Sub-agent] {name} tool call successful: {success}")

    def tool_error(self, message: str) -> None:
        print(f"  !! {message}")

    def parse_error(self, args_json: str) -> None:
        if self.mode == PrintMode.PRODUCTION:
            return
        display = args_json[:200] + "..." if len(args_json) > 200 else args_json
        print(f" Could not parse args: {display}")
        print("   !! Argument parse failed - skipping tool execution")

    def parallel_start(self, num_tools: int) -> None:
        if self.mode in (PrintMode.VERBOSE, PrintMode.DEBUG):
            print(f"\n{self.CYAN}[parallel] {num_tools} tools{self.RESET}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"\n[Sub-agent] [parallel] {num_tools} tools")
        elif self.mode == PrintMode.PRODUCTION:
            print(f"  [parallel] {num_tools} tools")

    def parallel_tool_queued(self, name: str) -> None:
        if self.mode in (PrintMode.VERBOSE, PrintMode.DEBUG, PrintMode.SUBAGENT):
            print(f"   -> {self.GREEN}{name}{self.RESET}")
        elif self.mode == PrintMode.PRODUCTION:
            print(f"    -> {name}")

    def parallel_tool_result(self, name: str, result: Any, success: bool) -> None:
        status = "OK" if success else "ERR"
        if self.mode == PrintMode.DEBUG:
            print(f"   {self.GREEN}{name}{self.RESET} <- {result}")
        elif self.mode == PrintMode.VERBOSE:
            result_str = str(result)
            truncated = f"{result_str[:100]}..." if len(result_str) > 100 else result_str
            print(f"   {status} {self.GREEN}{name}{self.RESET}: {truncated}")
        elif self.mode == PrintMode.SUBAGENT:
            print(f"   {status} {self.GREEN}{name}{self.RESET}")
        elif self.mode == PrintMode.PRODUCTION:
            print(f"    {status} {name}")

    def iteration_start(self, iteration: int, max_iterations: Optional[int] = None) -> None:
        if self.mode == PrintMode.PRODUCTION:
            print(f"\n[{iteration}]", end=" ", flush=True)
        elif max_iterations is not None:
            print(f"\n{self.CYAN}[Chat] Iteration {iteration}/{max_iterations}{self.RESET}")
        else:
            print(f"\n--- Iteration {iteration} ---")

    def iteration_complete(self, iteration: int, reason: str) -> None:
        if self.mode == PrintMode.VERBOSE and reason == "answer_ready":
            print(f"\n{self.GREEN}[Chat] Answer ready after {iteration} iteration(s){self.RESET}")
        elif reason == "max_iterations":
            print(f"\n{self.CYAN}[Chat] Max iterations reached{self.RESET}")

    def assistant_response(self, text: str) -> None:
        if text and self.mode != PrintMode.PRODUCTION:
            print(f"Assistant: {text}")

    def token_usage(self, tokens: int) -> None:
        print(f"Token Usage: {tokens}")

    def note_added(self, title: str) -> None:
        if self.mode != PrintMode.PRODUCTION:
            print(f"[note] Added note title to notebook: '{title}'")

    def warning(self, message: str) -> None:
        if self.mode == PrintMode.DEBUG:
            print(f"!! Warning: {message}")

    def error(self, message: str) -> None:
        print(f"!! {message}")

    def debug_response(self, response: Any) -> None:
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
