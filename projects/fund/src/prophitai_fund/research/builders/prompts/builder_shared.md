### Memory Quality Gate

Before calling `append_memory`, check ALL three conditions:
1. **Not redundant with a loaded skill** — If the fact is already documented in a
   skill you loaded this run, do not duplicate it as a memory entry.
2. **Not trivially confirmatory** — Do not persist facts like "field X exists in
   dataclass Y" or "feature Z works as documented." Only persist findings that were
   surprising, counterintuitive, or contradicted your expectations.
3. **Reusable across strategies** — The fact must apply to future strategy builds,
   not just the current one. If it only matters for this specific strategy, skip it.

If a fact fails any of these checks, do not persist it.

### Critical Constraint: Skills Must Be Strategy-Agnostic

Skills exist to accelerate FUTURE strategy builds. Once a strategy is built and
deployed, it never passes through this pipeline again — a skill tied to one strategy
will never be loaded again. Every skill must describe a reusable PATTERN or TECHNIQUE
that applies across any strategy rather than strategy-specific details.

### When to Edit a Skill

Edit a skill when:
- **Something worked** — Add the successful approach as a confirmed pattern with
  a brief note on why it worked
- **Something failed** — Add a "Pitfalls" or "What NOT to Do" section describing the
  failure, what went wrong, and the fix. These are the most valuable edits.
- **You found a better approach** — Update the recommended approach and move the old
  one to a "Alternatives Considered" section
- **The framework changed** — If you discover a constructor signature changed or a
  new base class was introduced, update affected skills

### Skill Content Structure

When building a skill, use this structure:

```markdown
## When to Use
One-liner on what triggers this skill.

## Procedure
Step-by-step instructions with code examples.

## Code Template
\```python
# Copy-paste starting point
\```

## Pitfalls
- What can go wrong and how to avoid it

## Confirmed Patterns
- Approaches that worked with brief context on when/why

## Revision Log
- YYYY-MM-DD: Created after building [context]
- YYYY-MM-DD: Added pitfall — [what failed and why]
```

### Skill Lifecycle

1. **First run:** No skills exist. Build them as you discover reusable patterns.
2. **Subsequent runs:** Load relevant skills before starting work. Edit them with
   new learnings after completing work.
3. **Over time:** Skills accumulate battle-tested procedures. Load a skill BEFORE
   attempting a task it covers — don't reinvent what you've already documented.

### Code Review Post-Steps

After receiving the reviewer's findings:
1. **Apply fixes** — Address all `error` and `warning` severity findings. Use `sandbox_edit`
   for targeted fixes. Skip `suggestion` items unless they are trivial (1-2 line changes).
2. **Re-run contract tests** — Ensure fixes didn't break anything. If a test fails, fix it
   before proceeding.
3. **Record review learnings** — If the reviewer caught a pattern you should avoid in future
   builds, save it as a memory entry or update a relevant skill.

### Shared Critical Rules

- **All files must pass `ruff check`.** Fix any lint errors before completing.

- **Pass `sandbox_id` to EVERY sandbox tool call** without exception.

- **Mark tasks complete immediately.** Call `update_plan(task_id)` as soon as each
  task is finished — do NOT batch multiple `update_plan` calls together. Progress
  tracking only works when tasks are marked in real time.