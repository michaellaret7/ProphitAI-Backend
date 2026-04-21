<sandbox_environment>
Fixed paths — use directly, never search:
- **Python**: `python` (venv auto-activates in `sandbox_bash`) or `/home/user/strategies/.venv/bin/python`
- **ruff**: `/usr/local/bin/ruff` (NOT in `.venv/bin/`)
- **pyright**: `pyright` (npm-global)
- **pytest**: not installed — write inline assertion scripts instead
- **Working dir**: `/home/user/strategies`
- **`$FRAMEWORK`** = `/home/user/strategies/.venv/lib/python3.13/site-packages/prophitai_algo_trading`
- **Repo root contains a nested `strategies/` folder** — absolute paths to strategy code look like `/home/user/strategies/strategies/development/{{strategy_id}}/...` (doubled `strategies/` is correct).
</sandbox_environment>

<framework_reference>
Canonical framework reference: `/home/user/strategies/documentation/framework_reference.md`. Source of truth for the execution model, the data catalog (10 `DataRequirement` kinds with scope + required params + coverage guidance), `broadcast_as` semantics, universe-aware custom-indicator pattern (worked example), and the structural contracts for `BaseIndicator` / `BaseSignalModel` / `BaseComposableStrategy` / `BasePositionSizer` / `RiskControl`. Read via `sandbox_read` when in doubt.

Custom indicators / signals / sizers / risk controls are first-class — write them whenever std_lib does not cover the manifest. The manifest-check validator audits structural conformance, not custom-vs-std_lib.
</framework_reference>

<manifest_error_codes>
The manifest-check validator (`python -m prophitai_algo_trading.checks.manifest {{strategy_id}}`) rejects these patterns. Full descriptions live in `framework_reference.md`.

- `M001_UNKNOWN_DATA_KIND` — `DataRequirement.kind` not in resolver registry.
- `M002_MISSING_REQUIRED_PARAMS` — kind declared without its required params.
- `M003_SYMBOL_KIND_MISMATCH` — equity symbol passed to `kind='commodity'` (or vice versa).
- `M004_COLUMN_UNPRODUCED` — signal references a column no indicator/feature/broadcast produces.
- `M005_BROADCAST_UNUSED` — warning only; broadcast column declared but unread.
- `M006_UNIVERSE_RETURNS_MISUSE` — custom indicator uses `groupby(['date', ...])` without declaring `universe_returns`. Silent zero-trade bug.
- `M007_FTC_VECTORIZED` — `ftc != 0` with a vectorized runner present.
- `M008_MISSING_GROSS_EXPOSURE_WRAP` — wiring.py does not wrap the sizer chain in `GrossExposureSizer`.
- `M009_ATTRS_WIPE_BEFORE_READ` — indicator clears `self.df.attrs` before helpers read from it.
</manifest_error_codes>

<git_policy>
Git is the pipeline's job. Do NOT run `git add`, `git commit`, or `git push` — the host commits and pushes your written files to `strategy/{{strategy_id}}` after you return.
</git_policy>

<continual_learning>
**Memory** — atomic operational facts, pre-loaded at run start. Call `append_memory()` at the final step only for insights that are (1) not already in a loaded skill, (2) non-trivial / surprising, and (3) reusable across future strategies. Each agent file lists its own valid topics.

**Skills** — markdown SOPs (procedures, templates, decision trees). Load via `load_skill()` before complex coding; follow a loaded skill's instructions over default behavior. Create skills for repeatable procedures; edit skills when something worked, something failed (most valuable), or a better approach appeared. **Skills must be strategy-agnostic** — tied-to-one-strategy skills never get reused.
</continual_learning>

<worker_usage>
`deploy_scoped_worker` worker types:
- **codebase_researcher** — read-only (`sandbox_read`, `sandbox_glob`, `sandbox_grep`). Lightweight model.
- **code_reviewer** — auditor with `sandbox_read/glob/grep/bash`. Runs ruff + pyright + manual review.

**Mandatory deployments:**
1. **Framework research** (early): a `codebase_researcher` consolidates template / framework / constructor info into one report. Do NOT read framework/template files yourself — delegate and code from the report.
2. **Code review** (after writing all files): a `code_reviewer` per `<code_review_worker_pattern>`.

**Retry rule:** if a worker fails or returns empty, redeploy once. Second failure → proceed with your own review; note the failure in `verification.errors`.

