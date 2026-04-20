---
name: condense-past-ideas
description: Condense the fund's past_ideas.md log into concise one-paragraph-per-strategy summaries to prevent context bloat when the file is loaded into agent prompts. Use when the user asks to shrink, condense, compact, or summarize past_ideas.md, or when the file has grown beyond ~100 lines. Target path is projects/fund/src/prophitai_fund/past_ideas.md.
license: Apache-2.0
metadata:
  author: michael-laret
  version: "1.0"
---

## Overview

`past_ideas.md` is loaded into every fund agent prompt (idea generator, architect, validator). Verbose multi-section entries (Description, Edge, Universe, Entry & Exit, Risk Management, Research Backing, Research Results) for each strategy bloat the context window linearly with strategy count. This skill rewrites the file so each strategy keeps its YAML frontmatter and gets a single tight paragraph covering what it was and why it failed.

## Target file

`projects/fund/src/prophitai_fund/past_ideas.md` (resolve relative to repo root).

## Procedure

1. Read the current `past_ideas.md`.
2. Split into strategy blocks — each block starts with a `---` line followed by `name: ...` and ends at the next `---` line that starts a new block (or EOF).
3. For every strategy block, produce an output block of exactly this shape:

   ```
   ---
   name: <preserve verbatim>
   category: <preserve verbatim>
   date: <preserve verbatim>
   verdict: <preserve verbatim>
   ---

   <single paragraph, 3–7 sentences>
   ```

4. Overwrite `past_ideas.md` with the concatenation of output blocks, separated by a single blank line.

## What the paragraph must contain

Pack the following into one paragraph, in roughly this order:

1. **One-line signal description**: what the strategy trades, rebalance frequency, direction (long-only / long-short / L/S), and the core signal or composite (e.g. "residual alpha momentum ranked by z(alpha_vs_spy) + z(alpha_vs_sector) + z(IR)").
2. **Primary academic citation** if it's load-bearing for why the idea was proposed (e.g. "per Blitz-Huij-Martens 2011" or "Frazzini-Lamont 2007 EAP"). One citation max — not a literature review.
3. **Failure classification** — this is the most important part. Distinguish two failure modes explicitly:
   - **Pipeline bug** — files were template scaffold, MANIFEST.json leaked from another strategy, builders wrote to wrong directory, wiring imported a different strategy's classes, zero trades from a structural mismatch. Say explicitly that **the signal was never really tested** and the concept remains unevaluated.
   - **Real signal failure** — strategy was built correctly with its own code and classes, backtest ran on the intended signal, but results missed the Sharpe threshold. Include the best Sharpe and, if positive, the per-trade edge / win rate / total return — those tell future agents whether the idea deserves a retry.
4. **Actionable structural issue** if the validator identified one (e.g. "universe was 50 tickers vs IDEA.md's 800-1400", "short-leg joint filters returned 3 tickers", "SPY halt fired during bear markets removing active earnings seasons"). Skip this if no clear structural issue was noted.
5. **Retry verdict**: "signal concept unevaluated" for pipeline bugs, "worth retesting with [fix]" for real failures with positive per-trade edge, no retry note for real failures with no edge.

## What to drop

- Full Research Backing citation lists (keep at most one primary citation)
- Universe filter lists (replace with a short phrase if the universe shape mattered for failure)
- Entry/Exit rule enumerations (E1, E2, E3...)
- Risk Management sizing details
- Flip/fail conditions
- Macro regime paragraphs
- Orthogonality justifications vs existing strategies
- All full backtest run tables — keep only the best Sharpe and any supporting edge stats

## Preserve verbatim

- Every YAML frontmatter field (`name`, `category`, `date`, `verdict`)
- The `---` delimiter lines
- The ordering of strategies in the file (chronological, oldest first)
- The emoji-free plain-text style used in existing condensed entries

## Example transformation

**Before** (~70 lines for one strategy, with Description, Edge, Universe, Entry & Exit, Risk Management, Research Backing, Research Results sections):

> ### Description
> A monthly-rebalancing, long-only US equity momentum strategy that selects winners based on the SHAPE of the information path... [several hundred words] ...
> ### Edge
> PRIMARY SIGNAL: Continuous Information Score (CIS) = 0.40*z(-frog_in_pan) + ... [several hundred more words] ...
> [... five more sections ...]
> ## Run Table (12 total)
> | Run | ... | Sharpe | ... |
> | 0 | ... | -0.26 | ... |
> [... 11 more rows ...]

**After** (3–7 sentences):

> Monthly long-only US equity momentum selecting winners by information-path smoothness per Da-Gurun-Warachka (2014) Frog-in-the-Pan: composite of frog_in_pan, equity_curve_r2, zero_return_days_pct, and momentum_12m_1m_skip. Low-FIP is by construction a momentum-crash precursor filter. Failure was a pipeline build bug: strategy files were unmodified template scaffold, MANIFEST.json belonged to WVCCI, and Stages 4+5 wrote nothing CIM-specific. Best Sharpe 0.31 from the template EMA/RSI crossover run on CIM's screened universe. Signal concept unevaluated.

## Execution checklist

- [ ] Read file, confirm every strategy has frontmatter with `name`/`category`/`date`/`verdict`
- [ ] Produce one condensed paragraph per strategy
- [ ] Classify failure mode (pipeline bug vs real signal failure) for every `verdict: failed` entry
- [ ] Include best Sharpe for every tested strategy
- [ ] Write the file in one Write call (full overwrite)
- [ ] Report before/after line count to the user

## Do not

- Do not drop strategies. If the file has 50 strategies, the output has 50 strategies.
- Do not merge or deduplicate strategies even if they're thematically similar — each entry is a historical record.
- Do not add headers (`### Description`, `## Summary`, etc.) inside the paragraph.
- Do not use bullet points inside the paragraph.
- Do not invent a failure classification if the original text is genuinely ambiguous — say "failure mode unclear from log" and leave it for the user.
