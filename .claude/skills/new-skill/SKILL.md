---
name: new-skill
description: Scaffold a new skill that follows this repo's conventions — interviews for purpose, trigger phrases, and tool needs, then writes `.claude/skills/<name>/SKILL.md` from the skill template with frontmatter and body that pass the integrity gates on first try. Use when user says "write a skill", "scaffold a skill", "create a new skill", "I keep doing X, make it a skill", "new slash command", or "turn this workflow into a skill". NOT for capturing a one-off session discovery — that is `/learn`.
argument-hint: "[skill-name (kebab-case)] [--from-learn] [--dry-run]"
allowed-tools: ["Read", "Write", "Glob", "Grep", "Bash"]
disable-model-invocation: true
effort: medium
---

# /new-skill — Author a Convention-Compliant Skill

Scaffold a new skill the way this repo's gold-standard skills are written: a **deep module behind a simple interface** (Ousterhout, *A Philosophy of Software Design* — "deep modules": a small surface that hides substantial implementation). The user supplies a fuzzy intent; this skill interviews it into a tight spec, then writes `.claude/skills/<name>/SKILL.md` with frontmatter and body that are mutually consistent, so it satisfies the repo conventions without a second pass.

Adapted from the *write-a-skill* pattern in [mattpocock/skills](https://github.com/mattpocock/skills), reshaped to this repo's frontmatter, section, and gate conventions.

## When to use

- You keep re-explaining the same 3+ step workflow to Claude and want it captured as a reusable slash command.
- You need a domain-specific check or output format (citation style, replication gate, a new review lens).
- You want a new skill that is consistent with the 40+ siblings in `.claude/skills/` — same sections, same cross-reference style, same gate-passing frontmatter.

**Use `/learn` instead** when you just discovered something non-obvious *this session* and want it preserved — `/learn` captures a discovery; `/new-skill` deliberately designs an interface. With `--from-learn`, this skill upgrades a `/learn`-shaped stub into a full convention-compliant skill.

## Phases

### Phase 0 — Resolve the name and check for collisions

1. Take the kebab-case name from `$0` (or ask). Reject non-kebab-case, names that collide with an existing `.claude/skills/<name>/`, or names that shadow a built-in (`commit`, `learn`, …) — `ls .claude/skills/` and stop if taken.
2. Read [`templates/skill-template.md`](../../../templates/skill-template.md) for the canonical structure and the frontmatter-field reference.
3. Skim 2-3 sibling skills near the intended domain (e.g. `Glob .claude/skills/*/SKILL.md`, then `Read` the closest matches) so the new skill borrows real conventions, not invented ones.

### Phase 1 — Interview (collect everything *before* writing)

A skill cannot stop to ask mid-write, so gather all interactivity up front (the [orchestrator-protocol.md](../../rules/orchestrator-protocol.md) RUN_CONFIG discipline). Ask, in one batch:

1. **Purpose** — one sentence: what does it accomplish and why does it exist?
2. **Trigger phrases** — the 4-7 quoted phrases a user would actually say. These become the `description`'s "Use when…" clause and are what makes the skill auto-discoverable.
3. **Inputs / arguments** — positional args and any **flags** (each must become a documented `--token`).
4. **Tools** — does the body Read? Write? Grep/Glob? run `Bash`? fan out to a subagent (the `Task` tool)? hit the web via `WebSearch`/`WebFetch`? Only declare what it actually uses.
5. **Output** — a written file (where?), a chat report, or an in-place edit? Should it be read-only?
6. **Scope boundary** — the one or two things it explicitly does NOT do (and which sibling owns those).

Echo a one-paragraph **design brief** back for confirmation before writing.

### Phase 2 — Write the SKILL.md (deep module, simple interface)

Write `.claude/skills/<name>/SKILL.md` from the template, with these gold-standard sections:

- Frontmatter: `name`, `description` (third person, with the quoted trigger phrases), `argument-hint`, `allowed-tools`, `effort`. Add `disable-model-invocation: true` if it writes a persistent, load-bearing file (template's "when to disable" rule).
- Body sections: **When to use**, numbered **Phases** (or Steps), an **Output / report format**, **Exit behavior**, **Cross-references** (to real sibling files), **What this skill does NOT do**, and a **## Flags** section if any flags are advertised.
- Keep the *interface* small (a few args) and the *implementation* deep (the phases carry the weight) — resist exposing a knob for every internal choice.

### Phase 3 — Enforce parity so the gates pass first try

There is no checker script in this repo, so these parities are **your** responsibility before you hand the skill back. `/deep-audit` Phase 0 re-checks them later; getting them right here is what keeps that audit quiet:

- **Flag parity (both directions).** Every flag in `argument-hint` MUST appear in the body as a bare-backticked token, and every flag documented in the body MUST appear in `argument-hint`. So `--from-learn` and `--dry-run` are listed in the hint *and* described under `## Flags`. A stale hint flag fails the gate as surely as a missing one.
- **allowed-tools parity.** The body may only invoke tools listed in `allowed-tools`. If a phase fans out to a subagent (the `Task` tool), that tool must be in the list; if it never does, do not list it. This skill lists exactly `Read, Write, Glob, Grep, Bash` — the tools its phases use, and no subagent fan-out.
- **Anchor resolution.** Internal `[text](path#anchor)` links must resolve — only link to headings that exist.

Re-read the finished frontmatter against the body and confirm all three parities by hand before declaring done.

### Phase 4 — Remind: register the surface

The skill is NOT discoverable to a reader until it is listed. `CLAUDE.md` carries an "Installed Workflow Surfaces" inventory that must match `ls .claude/skills/` exactly — a skill absent from it is invisible, and `/deep-audit` Phase 0 flags the mismatch.

REMIND the user to:

1. Add `/<name>` to the **CLAUDE.md** "Installed Workflow Surfaces" list, under the right grouping.
2. If the skill is user-facing enough to document publicly, mention it in the relevant `README.md`.
3. Re-run the Phase 0 mechanical checks in [`/deep-audit`](../deep-audit/SKILL.md) — they must come back clean.

Print the ready-to-paste inventory line so the user can drop it in.

## Output / report format

- A new file at `.claude/skills/<name>/SKILL.md`.
- A chat summary: the resolved name, the design brief, the verified parities, and the paste-ready CLAUDE.md inventory line.
- With `--dry-run`: emit the proposed SKILL.md to chat only and write nothing.

## Exit behavior

- **Skill written, parities verified:** exit 0 with the path, the inventory line, and the explicit "now register it in CLAUDE.md" reminder.
- **Name collision or non-kebab-case:** stop in Phase 0 with the conflict named; write nothing.
- **A parity check fails:** fix in-place before returning; never hand back a skill that fails its own conventions.
- **`--dry-run`:** print the draft, write nothing, exit 0.

## Flags

- `--from-learn` — Seed the interview from an existing `/learn`-style stub (or the current session's discovery) and upgrade it into a full convention-compliant skill rather than starting blank.
- `--dry-run` — Produce the SKILL.md content in chat for review without writing it to disk or touching any surface table.

## Cross-references

- [`templates/skill-template.md`](../../../templates/skill-template.md) — the canonical structure, frontmatter-field reference, and the "when to set `disable-model-invocation`" rule this skill follows.
- [`.claude/skills/learn/SKILL.md`](../learn/SKILL.md) — capture a session discovery (the lighter sibling); `--from-learn` upgrades its output.
- [`.claude/skills/r-package-check/SKILL.md`](../r-package-check/SKILL.md) — a gold-standard skill to imitate (phased, verification-gated, explicit exit behavior).
- [`.claude/rules/orchestrator-protocol.md`](../../rules/orchestrator-protocol.md) — why the interview collects all interactivity *before* writing.
- [`.claude/skills/deep-audit/SKILL.md`](../deep-audit/SKILL.md) — Phase 0 re-checks the parities this skill is built to satisfy on the first try.

## What this skill does NOT do

- **Capture a session discovery** — that is [`/learn`](../learn/SKILL.md). This skill designs an interface; `/learn` records a finding.
- **Edit the CLAUDE.md inventory for you.** It *prints* the line and reminds you; registering it is a deliberate human step so the surface is never silently satisfied.
- **Write agents, rules, or hooks.** It scaffolds a skill only; an agent goes in `.claude/agents/`, a rule in `.claude/rules/`.
- **Commit anything.** Branch / PR / merge is [`/commit`](../commit/SKILL.md)'s job.
