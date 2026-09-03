# Session Log — Adapt Claude Code workflow to geobr

**Date:** 2026-08-31
**Plan:** [floating-launching-stream.md](../plans/floating-launching-stream.md) (APPROVED)

## Goal

Make the inherited `.claude/` config (forked from claude-code-my-workflow, partially adapted for
censobr) actually fit geobr: a dual-language monorepo whose value is a release-asset download
architecture.

## Key context established this session

- **Layout:** `r-package/` (R 2.0.1, 36 modules, 39 testthat files) + `python-package/` (1.0.0, 40
  modules, 39 pytest files). Every inherited rule glob pointed at repo root → zero matches.
- **Local toolchain:** R 4.6.1 only. No `python`, `uv`, `gh`, `conda`, or `.venv`. Python is
  edit-and-CI from this machine.
- **Default branch is `master`**, remote `ipea/geobr`. Recent history commits directly to master.
- **Download architecture:** assets live in `ipea/geobr_prep_data` releases. R scrapes
  `releases/expanded_assets/<tag>` for `*.parquet`; Python calls the GitHub API. Both parse
  `file_name → geo / year / simplified`, cache a metadata parquet in the session temp dir, then
  build per-file download URLs.

## Decisions

- `/commit` gate = touched-package offline tests; commit+push to current branch; `gh` optional.
- MEMORY.md archived to `quality_reports/archive/`, then reset to geobr facts.
- Three new rules (python conventions, cross-language parity, data-release), two new skills
  (`/py-package-check`, `/parity-check`), one new agent (`python-package-reviewer`).

## Findings worth acting on (surfaced during exploration, not fixed here)

1. **Release tag is hardcoded in 5 places across both packages**, in two different formats:
   `r-package/R/onLoad.R:7`, `r-package/R/utils.R:4` (dead — assigned, never read),
   `r-package/R/utils.R:380` (`data_v2.0.0` fallback URL), `python-package/geobr/utils.py:20`,
   `python-package/geobr/utils.py:24`.
2. **R and Python resolve the release differently.** R pins to `geobr_env$data_release`. Python
   calls `releases/latest` *first* and only falls back to the pinned tag — so Python can silently
   serve a newer data release than R for the same package version.
3. `python-package/pyproject.toml` homepage says `ipea/geobr`; remote and DESCRIPTION say `ipea/geobr`.

## Progress

- [x] Plan approved, status set to APPROVED
- [x] CLAUDE.md rewritten for geobr (143 lines; was the untouched upstream Beamer/Quarto template)
- [x] MEMORY.md archived to `quality_reports/archive/MEMORY_upstream-template.md`, rewritten (85 lines)
- [x] Rules: 4 retargeted, 3 created (python-package, data-release, cross-language-parity)
- [x] Agents: `verifier` and `r-reviewer` rewritten, `python-package-reviewer` created, 2 retargeted
- [x] Skills: `/commit` and `/deep-audit` rewritten, `/py-package-check` + `/parity-check` created,
      4 cleaned of dead script references
- [x] WORKFLOW_QUICK_REF.md placeholders filled; templates de-censobr'd
- [x] Verification 1-6 run; results in the summary

## Mid-session discovery that changed the design

The `/commit` R gate failed on first run — 300+ test failures, all "Could not download geobr
metadata". Root cause was **not** the package:

- The machine sits behind Ipea's proxy `cache.ipea.gov.br:3128`, set in **WinINET only**.
  PowerShell/.NET honour it; **libcurl does not**, and no `http_proxy`/`https_proxy` env vars are set.
  So R's `curl`/`httr2` time out against github.com while `Invoke-WebRequest` succeeds.
- Separately, the **sandboxed Bash tool has no outbound network at all**; the PowerShell tool does.
- Exporting the proxy and re-running through PowerShell:
  **FAIL 0 | WARN 0 | SKIP 1 | PASS 323.**

