from prophitai_fund.tools.workers.codebase_researcher import CODEBASE_RESEARCHER_PROMPT
from prophitai_fund.tools.workers.indicator_builder import INDICATOR_BUILDER_PROMPT
from prophitai_fund.tools.workers.signal_strategy_builder import SIGNAL_STRATEGY_BUILDER_PROMPT
from prophitai_fund.tools.workers.execution_builder import EXECUTION_BUILDER_PROMPT
from prophitai_atlas.models import WorkerSpec

CODING_TOOLS = frozenset({
    "sandbox_read",
    "sandbox_write",
    "sandbox_edit",
    "sandbox_glob",
    "sandbox_grep",
    "sandbox_bash",
})

WORKERS: dict[str, WorkerSpec] = {
    "codebase_researcher": WorkerSpec(
        name="codebase_researcher",
        system_prompt=CODEBASE_RESEARCHER_PROMPT,
        tools=frozenset({
          "sandbox_read",
          "sandbox_glob",
          "sandbox_grep"
        }),
        max_iterations=30,
        provider="fireworks",
        model="Qwen3.6-Plus",
    ),
    "indicator_builder": WorkerSpec(
        name="indicator_builder",
        system_prompt=INDICATOR_BUILDER_PROMPT,
        tools=CODING_TOOLS,
        max_iterations=100,
        provider="fireworks",
        model="Qwen3.6-Plus",
    ),
    "signal_strategy_builder": WorkerSpec(
        name="signal_strategy_builder",
        system_prompt=SIGNAL_STRATEGY_BUILDER_PROMPT,
        tools=CODING_TOOLS,
        max_iterations=100,
        provider="fireworks",
        model="Qwen3.6-Plus",
    ),
    "execution_builder": WorkerSpec(
        name="execution_builder",
        system_prompt=EXECUTION_BUILDER_PROMPT,
        tools=CODING_TOOLS,
        max_iterations=100,
        provider="fireworks",
        model="Qwen3.6-Plus",
    ),
}
