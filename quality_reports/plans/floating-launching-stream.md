# Plan — Adapt the Claude Code academic workflow to geobr

**Status:** APPROVED
**Date:** 2026-08-31
**Repo:** `ipea/geobr` (branch `master`)

---

## Context

The `.claude/` config in this repo was forked from `pedrohcgs/claude-code-my-workflow` and then
partially adapted for **censobr** — a single-language R package with its source at the repo root.
geobr is a different shape: a **dual-language monorepo** (`r-package/` + `python-package/`) whose
value is in a download architecture (release-asset sniffing → metadata table → tempdir cache) that
the config knows nothing about.

The result is a workflow that is largely inert here. Concretely:

| Symptom | Evidence |
|---|---|
| Rules never activate | `r-package-conventions.md` frontmatter globs `R/**/*.R`, `DESCRIPTION`, `NAMESPACE` — geobr's live at `r-package/R/*.R`, `r-package/DESCRIPTION`. Zero matches. |
| Half the repo is uncovered | `python-package/` (40 modules, 39 test files) has no rule, no reviewer agent, no check skill. |
| `CLAUDE.md` is the upstream template | Beamer/Quarto/XeLaTeX commands, lecture tables, `[YOUR PROJECT NAME]`. Loaded every session. |
| `MEMORY.md` is the *template's* memory | ~150 lines about surface-sync scripts, journal profiles, the template's own release cycle. Zero geobr facts. |
| Skills call scripts that don't exist | `/commit` → `scripts/quality_score.py`, `scripts/check-surface-sync.sh`; `/deep-audit` → `scripts/check-skill-integrity.py`; `verifier` agent → `scripts/sync_to_docs.sh`, XeLaTeX. |
| `/commit` targets the wrong branch and a missing tool | Hardcodes `main`; repo default is `master`. Calls `gh pr create` / `gh pr merge`; **`gh` is not installed on this machine**. |
| Stale identity | 10 leftover `censobr` references across rules, skills, references, and `templates/quality-report.md`. |

**Verified local toolchain:** R 4.6.1 at `C:\Program Files\R\R-4.6.1`. **No `python`, no `uv`, no `gh`,
no `conda`, no `python-package/.venv`.** Python work on geobr from this machine is edit-and-CI, not
run-locally — the config must say so rather than emitting commands that fail.

**Outcome:** a workflow whose rules fire on the right paths, that knows both languages, that encodes
geobr's download architecture as reviewable invariants, and whose gates run commands that exist.

---

## Recommended approach

Six workstreams. Nothing new is invented where an upstream file can be retargeted.

### 1. `CLAUDE.md` — rewrite for geobr (~120 lines)

Replace the template wholesale. Sections: project identity (dual package, versions R 2.0.1 /
Python 1.0.0, `master`, `ipea/geobr`); **data architecture** (assets in `ipea/geobr_prep_data`
releases → per-call sniff → metadata table → URL construction → session `tempdir()` cache, keyed by
the `data_release` tag); folder structure (already corrected on disk — keep it); real commands for R
and Python with a note on which run locally; conventions; the installed skill/rule inventory.

Delete: LaTeX/Quarto/palette commands, the 80/90/95 score table (no scorer exists — replaced by the
gate in §4), Beamer environments, Quarto CSS classes, lecture state table.

### 2. `MEMORY.md` — reset and seed

Archive the inherited file to `quality_reports/archive/MEMORY_upstream-template.md` (nothing is
lost), then rewrite with: the ~4 workflow lessons that genuinely transfer (plan-on-disk,
spec-then-plan, context-survival checklist, `[LEARN]` protocol) plus geobr architecture facts worth
persisting — the `data_release` tag mechanism, the tempdir-cache contract, R↔Python parity, the
local-toolchain constraint above. Target ≤ 60 lines.

### 3. Rules — retarget, and add the three geobr-specific ones

