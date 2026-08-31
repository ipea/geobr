---
paths:
  - ".claude/agents/**/*.md"
  - ".claude/skills/**/SKILL.md"
---

# Per-Agent Model Routing (architect/editor split)

**Match model tier to the cognitive demand of the work.** Reserve Opus for high-judgment work; route mechanical work to Haiku; default review/critique to Sonnet. Anthropic's [Apr 8 2026 "Decoupling brain from hands"](https://www.anthropic.com/engineering) endorses this pattern; Aider's architect/editor split is the canonical community shape.

## The 70/20/10 routing pattern

| Share | Tier | Use for |
|---:|---|---|
| ~70% | **Haiku 4.5** | Mechanical work — file renames, search-and-replace, roxygen boilerplate, NEWS/CHANGELOG formatting, simple grep / file lookups |
| ~20% | **Sonnet 4.6** | Review and critique — `r-reviewer`, `python-package-reviewer` |
| ~10% | **Opus 4.8** | High-judgment work — `r-package-reviewer`, `verifier` for non-trivial gates |

Set per-agent via `model:` in the agent's YAML frontmatter:

```yaml
---
name: r-reviewer
model: sonnet      # was: inherit
---
```

Set per-skill via the same field in `SKILL.md` frontmatter. Inheritance is fine for skills whose work spans tiers (e.g. `/deep-audit` dispatches a mix).

## The effort axis (the first cost lever)

Model tier is the second cost lever; **effort is the first.** Every model runs at an effort level (`low / medium / high / xhigh / max`), and lowering effort is cheaper than dropping a tier — reach for it first.

- **Opus 4.8 defaults to `high`**, and its `high` does roughly what Opus 4.7's `xhigh` did, for fewer tokens. Do **not** reflexively set `xhigh`.
- **Mechanical work** (Haiku tier) → `low` / `medium`.
- **Review and judgment** (Sonnet / Opus) → `high` (the default).
- **The hardest runs** (deep refactors, a full `/deep-audit` sweep) → `xhigh`; `ultracode` (xhigh + dynamic workflows) for repo-scale autonomous tasks.
- Reserve `max` for the rare case where you've verified `xhigh` was insufficient.

Set per skill/agent with the `effort:` frontmatter field. Some skills ship at `effort: high` for genuinely hard gates (e.g. `/r-package-check`, `/deep-audit`). Match effort to the cognitive demand the same way you match model tier — and tune effort before you swap models.

## Where Fable 5 fits — and where it does not

**Fable 5** (GA 2026-06-09) is the most capable model in Claude Code — and this rule deliberately does **not** route any of the template's fleet to it. Two verified reasons:

1. **Cost discipline.** Fable 5 is $10/$50 per MTok vs Opus 4.8's $5/$25 — a flat 2× on exactly the judgment tier the 70/20/10 split exists to guard. The reviewer and verifier agents here are bounded, single-sitting tasks; Fable's premium is priced for *long-horizon, larger-than-one-sitting* autonomous work, which the fleet is not.
2. **Protocol maturity.** In one launch-week session's fan-out, Fable 5 subagents failed the forced structured-output tool protocol 28/28 times vs 0 observed failures on Opus 4.8 — a single-session signal, not a benchmark, but exactly the failure mode that matters here: in a fan-out fleet, a silent tool-protocol failure means a review lens returns *nothing*. (Same logic as the "don't push Opus down a tier" anti-pattern: a too-immature judge is as bad as a too-cheap one.)

**Where Fable 5 *is* the right call:** your own interactive sessions on the hardest long-horizon work — a multi-day refactor, a deep research synthesis you'll steer by hand — where you are in the loop to catch a protocol hiccup and the task actually exploits the model's horizon. Select it per-session (`/model fable`); leave the fleet's `model:` pins alone. Re-evaluate at Fable point releases (the protocol gap is the kind of thing that gets fixed); when it does, the high-judgment tier is the natural first candidate.

**Cost reality check:** a full `/deep-audit` sweep runs a meaningful fraction of a dollar-denominated token budget at Opus prices; doubling the judgment tier doubles that line item with no quality evidence yet. When cost-constrained, drop *effort* first (the first lever, above), then tier — never the reverse.

## Why this matters

Cost reduction on routed skills is typically **50–80%** with no quality loss on the mechanical tier. The cache-TTL change (5-min default in 2026; Claude subscriptions get 1-hour automatically, API keys opt in) made multi-turn pipelines on API keys materially more expensive; per-agent routing recovers that lost ground without sacrificing the high-judgment lens where it matters.

## Routing recipe per task type

### Mechanical (Haiku 4.5)

- **Proofread fix application** (when the fix is "replace X with Y" mechanically).
- **Roxygen boilerplate / `@template` wiring** (mechanical doc edits under `r-package/R/`).
- **`NEWS.md` / `CHANGELOG.md` bullet formatting** and changelog tidying.
- **File rename / search-and-replace operations.**

### Review / critique (Sonnet 4.6)

- **R code review** (`r-reviewer`).
- **Python package review** (`python-package-reviewer`) — enforces `python-package-conventions.md`.
- **Doc/NEWS prose inspection** — vignettes, README, NEWS wording.

### High-judgment (Opus 4.8)

- **R package reviewer** (`r-package-reviewer`) — CRAN-policy judgment is the release gate; do not demote.
- **Verifier** (`verifier`) on non-trivial gates.

## When inheritance still makes sense

- A new agent you haven't profiled yet — start with `model: inherit`, run once, then route.
- An agent whose work spans tiers in the same invocation (rare; usually a sign the agent should be split).
- One-shot test agents you'll discard.

## Anti-pattern: pushing Opus down a tier

Do **not** demote `r-package-reviewer` or `verifier` to Haiku to save cost. These are the agents that protect the package from hallucinated claims and from CRAN-policy violations. The cost of one false-positive PASS — a broken submission, or a package pulled from CRAN — is materially higher than running Opus on every check.

## Anti-pattern: self-as-architect-and-editor pairing

Aider's pattern uses one model as both planner and executor. We deliberately do not — same-model self-pairings produce correlated errors. Our split runs **different tier** on architect (Opus) vs. editor (Haiku/Sonnet); the diversity is part of the cost story.

### Corollary: challenger ≠ auditor tier (guardrail, not a build)

If a future contributor ever adds an explicit *challenger → auditor* step (e.g., an "audit-then-score" / "ground truth is a process" verifier where one agent argues against a claim and a second adjudicates), the challenger **must** run on a different tier than the auditor — two same-tier LLMs share blind spots, so a same-tier challenger launders correlated errors as independent confirmation. This costs nothing to honor today; it exists so the diversity property isn't quietly lost when the split is built. **This is a constraint on a hypothetical future step, not a green light to build it.**

## How `/commit` uses this rule

`/commit`'s pre-commit verifier currently runs at the orchestrator's tier. When this rule's pattern matures (Sonnet 4.6 reliably catches most issues), the verifier can be routed to Sonnet by default with Opus reserved for `--strict` mode. Pending evaluation.

## Cross-references

- [`orchestrator-protocol.md`](orchestrator-protocol.md) — the fan-out primitives these tiers are assigned across.
