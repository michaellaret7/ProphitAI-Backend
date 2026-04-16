"""Tool registry for the Signal+Strategy Builder agent.

Sandbox dev tools for reading and writing code. No scaffold_strategy — the
strategy directory is already scaffolded by the Indicator Builder.

deploy_scoped_worker and memory tools are NOT in this list — they are
bound via add_tool() at agent init time with functools.partial.
"""

from typing import Callable

from prophitai_tools.sandbox.dev_tools.read import sandbox_read
from prophitai_tools.sandbox.dev_tools.write import sandbox_write
from prophitai_tools.sandbox.dev_tools.edit import sandbox_edit
from prophitai_tools.sandbox.dev_tools.glob import sandbox_glob
from prophitai_tools.sandbox.dev_tools.grep import sandbox_grep
from prophitai_tools.sandbox.execution import sandbox_bash

SIGNAL_STRATEGY_BUILDER_TOOLS: list[Callable] = [
    sandbox_read,
    sandbox_write,
    sandbox_edit,
    sandbox_glob,
    sandbox_grep,
    sandbox_bash,
]
