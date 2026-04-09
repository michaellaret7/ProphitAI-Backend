"""Tool registry for the Strategy Architect agent.

Read-only sandbox tools for inspecting the algo_trading framework.
The Architect reads base classes, std_lib indicators, sizers, risk controls,
and signal primitives — it never writes code or modifies files.
"""

from typing import Callable, List

# ================================
# --> Sandbox read tools
# ================================
from prophitai_tools.sandbox.dev_tools.read import sandbox_read
from prophitai_tools.sandbox.dev_tools.glob import sandbox_glob
from prophitai_tools.sandbox.dev_tools.grep import sandbox_grep

ARCHITECT_TOOLS: List[Callable] = [
    sandbox_read,
    sandbox_glob,
    sandbox_grep,
]