This forced a correction to config I had already written: I had claimed "the R suite must pass
offline". It does not and cannot — all 38 R test files call `skip_on_cran()` but **none** call
`skip_if_offline()`, so a network outage produces failures indistinguishable from regressions.
Corrected in `r-package-conventions.md` §7b, `data-release-conventions.md` §6, `CLAUDE.md`, the
`/commit` R gate, and the `verifier` agent — all of which now carry the proxy recipe, the 323-pass
baseline, and an `INCONCLUSIVE` verdict for network collapse.

Python is the mirror image: only 2 of 49 test files are marked `network`, and CI runs
`-m "not network"` green — so the Python default suite genuinely is offline-safe.

## Follow-up: proposed, then declined by the maintainer

I recommended adding `skip_if_offline()` alongside `skip_on_cran()` across the 38 R test files.
**The maintainer declined (2026-08-31). It was never applied — no test file was touched.**
The decision is now recorded in MEMORY.md, `r-package-conventions.md` §7b, and
`data-release-conventions.md` §6 so no future session re-proposes it. The reviewer agents'
testing checklists were updated to stop prescribing it.

What stays true regardless: the R suite needs a live connection, so check the proxy before
reading a wall of R failures as a regression.

---

# Addendum — read_municipality() review → CLAUDE.md "R Package Architecture"

Reviewed `read_municipality()` and its whole call chain, verified empirically by running the
functions (proxy set, via PowerShell). Expanded the user's 5-step skeleton into a documented
pipeline with function names + line numbers, the `filter_arrw()` dispatch table, the canonical
signature contract, the family variations, and the invariants.

## Empirically verified (not inferred)

- Metadata table: 505 rows / 28 geographies at `v2.0.0`; `municipalities` has 58 rows spanning
  1872–2025; one (year, simplified) pair → exactly 1 file.
- `code_muni` dispatch: `"RJ"` → 92 rows, `33` → 92 rows, `1200179` → 1 row.
- Return classes: `sf tbl_df tbl data.frame` / `duckspatial_df tbl_duckdb_connection …` /
  `Table ArrowTabular ArrowObject R6`. CRS `EPSG:4674`.
- `keep_areas_operacionais` works (2010/2017/2022 carry codes 4300001-2; **2020 does not** — an
  upstream data gap, not a code bug).
- Cache holds one parquet per (geo, year, simplified) plus `metadata_geobr_gpkg.parquet`.

## Findings (reported, not fixed — package source)

1. **`download_parquet()` failure path does not halt.** `r-package/R/utils.R:432-435`: the comment
   says "Halt function if download failed" but the branch calls bare `invisible(NULL)` instead of
   `return(invisible(NULL))`. Execution falls through to `geobr_open_dataset()` on a nonexistent
   file. Net result is still `NULL` (that helper also fails safely), so no user-visible breakage —
   but the failure message prints **twice** and the code reads as if it short-circuits when it does not.
2. **`output` is validated after the download.** `convert_output()` checks the allowed set; a typo
   downloads the full parquet first, then errors. Verified: cache went 0 → 1 file on a rejected call.
3. **Latent:** `select_metadata()` returns a data.frame; `download_parquet()` assumes one row. A
   duplicate asset name upstream would pass a length-2 vector into a single-file download.

## Correction to earlier config work

The `cross-language-parity` rule and `/parity-check` claimed R↔Python naming exceptions
(`read_quilombos`/`read_favelas`). **Wrong** — those are *file* names; the exported R functions are
`read_favela` and `read_quilombola_land`, matching Python exactly. Both were rewritten to compare
`NAMESPACE` exports against `geobr/__init__.py` rather than filenames. The corrected check runs
clean: **31 exported readers on each side, zero gaps in either direction.** Also documented that the
repo's own `helpers/diff_packages.py` is filename-based and so reports these two as false gaps.

---

# Addendum 2 — Python architecture section

Reviewed `read_municipality.py` and the shared pipeline (`utils.read_geobr_v2`, `_output`,
`_cache`, `_filter`, `_duckdb_backend`) and wrote `## Python Package Architecture` in CLAUDE.md.
**Static review only** — no Python toolchain on this machine — and the section says so explicitly.

