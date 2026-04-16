"""Tool registry for the Validator agent.

Sandbox dev tools for reading IDEA.md + config + runner scripts and writing
ticker_universe.py / RESULTS.md. Host-bound screeners for translating the
idea's universe criteria into a concrete ticker list.

past_ideas, memory, and skill tools are NOT in this list — they are bound
via add_tool() at agent init time with functools.partial so their file
paths stay hidden from the LLM.
"""

from typing import Callable

from prophitai_tools.sandbox.dev_tools.read import sandbox_read
from prophitai_tools.sandbox.dev_tools.write import sandbox_write
from prophitai_tools.sandbox.dev_tools.edit import sandbox_edit
from prophitai_tools.sandbox.dev_tools.glob import sandbox_glob
from prophitai_tools.sandbox.dev_tools.grep import sandbox_grep
from prophitai_tools.sandbox.execution import sandbox_bash
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.screener.etf_screener import etf_screener


VALIDATOR_TOOLS: list[Callable] = [
    sandbox_read,
    sandbox_write,
    sandbox_edit,
    sandbox_glob,
    sandbox_grep,
    sandbox_bash,
    equity_screener,
    etf_screener,
]
