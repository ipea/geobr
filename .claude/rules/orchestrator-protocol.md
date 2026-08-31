# Orchestrator Protocol: the review runtime

**The review-fix loop is a real runtime contract, expressed with the primitive every Claude Code session has: the `Task` subagent.** Skills fan out to forked reviewers, reduce their *structured* findings ([`orchestration-schemas.md`](../references/orchestration-schemas.md)) through a deterministic gate, judge with a hallucination guard, and loop until dry. What is *not* automatic is the **trigger**: nothing launches this loop on its own — the user (or a skill invocation) starts it. That boundary is deliberate (see "What is NOT automatic").

## The loop (the contract)

```
Skill invoked (with a RUN_CONFIG)
  │
  Step 1: IMPLEMENT / DRAFT
  │
  Step 2: VERIFY — compile, render, check outputs   (retry ≤ 2)
  │
  Step 3: FAN-OUT REVIEW — parallel forked reviewers, each returns FINDINGs
  │
  Step 4: REDUCE + JUDGE — stack scorecards; gate predicate → verdict;
  │        run the post-judge hallucination gate on judge-introduced CRITICALs
  │
  Step 5: FIX — apply critical → major → minor (with approval)
  │
  Step 6: SCORE — test-suite / check roll-up
  │
  └── converged?  (a round adds 0 new CRITICAL/MAJOR — see loop-until-dry)
        YES → present summary
        NO  → back to Step 3, in FRESH context
              (hard fallback cap reached → present with remaining issues)
```

## The runtime primitives

These four primitives are the runtime. Every fan-out skill is a composition of them; none should re-describe them in prose — they reference this section and [`orchestration-schemas.md`](../references/orchestration-schemas.md).

### 1. Fan-out

Spawn the reviewers **in parallel in a single message** — N `Task` calls, each `context: fork` so the main thread stays clean and each reviewer gets full budget for its lens. `Task` subagents are the **portable primitive**: they exist in every Claude Code install, so the template depends on them, not on the session-gated Workflow tool. *(Where the Workflow tool is available — e.g. an `ultracode`/dynamic-workflow session — a skill may use it for the same fan-out→reduce→judge shape; treat that as an optional accelerator, never a requirement.)*

Which agent fills which lens, at which model tier, is in [`model-routing.md`](model-routing.md); the full global fleet is catalogued at `~/.claude/references/agent-fleet.md`.

### 2. Reduce (typed, not eyeballed)

Each reviewer returns `FINDING`s and a `SCORECARD` in the shared schema. The synthesizer **stacks typed objects** and applies the **gate predicate** — `CRITICAL>0 → BLOCK`, `MAJOR>0 → REVISE`, else `PASS`. The verdict is a deterministic function of the findings, not a re-judgment of the artifact.

### 3. Judge + hallucination gate

A synthesizer/editor may freely *downgrade* or *de-duplicate* lens findings, but any **CRITICAL it introduces that no lens raised** must survive the post-judge hallucination gate ([`orchestration-schemas.md` §4](../references/orchestration-schemas.md)): re-verify it in a fresh `verifier` fork; if it can't be grounded, drop it to `[JUDGE-HALLUCINATED]` and recompute. This is what makes an autonomous review trustworthy next to a credibility-sensitive artifact.

### 4. Loop-until-dry

Replace bespoke "max 5 rounds" stopping logic with **convergence**: stop after **2 consecutive dry rounds** (a round that adds 0 new CRITICAL/MAJOR findings, deduped on `location`+`finding`). Guards:

- **Fallback cap** — `RUN_CONFIG.max_rounds` (default 5) bounds a non-converging loop.
- **Two-strikes** — the *same* finding surviving rounds N and N+2 is escalated to the user, not patched a third time ([`summary-parity.md`](summary-parity.md)).
- **Spend cap** — `RUN_CONFIG.spend_cap_tokens` (default ~500k) warns-and-asks; it is a spend ceiling, not a context limit (each re-audit is fresh).
- **Runaway backstop** — never exceed the harness's hard subagent cap; cost-pilot any ≥7× fan-out on one section before a full sweep.

### RUN_CONFIG: collect interactivity *before* launch

A forked subagent cannot stop to ask the user a question. So every interactive choice a fan-out needs — review scope, N reviewers, fresh-context flag, whether a failing check blocks — is gathered **before** the fleet spawns, echoed back as the **Pre-Flight Report**, and only then launched. Schema: [`orchestration-schemas.md` §5](../references/orchestration-schemas.md). An unresolved required field halts *before* launch, never mid-run. This is what lets a fan-out keep its interactivity inside a no-mid-run-input runtime.

## Where the runtime is implemented

> **Scoped to geobr.** This repo carries a package-development subset of the fleet. The
> slide/manuscript skills that once filled this table (`/slide-excellence`, `/qa-quarto`,
> `/review-paper`, `/create-lecture`, `/data-analysis`) are **not installed here** — the full
> set remains at `~/.claude/`.

| Skill | Primitives | Notes |
|-------|-----------|-------|
| `/r-package-check` | verify → review (`r-package-reviewer`) → triage | R release gate — `R CMD check --as-cran` on `r-package/` |
| `/py-package-check` | verify → review (`python-package-reviewer`) → triage | Python release gate — mirrors `Python-CMD-check.yaml`. Needs a Python toolchain |
| `/parity-check` | single-lens read-only comparison | R↔Python API drift; report-only, no fan-out |
| `/commit` | verify (Step 0 touched-package gate) | Halts on a failing gate. No `quality_score.py` in this repo — the gate is the test suite |
| `/deep-audit` | mechanical checks → fan-out → fix, **loop-until-dry** | Repo-wide consistency |
| `/review-r` | single-lens read-only review | `.R` code quality; pairs with `/r-package-check` |
| `/diagnose` | ladder (environment → cache → tag → data → code) | Root-cause loop; environment rungs before source |

## What is NOT automatic

- **No post-plan-approval trigger / no daemon.** Exiting plan mode does not launch a fix loop, and there is no background service that points the runtime at an artifact unattended. A multi-agent fix loop with no human in it, run against a submission, shared data, or a co-author's draft, is exactly the failure mode we refuse — the loop is always user/skill-initiated. **This is a documented non-goal, not a missing feature.**
- **No repo-wide orchestrator chaining.** Skills compose the primitives within their own scope; they do not invoke each other without an explicit call.
- **Quality gate enforcement.** There is no `quality_score.py` and no installed pre-commit hook in this repo. The gate is `/commit` Step 0 — the touched package's test suite — which halts and asks rather than blocking. A direct `git commit` bypasses it entirely; that is a known, accepted gap, not a claim of enforcement.

## "Just Do It" mode

When the user says "just do it" / "handle it" (within an already-invoked skill):

- Skip the final approval pause for the current skill; still run the full fan-out → reduce → judge → loop-until-dry; still present the summary.
- **Do NOT treat this phrase as commit authorization.** Commits require an explicit `/commit` or unambiguous request — see [`.claude/skills/commit/SKILL.md`](../skills/commit/SKILL.md).

## Cross-references

- [`.claude/references/orchestration-schemas.md`](../references/orchestration-schemas.md) — FINDING / SCORECARD / RUN_CONFIG / hallucination-gate contracts.
- [`.claude/rules/model-routing.md`](model-routing.md) — the reviewer fleet + model tiers.
- [`.claude/rules/plan-first-workflow.md`](plan-first-workflow.md) — when to enter plan mode before invoking a skill.
