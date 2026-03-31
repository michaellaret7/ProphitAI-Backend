---
name: review-pr
description: Review a PR for code quality issues against ProphitAI development guidelines. Uses Opus agents to audit the diff, then reports exact issues to fix.
---

## Overview

Deep code review of a pull request against ProphitAI's development guidelines and code quality standards defined in `AGENTS.md`. Reports only real, actionable issues — no nitpicks, no false positives.

## Workflow

Follow these steps **in order**.

### Step 1: Identify the PR

If the user provided a PR number, use it. Otherwise, detect the current branch and find its open PR:

```bash
gh pr list --head $(git rev-parse --abbrev-ref HEAD) --state open --json number,title,url
```

If no open PR exists, tell the user and stop.

### Step 2: Gather the diff and commit history

Run in parallel:

```bash
gh pr diff <number>
```

```bash
gh pr diff <number> --name-only
```

```bash
gh pr view <number> --json title,body,baseRefName,headRefName,commits
```

```bash
git log <base>..HEAD --oneline
```

### Step 3: Read CLAUDE.md

Read `AGENTS.md` to load the full set of development guidelines. This is the source of truth for all rules.

### Step 4: Launch parallel Opus review agents

Launch **4 parallel Opus agents**, each with the full diff, file list, and CLAUDE.md contents. Each agent reviews from a different angle:

**Agent 1 — Guidelines Compliance**
Audit the diff against every applicable rule in CLAUDE.md:
- File size limits (500 lines), function size (50 lines), class size (100 lines)
- Naming conventions: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- Type hints and explicit return types on all functions
- Module docstrings, public function docstrings
- `# Reason:` prefix on complex inline comments
- Helper functions at top of file with block comment separators
- UTC timezone handling: never `datetime.now()`, always `get_current_utc_time()`
- Session decorators: `@with_session`, `@with_transaction`, `@with_sessions`
- Portfolio parameter convention: `tickers: List[str]`, `weights: List[float]`
- No backwards compatibility hacks
- No files/folders with leading underscore in the name
- KISS / YAGNI / DRY / Single Responsibility / Fail Fast
- No hardcoded secrets or credentials committed

For each violation, cite the exact CLAUDE.md rule text and the file + line number.

**Agent 2 — Code Quality & Bugs**
Read every changed file in the diff. Look for:
- Logic errors, off-by-one, null/None dereference
- Security issues: credential exposure, injection, missing auth checks
- Missing error handling on critical paths (DB, external APIs, file I/O)
- Debug artifacts: `print()` statements, commented-out code, TODO/FIXME left in
- Dead code or unreachable branches introduced by the PR
- Incorrect API usage or broken function signatures
- Race conditions or thread-safety issues
- Silent failures (swallowing exceptions, returning empty instead of raising)

Only flag issues **introduced by this PR**, not pre-existing problems.

**Agent 3 — Architecture & Design Patterns**
Check the changes follow ProphitAI's established patterns:
- API layering: Routes → Controllers → Services → Repositories (no skipping layers)
- Tool registration: `@agent_tool` decorator, imported in registry
- Agent patterns: proper use of `AgentBase`, `Agent`, `PlannerAgent`, `WorkerAgent`
- Session management via decorators, not manual session creation
- Callback pattern for streaming
- DRY: check if the new code duplicates existing functionality elsewhere in the codebase
- Single Responsibility: each new function/class has one clear purpose
- Dependency direction: no circular imports, proper layer boundaries

**Agent 4 — File Hygiene & Stray Content**
Check for:
- Stray files that shouldn't be committed (scratch files, AI output dumps, temp files)
- Files added to wrong directories (production code in test dirs or vice versa)
- Excess test files (CLAUDE.md rule: don't create duplicates, just fix the one)
- Config files with hardcoded values that should use env vars
- `.gitignore` additions that come too late (file already tracked)
- Filename issues: spaces, wrong casing, leading underscores

Each agent returns a list of issues with:
- **File path and line number**
- **What's wrong**
- **Which rule or principle it violates**
- **Suggested fix** (one sentence)

### Step 5: Deduplicate and filter

Merge results from all 4 agents. Remove:
- Duplicate issues flagged by multiple agents (keep the most detailed version)
- Issues on lines NOT modified by the PR (pre-existing problems)
- Issues that a linter, typechecker, or CI would catch (imports, formatting, types)
- Speculative concerns that aren't demonstrably wrong

### Step 6: Classify and report

Group remaining issues by severity:

**CRITICAL** — Security vulnerabilities, hardcoded secrets, data loss risks, broken auth
**HIGH** — Bugs that will cause runtime failures, missing error handling on critical paths, broken patterns
**MEDIUM** — Guideline violations that affect maintainability (size limits, missing docstrings, naming)
**LOW** — Minor hygiene issues (stray files, comment accuracy)

Present the final report in this format:

```
## PR Review: <PR title>

### Critical
1. **<file>:<line>** — <description>
   Rule: <CLAUDE.md quote or principle>
   Fix: <one-line suggestion>

### High
...

### Medium
...

### Low
...
```

If no issues are found, say so clearly:

```
## PR Review: <PR title>

No issues found. Code is clean and follows project guidelines.
```

## Rules

- Use **Opus** model for all review agents — do not use Haiku or Sonnet
- Only report issues you are confident about — when in doubt, leave it out
- Never suggest adding Claude attribution or AI branding
- Focus on what needs to be **fixed**, not general suggestions or "nice to haves"
- Every issue must have a file path, line number, and concrete fix
- Do NOT attempt to fix the issues — just report them