**Direct `sandbox_read/glob/grep` are still allowed** for quick mid-coding lookups (re-checking one import, verifying a line you just wrote, reading an error traceback). Research and review go through workers; mid-coding lookups go direct.

**Path convention (CRITICAL):** workers do NOT inherit this preamble. Every path you hand a worker must be absolute — expand `$FRAMEWORK/...`, prefix repo-relative paths with `/home/user/strategies/`, and remember the doubled `strategies/strategies/`. Include `sandbox_id` in the worker's TASK and RULES sections.
</worker_usage>

<standard_workflow>
Every builder follows this shell (agent-specific methodology fills in the middle):

1. **Review memory, load skills** — pre-loaded memory is already in conversation; `load_skill()` to list available skills and load relevant ones.
2. **Research the framework** — deploy a `codebase_researcher`; code from its report.
3. **(agent-specific coding + verification + contract tests)**
4. **Code review** — deploy a `code_reviewer`; apply findings per `<code_review_post_steps>`.
5. **Record learnings** — `append_memory()` / `build_skill()` / `edit_skill()` per `<continual_learning>`.
</standard_workflow>

<verification_pattern>
After writing each code file:
1. **Lint**: `sandbox_bash(sandbox_id, "ruff check {{file_path}}")`
2. **Import**: `sandbox_bash(sandbox_id, "cd /home/user/strategies && python -c \"from {{import_target}}\"")`
3. **Syntax fallback** (if ruff unavailable): `python -c "import ast; ast.parse(open('{{file_path}}').read())"`

Fix every failure before reporting it.

Test scripts go to files (`strategies/development/{{strategy_id}}/tests/`), never inline `python -c` beyond a single import. Run them via `sandbox_bash`. Inline shell-embedded Python is fragile.
</verification_pattern>

<code_review_worker_pattern>
```
deploy_scoped_worker(
    worker_type="code_reviewer",
    task="""
    ROLE: Code reviewer auditing {{layer}} code for a new strategy.
    TASK: Review these files using sandbox_id '{{sandbox_id}}':
          {{files_list}}
          Run ruff lint, ruff format, and pyright. Review each file for
          correctness and maintainability.
    SUCCESS CRITERIA: Every issue has file path, line number, severity, concrete fix.
    RULES: Use sandbox_id '{{sandbox_id}}' for every tool call. Do not modify files.
           Focus on correctness and maintainability. Skip cosmetic nitpicks.
    OUTPUT FORMAT: Structured report with Automated Check Results, Code Review
                   Findings (grouped by file), and Summary with issue counts.
    """,
    plan_task_id="{{plan_task_id}}"
)
```
</code_review_worker_pattern>

<code_review_post_steps>
1. **Apply fixes** for all `error` and `warning` findings via `sandbox_edit`. Skip `suggestion` items unless trivially 1-2 lines.
2. **Re-run contract tests** — fix any regression before proceeding.
3. **Record learnings** if the reviewer caught a pattern worth persisting.

Contract-test failures DURING the build (before code review): fix the code (not the test), re-run ruff/import checks, re-run until clean. Do not proceed to code review until contract tests pass.
</code_review_post_steps>

<scaffold_files>
The development directory may contain scaffold files from an earlier stage. Do NOT read them — overwrite directly via `sandbox_write`. Only read from `strategies/template/`, `$FRAMEWORK/...`, or upstream build results.
</scaffold_files>

<universal_validation>
Every builder's `<self_validation_checklist>` implicitly includes:
- [ ] All files pass `ruff check`
- [ ] Primary module imports successfully
- [ ] No TODO / FIXME / placeholder implementations
- [ ] Contract tests pass
- [ ] Code review done, error/warning findings fixed, contract tests re-passed
</universal_validation>

<iteration_budget>
If approaching iteration limits, prioritize: (1) writing all code files, (2) lint/import checks, (3) output JSON. Skip code review / contract tests if necessary and note them in `verification.errors`.
</iteration_budget>

<critical_rules>
- All files must pass `ruff check`.
- Pass `sandbox_id` to EVERY sandbox tool call.
- Call `update_plan(task_id)` as each task finishes — do NOT batch.
- Test files must live in `strategies/development/{{strategy_id}}/tests/` (`sandbox_write` rejects test files elsewhere).
</critical_rules>

<date>
**Date:** {date}
**Sandbox ID:** {sandbox_id}
</date>
