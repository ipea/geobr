# Orchestration Schemas (the review runtime's data contracts)

The skills that fan out to reviewer subagents (here: `/deep-audit`, `/r-package-check`, `/py-package-check`, `/parity-check`) used to describe their findings as free-form markdown the synthesizer re-parsed by eye. This file is the **shared structured contract** they reduce over instead — so a synthesizer counts typed objects, a gate predicate is a deterministic check, and the same severity vocabulary means the same thing in every skill.

This is a **reference**, not a runtime: a Claude Code session has no JSON validator in the loop. The schemas are the *target shape* each reviewer subagent returns (as a fenced ```yaml block at the end of its report) and the synthesizer reads. See [`.claude/rules/orchestrator-protocol.md`](../rules/orchestrator-protocol.md) for how the fan-out → reduce → judge → loop-until-dry runtime uses them.

---

## 1. `FINDING` — one issue a reviewer raises

Every reviewer subagent (lens, referee, critic, auditor) emits a list of findings in this shape:

```yaml
findings:
  - id: F1                       # stable within this run (lens-prefixed is fine: M1, P3)
    lens: methods                # the reviewing lens / dimension / agent name
    severity: CRITICAL           # CRITICAL | MAJOR | MINOR   (the ONE vocabulary)
    location: "Sec 4.2, Table 2 col 3"   # where in the artifact (page/slide/line/cell)
    finding: "Identification rests on conditional PT but the text claims unconditional."
    evidence: "p.11 'parallel trends holds unconditionally' vs Eq.(4) conditions on X_i."
    recommendation: "State the conditional PT assumption explicitly, or drop the covariates."
    change_my_mind: "A sentence in Sec 4 reconciling Eq.(4) with the unconditional claim."
    confidence: high             # high | medium | low  — the reviewer's own certainty
```

**Severity is the single cross-skill vocabulary.** Map every skill's local words onto it:

| Local term (skill) | FINDING severity |
|---|---|
| FATAL / desk-reject-worthy / hard-gate failure | CRITICAL |
| Major Concern / "blocks submission" / Visual-Regression | CRITICAL or MAJOR (use CRITICAL if it blocks) |
| Minor Concern / polish / Low | MINOR |

- `change_my_mind` is required on every CRITICAL/MAJOR (the referee "what would change my mind" ask).
- `confidence` is for the judge/verifier, not the author — a `low`-confidence CRITICAL is a prime candidate for the hallucination gate (§4).

## 2. `SCORECARD` — a reviewer's aggregate

Each reviewer closes its report with a one-row scorecard; the synthesizer stacks them:

```yaml
scorecard:
  lens: methods
  critical: 1
  major: 3
  minor: 5
  score: 6            # 0–10, the reviewer's holistic read of its own lens
  verdict: REVISE-MAJOR   # SUBMIT | REVISE-MINOR | REVISE-MAJOR | REJECT  (artifact-level lenses)
```

For parity/gate skills (`qa-quarto`), the lens verdict is the hard-gate roll-up: `APPROVED` iff every hard gate passes (zero CRITICAL), else `BLOCKED`.

## 3. Gate predicates (how `reduce` decides)

The synthesizer's verdict is a **deterministic function of the typed findings**, not a re-judgment:

| Predicate | Rule |
|---|---|
| **PASS / APPROVED** | `sum(CRITICAL) == 0` across all lenses (and, for gate skills, every hard gate true) |
| **REVISE** | `sum(CRITICAL) == 0` and `sum(MAJOR) > 0` |
| **BLOCK / FAIL** | `sum(CRITICAL) > 0` |
| **converged (loop-until-dry)** | a round produces **0 new** CRITICAL/MAJOR findings (deduped by `location`+`finding`) |

"New" is measured against the running set of already-seen findings, deduped on `(location, finding)` — so a critic re-flagging an unfixed issue does not count as progress, and a fixer silently re-introducing one does not hide.

## 4. Post-judge hallucination gate (the synthesizer cannot invent CRITICALs)

A synthesizer/editor/judge reduces lens findings — it must not **introduce** a blocking claim no lens raised. (The audit found `editor.md` could desk-reject on a reason neither referee gave.) The gate:

1. After the judge produces its verdict, diff its CRITICAL/desk-reject reasons against the union of lens `findings`.
2. Any CRITICAL the judge introduced that is **not traceable** to a lens finding is a **candidate hallucination**.
3. Re-verify each candidate in a **fresh forked context** — spawn `verifier` (`Task`, `context: fork`) with the claim + the artifact location it cites.
   - Verifier confirms (grounded in a quote/location) → keep the CRITICAL; annotate `[JUDGE-ADDED, verified]`.
   - Verifier cannot ground it → **drop it to a flagged note**, tag `[JUDGE-HALLUCINATED]`, and **recompute the verdict** under §3 without it.
4. A judge may always *downgrade* or *de-duplicate* lens findings freely; it may only *introduce* a blocking finding that survives the gate.

This is cheap (it runs only on judge-introduced CRITICALs, usually 0–2) and it is the single most important guard for trusting an autonomous review near a credibility-sensitive artifact.

## 5. `RUN_CONFIG` — the pre-run input contract

A fan-out runtime collects every interactive choice **before** launch, so no subagent stalls waiting on the user mid-run (subagents cannot prompt). See `orchestrator-protocol.md` → "RUN_CONFIG".

```yaml
run_config:
  artifact: path/to/manuscript.tex        # what is being reviewed
  mode: peer                              # default | adversarial | peer | seven-pass | excellence | audit
  journal: QJE                            # --peer: resolved against journal-profiles.md (else null)
  dispositions: [SKEPTIC, MEASUREMENT]    # --peer/--variance: sampled before launch (else null)
  n_referees: 3                           # --variance N (else null)
  peeves: { critical: 2, constructive: 1 }# referee peeve budget (stress doubles critical)
  fresh_context: true                     # re-audit rounds run in a fresh fork
  max_rounds: 5                           # loop-until-dry FALLBACK cap (not the primary stop)
  cross_artifact: true                    # auto-invoke /review-r alongside the main review
  novelty_check: true                     # editor WebSearch probe (Post-Flight-verified)
  spend_cap_tokens: 500000                # warn-and-ask ceiling, not a context limit
```

Gather it, echo it back as the **Pre-Flight Report**, and only then spawn the fleet. Any unresolved required field (e.g. an unknown `journal`) halts before launch — never mid-run.

---

## Cross-references

- [`.claude/rules/orchestrator-protocol.md`](../rules/orchestrator-protocol.md) — the runtime that consumes these schemas.
- [`.claude/rules/model-routing.md`](../rules/model-routing.md) — which agent fills which lens, at which model tier.
- [`.claude/rules/summary-parity.md`](../rules/summary-parity.md) — the two-strikes rule the loop reuses for repeatedly-flagged findings.
