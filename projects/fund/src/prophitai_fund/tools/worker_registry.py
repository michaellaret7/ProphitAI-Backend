from prophitai_fund.tools.workers.codebase_researcher import CODEBASE_RESEARCHER_PROMPT
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
}
