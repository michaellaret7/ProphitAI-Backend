from prophitai_fund.tools.workers.codebase_researcher import CODEBASE_RESEARCHER_PROMPT
from prophitai_atlas.models import WorkerSpec

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
    ),
}