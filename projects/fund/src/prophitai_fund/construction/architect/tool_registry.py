"""Tool registry for the Strategy Architect agent.

Sandbox tools for inspecting the algo_trading framework and writing
manifest sections incrementally. The Architect reads base classes,
std_lib indicators, sizers, risk controls, and signal primitives,
then writes manifest JSON sections to the sandbox for assembly.
"""

from typing import Callable, List

# ================================
# --> Sandbox tools
# ================================
from prophitai_tools.sandbox.dev_tools.read import sandbox_read
from prophitai_tools.sandbox.dev_tools.glob import sandbox_glob
from prophitai_tools.sandbox.dev_tools.grep import sandbox_grep
from prophitai_tools.sandbox.dev_tools.write import sandbox_write

ARCHITECT_TOOLS: List[Callable] = [
    sandbox_read,
    sandbox_glob,
    sandbox_grep,
    sandbox_write,
]