**Retarget (edit frontmatter + drop `censobr` wording):**
- `r-package-conventions.md` → globs `r-package/R/**/*.R`, `r-package/tests/**`, `r-package/man/**/*.Rd`,
  `r-package/vignettes/**`, `r-package/DESCRIPTION`, `r-package/NAMESPACE`, `r-package/NEWS.md`.
- `orchestrator-protocol.md` → rescope the "Scoped to censobr" note; rewrite the implemented-skills
  table to the skills that actually exist here after this plan.
- `model-routing.md` → add the Python reviewer row; drop dead cross-references.
- `summary-parity.md` → drop `**/*.qmd` from `paths:` (no Quarto here); keep the rest.

**New — `python-package-conventions.md`** (globs `python-package/**`). Mirrors the R rule for the
Python side: `pyproject.toml` dependency hygiene and the `uv.lock` frozen-sync contract; the
`network` pytest marker as the offline/online boundary; module layout (`_cache`, `_filter`,
`_output`, `_duckdb_backend` are private; `read_*` are public); geopandas/duckdb return-type
discipline; no writes outside the session temp dir. Records that these commands need a machine with
Python — CI is the enforcement point here.

**New — `cross-language-parity.md`** (globs both packages). The invariant that makes geobr one
package in two languages: every `read_*` exists on both sides with the same argument names and
defaults, both track the same `data_release`, and both resolve the same metadata keys. Builds on the
existing `python-package/helpers/diff_packages.py` set-difference check rather than replacing it.

**New — `data-release-conventions.md`** (globs `r-package/R/**`, `python-package/geobr/**`). Encodes
the download architecture as reviewable rules: the release tag is a single logical constant —
**flag that it is currently duplicated at `r-package/R/onLoad.R:8` and `r-package/R/utils.R:4`
(both `'v2.0.0'`), a live drift hazard**; downloads go to `tempdir()` only; a metadata sniff failure
must produce an actionable `cli::cli_abort` / exception, never a silent empty result; network-dependent
tests carry `skip_on_cran()` / `skip_if_offline()` (R) or `@pytest.mark.network` (Python).

### 4. Skills — fix the broken gates, add the Python counterparts

- **`/commit`** — the biggest repair. Replace Step 0 (`quality_score.py`) and Step 0b
  (`check-surface-sync.sh`) with a **touched-package gate**: `r-package/` changed → `devtools::document()`
  drift check + `devtools::test()`; `python-package/` changed → `uv run pytest -m "not network"`
  *if a Python toolchain is present*, otherwise report `SKIPPED — no local Python, CI will run it`
  (never a silent pass). Branch base `master`. Add a `gh` pre-flight: present **and** absent both
  work — see Defaults below.
- **`/r-package-check`** — point at `r-package/`; add geobr's realities: network tests, the
  `_R_CHECK_*` offline env, `cran-comments.md` already in the repo.
- **New `/py-package-check`** — the Python counterpart: `uv sync --frozen` → `uv run pytest -n 2 -m "not network"`
  → build, mirroring `.github/workflows/Python-CMD-check.yaml` exactly so local and CI can't diverge.
  Halts with a clear message when no Python is available.
- **New `/parity-check`** — runs the R↔Python parity invariant from §3: function-set diff, then a read
  of matched pairs for argument-name/default drift. Report only; no edits.
- **`/deep-audit`, `/new-skill`, `/review-r`, `/diagnose`** — strip references to the four
  nonexistent `scripts/*` gates and to `scripts/R/`, `Figures/`, lectures; re-point `/diagnose`'s
  worked example at geobr's actual failure modes (stale tempdir cache under a previous release tag,
  upstream data re-release).

### 5. Agents

- **`verifier.md`** — currently runs XeLaTeX, `sync_to_docs.sh`, `Rscript scripts/R/*.R`. Rewrite its
  verification commands to geobr's: R test/document/check, Python pytest (or an explicit skip),
  pkgdown build. This agent is invoked by `/commit`; today it would fail on every call.
- **`r-reviewer.md` / `r-package-reviewer.md`** — retarget paths, drop `censobr`.
- **New `python-package-reviewer.md`** — Sonnet tier (matching `r-package-reviewer`), enforcing
  `python-package-conventions.md`.

