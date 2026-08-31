---
name: checkpoint
description: Save a structured state snapshot the next session can resume from — active plan, decisions and why, file pointers with line numbers, open questions, next 1-3 actions, and what to deliberately forget. Use before a break, a model switch, a collaborator handoff, or when context is approaching auto-compaction. Use when the user says "checkpoint", "save state", "where am I", "compress", "distil this session", "wrap up for handoff", "before we hit auto-compact".
author: geobr
version: 2.0.0
argument-hint: "[short-topic-slug] [--no-memory]"
disable-model-invocation: true
allowed-tools: ["Read", "Write", "Glob", "Grep", "Bash"]
---

<!-- Merged in v2.0.0 from the former /checkpoint and /compress-session, which solved the same
     problem at two moments. The stop-point shape is adapted from Hugo Sant'Anna's clo-author
     v4.2.0; the "discarded as noise" section is from Breunig's long-context failure modes
     (dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) — naming failed
     hypotheses explicitly stops them being re-quoted by a future session. -->

# `/checkpoint` — distil state, don't truncate it

Auto-compaction is **lossy**: it keeps recent turns and drops earlier ones, preserving no record of
what was *decided*. This skill writes the structured alternative — a file the next session (yours, a
fresh context, or a collaborator) can resume from in under a minute.

The narrative `quality_reports/session_logs/` stays separate: **session log = what happened**,
**checkpoint = state to resume from**. The checkpoint links to the log; it does not re-tell it.

## When to use

- Before a break, a model switch, or the end of a working day.
- When context is approaching auto-compaction and mid-session decisions would otherwise be lost.
- Before handing the repo to a collaborator.
- After a long debugging detour, so the dead ends are recorded as dead ends rather than carried
  forward as live hypotheses.

**Not** for the narrative (that is the session log), for commit messages (`/commit` writes its own),
or for resetting context (`/clear`).

## Phase 1 — Gather state

Read in this order; if something is missing, record `(none on disk)` rather than inventing it:

```bash
ls -t quality_reports/plans/*.md | head -1          # active plan + its status
ls -t quality_reports/session_logs/*.md | head -1   # latest narrative log
git branch --show-current; git log --oneline -10; git status -s; git diff --stat HEAD
```

Also read `MEMORY.md` so Phase 3 does not propose a duplicate, and capture any in-flight TodoWrite
items.

## Phase 2 — Write the checkpoint

Write to `quality_reports/checkpoints/YYYY-MM-DD_<slug>.md`. Derive the slug from `$ARGUMENTS`, or
from the active plan's title if absent (say which you used). Keep it under ~80 lines — if state
does not fit, the *plan file* is the right home and the checkpoint should point at it.

```markdown
---
date: YYYY-MM-DD
branch: <branch>
plan: <path to active plan, or (none)>
session-log: <path to latest log, or (none)>
status: in_progress | paused | ready-to-merge
why-now: break | model-switch | handoff | approaching-compaction | accumulated-noise
---

# Checkpoint — <topic>

## Goal
<one sentence: what this work is trying to accomplish>

## Where I am
<one short paragraph or a few bullets: last completed step, current step, what is not yet done>

## State
- **Last commit:** <sha + subject>
- **Working tree:** <clean | N modified files>
- **Gate status:** <R suite / Python suite: passed, failed, or not run — and why>

## File pointers
<3-8 concrete `path:line` references where the next session resumes>
- `r-package/R/utils.R:349` — download_parquet, failure branch under review

## Decisions and why
<2-5 bullets of reasoning that would NOT be obvious from the diff. Skip if none; do not pad.>

## Open questions
<Q1, Q2 … each with where it blocks>

## Discarded as noise
<Failed hypotheses, abandoned approaches, debugging dead ends — and why each failed.
Naming them stops a future session re-quoting them as live leads. Skip if the session was clean.>

## Next 1-3 actions
1. <imperative, concrete, with a file pointer>

## Resume prompt
> Resuming from `quality_reports/checkpoints/<filename>`. Read it, then start at action 1.
```

## Phase 3 — Propose memory updates (skip with `--no-memory`)

Surface **0-3** candidate `[LEARN]` entries. Propose; never write to `MEMORY.md` unappproved:

```
[LEARN:category] <one-line headline>
Why: <what makes this non-obvious>
Apply where: <the future situation it changes>
```

On approval, append to `MEMORY.md` in the existing format. More than three candidates usually means
the session log is behind — say so instead of padding the list.

## Phase 4 — Report

```
✓ Checkpoint: quality_reports/checkpoints/YYYY-MM-DD_<slug>.md
  Branch: <branch>   Status: <status>   Why now: <why-now>
  Plan: <path or none>   Open questions: <n>   Discarded: <n>
  Resume: claude --continue, then read the checkpoint and start at action 1.
```

## Anti-patterns

- **Do not copy the conversation in.** Distillation is the whole point.
- **Do not let "Discarded as noise" recur.** The same dead end across three checkpoints is a
  structural problem — fix the docs or the workflow instead of re-discarding it.
- **Do not write a checkpoint with no plan and no pointers.** That is a note, not a resumable state;
  enter plan mode first.

## Cross-references

- [`../../rules/session-logging.md`](../../rules/session-logging.md) — the narrative companion.
- [`../../rules/plan-first-workflow.md`](../../rules/plan-first-workflow.md) — the plan this reads.
- [`../../../templates/decision-record.md`](../../../templates/decision-record.md) — for *why A over
  B*, not *where we are*.
