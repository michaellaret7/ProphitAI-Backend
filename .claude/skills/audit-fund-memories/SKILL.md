---
name: audit-fund-memories
description: Audit and clean the six memory.md files that feed the fund pipeline agents (idea_generation, architect, build/indicators, build/signals, build/execution, validation). Use when the user asks to review, audit, clean, or sanitize fund agent memories, or when pipeline failures suggest memory contamination. Catches strategy-name leaks (WVCCI, PEAPH, AQM52, LSDA, CIM, VCLR, RAMD), bug-encoding entries that teach cloning from another strategy's directory, validator entries that teach accepting template-scaffold results, duplicate/superseded entries, and outdated framework facts. Rewrites each memory in-place, preserving productive patterns and stripping strategy-specific names.
license: Apache-2.0
metadata:
  author: michael-laret
  version: "1.0"
---

## Overview

Memory files prime every builder agent at start of run. A single bad entry can teach the agent to reproduce a bug as a best practice — the WVCCI-clone incident (VCLR, CIM, LSDA, RAMD failures) was traced to `execution/memory.md` entries that said "import the upstream strategy's classes from its directory" when they should have said "halt and re-run the upstream builder." This skill prevents that by enforcing three rules: patterns not strategies, halt not workaround, and no superseded facts.

## Target files

All six live under `projects/fund/src/prophitai_fund/`:

- `idea_generation/memory.md`
- `construction/architect/memory.md`
- `construction/build/indicators/memory.md`
- `construction/build/signals/memory.md`
- `construction/build/execution/memory.md`
- `validation/memory.md`

## Procedure

1. Read all six files in parallel.
2. Classify each entry as KEEP, REWRITE, or DELETE using the rules below.
3. For each file, write a single fully-revised version in one Write call. Do not use multi-Edit — these files accumulate cruft and benefit from a clean rewrite.
4. Report before/after line counts and the count of KEEP/REWRITE/DELETE decisions per file.
5. After rewriting, `grep` the cleaned files for the strategy-name denylist (below) as a verification pass. Report any remaining hits.

## Classification rules

### DELETE — remove entirely

Delete an entry if it falls into any of these categories:

- **Bug-encoding**: normalizes a known bug as a pattern. Canonical example: an entry telling the execution builder to import classes from a different strategy's directory. The fix is for the builder to HALT on that condition, not to accept it as "sometimes upstream lives elsewhere."
- **Validator coping**: tells the validator to fix template scaffolds and record a `failed` verdict with the scaffold's EMA/RSI Sharpe. This pollutes past_ideas.md with fake failures. Rewrite so the validator halts with `build_failure` instead.
- **Superseded fact**: directly contradicted by a later corrected entry (e.g. "no rolling_max in std_lib" vs a later "rolling_max IS registered"). Keep only the current correction.
- **Stale universe claim**: idea-generator entries like "distribution-tail is an unexplored space" after a strategy in that space has been tried (LSDA). Replace with a generic "check past_ideas.md before claiming a space is unexplored."
- **Hard-coded ephemeral identifiers**: specific sandbox IDs, specific test ticker strings baked into instructions, one-run noise.

### REWRITE — keep the lesson, strip the strategy name

Rewrite an entry if it contains productive procedural knowledge AND a strategy-specific name, class name, or prefix. The denylist to scan for:

```
WVCCI  PEAPH  AQM52  AQM-52  LSDA  CIM  VCLR  RAMD  MCQP
WCVCCIPositionSizer  WVCCISignalModel  WVCCIStrategy  WVCCIConfig
CIMFipComputeIndicator  CCCFundamentalsIndicator  RAMDRegimeScaledSizer
LotteryShortSqueezeControl  LotteryFundingStressControl  LotteryVixHaltControl
PEAPHSectorConcentrationControl  PEAPHPreAnnouncementExitControl
PEAPHMacroRegimeIndicator  PEAPHAttentionMetricsIndicator
PEAPHEarningsCalendarIndicator  VCLRMacroRegimeIndicator
build_wvcci_engine  rmc_composite  DQS  RAS
```

Rewrite pattern: replace the concrete class name with the generic pattern it represents. Examples:

| Before | After |
|--------|-------|
| `AQM52IndicatorSuite takes no constructor args` | `Indicator suites may have no constructor args — check the signature` |
| `WVCCI: pass-through enrich() for diagnostic columns` | `Pass-through enrich() when manifest specifies diagnostic columns from indicator suite` |
| `CCCFundamentalsIndicator: cumsum trick` | `Multi-quarter fundamentals_valid: fully vectorized cumsum pattern` |
| `PEAPH: OR-logic long_exit` | `Event-driven strategies: check implementation_notes for OR vs AND exit intent` |
| `build_wvcci_engine()` in examples | `build_X_engine()` or `build_<strategy_id>_engine()` |
| `LotteryFundingStressControl / LotteryVixHaltControl` | the generic "asymmetric halt" pattern description |