### 6. `WORKFLOW_QUICK_REF.md` + `templates/quality-report.md`

Fill the `[YOUR PATH CONVENTION]` / `[YOUR SEED CONVENTION]` placeholders with geobr's real
non-negotiables (tempdir-only writes, no hardcoded release tags, parity, offline-by-default tests),
and swap the `censobr_env$data_release` line in the quality-report template for geobr's.

---

## Defaults I'm applying (override any at approval)

These were going to be questions; I'm proceeding with the recommended answer rather than blocking.

1. **Git flow** — `/commit` will **commit to the current branch and push**, matching your recent
   history (`72d9542 python page`, `6ec6dc4 python vignette` all landed directly on `master`). If `gh`
   is present it additionally offers the PR path; if absent it prints the GitHub compare URL instead
   of failing. No auto-merge either way.
2. **Commit gate** — touched-package offline tests (§4). Fast, and mirrors CI.
3. **`MEMORY.md`** — archive-then-reset (§2). Nothing deleted, just moved out of the session context.
4. **Scope** — all three new rules, both new skills, one new agent. This is what closes the
   Python-side gap; trim any item and I'll drop it cleanly.

---

## Files

**Rewritten:** `CLAUDE.md`, `MEMORY.md`, `.claude/WORKFLOW_QUICK_REF.md`, `.claude/agents/verifier.md`,
`.claude/skills/commit/SKILL.md`

**New:** `.claude/rules/python-package-conventions.md`, `.claude/rules/cross-language-parity.md`,
`.claude/rules/data-release-conventions.md`, `.claude/skills/py-package-check/SKILL.md`,
`.claude/skills/parity-check/SKILL.md`, `.claude/agents/python-package-reviewer.md`,
`quality_reports/archive/MEMORY_upstream-template.md`

**Edited (frontmatter globs + stale references):** `.claude/rules/{r-package-conventions,orchestrator-protocol,model-routing,summary-parity}.md`,
`.claude/agents/{r-reviewer,r-package-reviewer}.md`, `.claude/skills/{r-package-check,deep-audit,new-skill,review-r,diagnose}/SKILL.md`,
`.claude/references/{orchestration-schemas,prompt-formatting-core}.md`, `templates/quality-report.md`

**Untouched:** all of `r-package/`, `python-package/`, `docs/`, `.github/`. This plan changes
configuration only — no package source, no tests, no CI.

---

## Verification

1. `grep -ril censobr .claude templates CLAUDE.md MEMORY.md` → no hits.
2. `grep -rn "quality_score.py\|check-surface-sync\|check-skill-integrity\|sync_to_docs" .claude CLAUDE.md` → no hits.
3. Every rule's `paths:` glob resolves to ≥1 real file — verified by expanding each glob against the
   working tree and reporting the match count per rule.
4. Every command quoted in `CLAUDE.md` and in the new/edited skills is either executed successfully
   here, or explicitly marked as requiring a toolchain this machine lacks.
5. `Rscript -e 'devtools::test("r-package")'` runs (offline subset) — confirms the `/commit` gate is real.
6. End-to-end: touch a file under `r-package/R/`, invoke `/commit` in dry-run, and confirm the gate
   selects the R path, skips Python with a stated reason, and targets `master`.
7. Report the pass/fail of 1–6 in the summary; no step silently skipped.

---

## Out of scope (flagged, not fixed)

- ~~`python-package/pyproject.toml` disagrees with the git remote about the GitHub org.~~
  **RESOLVED 2026-09-02 — and the original reading was backwards.** The org was renamed
  `ipeaGIT` → `ipea`; `pyproject.toml` already had the *current* name and the git remote had the
  *legacy* one (a remote URL is not updated by an org rename). The whole repository has since been
  normalised to `ipea`. See `MEMORY.md` `[LEARN:meta]`.
- The duplicated `data_release` constant (`onLoad.R:8` / `utils.R:4`) is **documented** as a hazard by
  the new rule in §3; consolidating it is a source change for a separate task.