## Systematic R↔Python API divergences (verified across all 31 readers)

| | R | Python | Scope |
|---|---|---|---|
| `output` default | `"sf"` | `"gpd"` | all 30 readers taking `output` |
| `verbose` default | `TRUE` | `False` | **all 31** |
| argument order | `output, showProgress, cache, verbose` | `verbose, output, show_progress, cache` | positional calls not portable |

First argument matches in all 31 (including `date` for conservation_units / health_facilities /
quilombola_land). These are real drift, not idiom — but changing any default is breaking, so they
are documented as decisions for the maintainer, not flagged as bugs.

## Correction forced by this review

CLAUDE.md and three rules asserted "downloads go to the session temp dir and nowhere else — never
the user's home". **True for R, false for Python.** `_cache.cache_dir()` resolves to
`~/.cache/geobr` (or `$XDG_CACHE_HOME/geobr`), persistent, no expiry, no size cap; the temp dir is
only a fallback when `mkdir` fails. Corrected in CLAUDE.md (data architecture + conventions table +
pipeline diagram), `data-release-conventions.md` §4, `python-package-conventions.md`,
`WORKFLOW_QUICK_REF.md`, `/diagnose`, `/commit`, and the `verifier` + `python-package-reviewer` agents.

## Python findings (reported, not fixed)

1. **An unmatched code silently returns everything.** `read_filter_parquet_relation()`
   (`_duckdb_backend.py:476`) falls through to an unfiltered relation when no branch matches, and
   has no zero-row check. R's `filter_arrw()` aborts in both cases. So an invalid code raises in R
   but yields an empty or full result in Python — the "silent wrong answer" failure mode.
2. **The filter column is chosen from `codes[0]`** — a mixed list is dispatched on its first element.
3. **`_simplified_attempts()` is defined twice, identically** (`utils.py:485` and `:490`).
4. **`convert_output()`'s docstring documents a `filter_code` parameter** its signature lacks.
5. **`_setup_connection()` swallows every exception** loading `spatial`/`httpfs`
   (`_duckdb_backend.py:134`); a failed extension load surfaces later as a confusing SQL error.
6. **`_GEO_LOADERS` marks `indigenousland` with `year_param: "date"`** while `read_indigenous_land()`
   takes `year` — wrong hint in the auto-loader's warning message.
7. **Two filter implementations** must stay in agreement: `_filter.filter_by_code()` (pandas, legacy
   gpkg path) and `read_filter_parquet_relation()` (SQL, v2 path).

---

# Addendum 3 — Surface pruning

Reduced the workflow surface from **14 skills / 5 agents to 10 / 4**, on the maintainer's approval.

## Deleted (dead dependencies or no use case here)

| Removed | Why |
|---|---|
| `/promote-memory` + `promote-memory-council` agent | Reads `.claude/state/personal-memory.md`; neither the file nor `.claude/state/` exists. It is two-tier memory governance for a *template* repo — geobr is one project, one maintainer, one machine, so there is no promotion decision. |
| `/context-status` | Reads `~/.claude/sessions/*/context-monitor-cache.json`, written by hooks that are not installed (`.claude/hooks/` absent). The remainder was two `ls -lt` calls. |
| `/permission-check` | `settings.json` allows `Bash(*)`, `Edit(**)`, `Write(**)`, `Read(**)` — there is no prompt problem to diagnose. Its host-global privacy phasing protected template forkers, not this repo. |
| `/compress-session` | Merged into `/checkpoint` (below). |

## Merged: `/checkpoint` v2.0.0 (158 + 156 → 135 lines)

One skill for both moments — explicit stop-point *and* approaching auto-compaction. Kept
`compress-session`'s two genuinely distinct contributions: the **"Discarded as noise"** section
(naming failed hypotheses so a future session does not re-quote them as live leads) and the
`why-now` frontmatter field. Dropped the `/promote-memory` handoff — `[LEARN]` proposals now go
straight to `MEMORY.md` on approval, since the second memory tier no longer exists. Attribution to
Sant'Anna (clo-author) and Breunig (long-context failure modes) preserved.