If a rewrite would strip ALL substance from the entry (e.g. the entry was ONLY saying "AQM52 does X"), delete instead.

### KEEP — verbatim

Keep an entry as-is only if it is:

- Framework facts (exact kwargs, import paths, ABC signatures, scope semantics)
- DB behavior observations (research DB coverage gaps, screener column availability)
- Environment facts (pytest install path, ruff location, venv structure)
- Tool behavior (past_ideas write parser quirks)
- General coding patterns that reference no specific strategy

## The critical entries to watch for

These are the specific bug-encoding patterns that caused the WVCCI clone failures. If any are present in the input, DELETE and replace with a halt instruction:

1. **"Upstream strategy/config may live in different directory from execution layer"** in `execution/memory.md` — teaches the execution builder to import the wrong strategy's classes. Replace with: *wiring.py MUST import from its own strategy_id's directory; if upstream result points elsewhere, that's a build failure — halt and re-run upstream*.

2. **"Template Scaffold Never Customized — Detection Pattern"** with advice to "fix the runner and accept the template's Sharpe" in `validation/memory.md` — pollutes past_ideas.md. Replace with: *detect template scaffold, report `build_failure`, do NOT tune*.

3. **"CIM-Class Strategy: Template Scaffold + Wrong MANIFEST = Always Fails"** with "best fix budget usage: patch runner" — same pattern as #2. Same replacement.

4. **"Distribution-Tail Signals Are an Open Territory"** or equivalent idea-generator claims of unexplored spaces — always check past_ideas.md before writing these. Replace with a generic "check past_ideas.md for prior attempts, distinguish pipeline-bug failures (genuinely unevaluated) from real signal failures (evaluated)" memory.

## Style rules for rewritten entries

- Keep the frontmatter shape: `--- date / title / topic ---`
- Title should describe the pattern, not the strategy (e.g. "Piecewise linear regime scale: use > not >=" not "VIX piecewise scale: use > not >= (WVCCI build)")
- Body should describe WHAT to do and WHY, not WHO did it. Strip "confirmed in WVCCI build", "caught by code review on PEAPH", etc. — the provenance isn't load-bearing.
- If two entries teach the same lesson with different strategy names, merge them into one generic entry.
- If an entry lists the DB behavior for many signal families (each as a separate memory), consolidate into one "research DB gaps requiring web-search pivot" entry with a bulleted list.

## Size targets

Rough post-audit size expectations per file:

- `idea_generation/memory.md`: ~100-120 lines (consolidate DB-gap entries)
- `architect/memory.md`: ~200-220 lines (most entries are productive framework patterns)
- `build/indicators/memory.md`: ~150-170 lines (remove superseded std_lib claims)
- `build/signals/memory.md`: ~85-95 lines (already lean, just strip names)
- `build/execution/memory.md`: ~160-170 lines (DELETE the upstream-directory entry)
- `validation/memory.md`: ~40-50 lines (rewrite the two coping entries)

If you end up significantly above these after a clean pass, re-audit — there's likely cruft left.

## Verification pass

After rewriting, run:

```bash
grep -En 'WVCCI|PEAPH|AQM52|AQM-52|LSDA|\bCIM\b|VCLR|RAMD|MCQP' <all six files>
```

Expected: zero matches. If any hit, go back and rewrite.

Also grep for the bug-encoding phrases:

```bash
grep -En 'may live in different directory|accept the template|fix the runner|best fix budget' <all six files>
```

Expected: zero matches.

## Execution checklist

- [ ] Read all six memory files
- [ ] Classify every entry KEEP/REWRITE/DELETE
- [ ] Rewrite each file in a single Write call (full replacement)
- [ ] Run the strategy-name grep — zero hits required
- [ ] Run the bug-phrase grep — zero hits required
- [ ] Report before/after line counts and KEEP/REWRITE/DELETE totals per file
- [ ] Specifically call out which bug-encoding entries were removed (the user wants to know these landed)

## Do not

- Do not edit `memory.md` files outside the six listed paths. Other packages (atlas, tools, data) have their own memory systems and are out of scope.
- Do not touch the skill's own memory — that's authored separately.
- Do not delete an entry just because it's long — length is not the metric. Productivity and strategy-agnosticism are.
- Do not invent framework facts. If an entry states something about the framework that you cannot verify (constructor kwargs, import paths, ABC signatures), leave it — it probably came from reading source during a real build. Only delete on clear supersession by a later entry.
- Do not merge entries across different memory files. Each agent's memory is scoped to its stage; cross-pollinating patterns into the wrong file creates confusion.