## Rewritten: `/diagnose` v2.0.0 (187 → 136 lines)

Was generic research-code debugging (estimands, seeds, tolerance bands for point estimates). Now a
**five-rung ladder ordered by likelihood**, built from failure modes actually hit this session:

1. Network/proxy — with the warning that `httr2::is_online()` returns `TRUE` when the fetch will
   still time out, so it is not a valid probe
2. Stale cache — and the R/Python asymmetry that makes Python's the persistent one
3. Release-tag drift across the five hardcoded copies
4. Upstream re-release changing filename-derived metadata
5. Code dispatch — only after 1-4 come back clean

Hard rule at the top: never read package source before rungs 1 and 2 are clean. Reports save to
`quality_reports/diagnoses/` only when the cause is in source; environment causes stay in chat.

## Verified after the change

Inventory matches disk (10 skills / 4 agents) · zero dead references repo-wide · every rule glob
still resolves · every internal markdown link resolves · `allowed-tools` covers every tool each
skill body invokes (10/10).

---

# End-of-session summary — 2026-08-31

**Scope:** adapt the inherited Claude Code workflow to geobr, then document the package architecture.
**Config only** — zero changes under `r-package/`, `python-package/`, `docs/`, or `.github/`.

## Delivered

1. **Workflow adaptation.** `CLAUDE.md` and `MEMORY.md` rewritten for geobr; 4 rules retargeted and
   3 written (`python-package-conventions`, `data-release-conventions`, `cross-language-parity`);
   `/commit`, `/deep-audit`, `verifier`, `r-reviewer` rewritten; `/py-package-check`,
   `/parity-check`, `python-package-reviewer` created; dead references to the template's
   `scripts/*` gates removed throughout.
2. **Architecture documentation.** `## R Package Architecture` (verified by executing the pipeline)
   and `## Python Package Architecture` (static review — no local interpreter, and the section says
   so) added to CLAUDE.md, both with function names and verified line numbers.
3. **Surface pruning.** 14 skills / 5 agents → 10 / 4. `/diagnose` and `/checkpoint` rewritten.
4. **Memory.** `MEMORY.md` reduced to what CLAUDE.md and the code do not already say: environment,
   architecture gotchas, known defects, settled decisions.

## Corrections made to my own earlier output this session

Recorded because the pattern matters more than the individual errors — each was caught by verifying
against the artefact rather than by re-reading what I had written:

1. Claimed R↔Python **naming exceptions** (`read_quilombos`/`read_favelas`). Those are *file* names;
   the exported functions match exactly. Caught by counting `NAMESPACE` exports. Fixed the parity
   rule and rewrote `/parity-check` Phase 1 to compare exports, not filenames — the corrected check
   returns 31 = 31, zero gaps.
2. Claimed downloads go to the **session temp dir only, never the user's home**. True for R, false
   for Python (`~/.cache/geobr`, persistent). Caught by reading `_cache.py`. Fixed in 7 places.
3. Claimed the R suite **must pass offline**. It cannot — no test calls `skip_if_offline()`. Caught
   by the suite failing. Fixed in 5 places, then re-framed as a settled decision when the maintainer
   declined the change.
4. Cited 4 wrong line numbers in the R section and 2 in the Python section. Caught by a mechanical
   re-check of every citation; all 22 now verified.

## Verification at close

Inventory matches disk (10 skills / 4 agents) · zero dead references · every rule glob resolves ·
every internal markdown link resolves · `allowed-tools` parity 10/10 · R suite 323 pass with proxy.

## Open, not done

- `/bump-data-release` and `/new-reader` proposed and not built.
- Six package-source defects reported, none fixed (see Addenda 1-2 and MEMORY.md).
- `/deep-audit` was rewritten but has never been executed here — its design is vouched for, its
  behaviour is not.
- Nothing committed; working tree carries `.claude/`, `CLAUDE.md`, `MEMORY.md`, `quality_reports/`,
  `templates/` as untracked.
