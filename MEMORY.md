# Project Memory — geobr

Facts, corrections, and settled decisions that persist across sessions. When a mistake is corrected,
append a `[LEARN:category]` entry. Keep this file short — it loads into context every session, and
the full architecture already lives in [CLAUDE.md](CLAUDE.md). Record here only what CLAUDE.md and
the code do **not** make obvious.

The upstream template's inherited memory is archived at
[`quality_reports/archive/MEMORY_upstream-template.md`](quality_reports/archive/MEMORY_upstream-template.md).

---

## Environment (read this before debugging anything)

[LEARN:env] **This machine sits behind Ipea's proxy `cache.ipea.gov.br:3128`, set in WinINET but NOT
exported as env vars.** PowerShell/.NET honour it; **libcurl does not**, so R's `curl`/`httr2` time
out against github.com and every `read_*()` fails with "Could not download geobr metadata". Export
before any networked R work:

```
$env:http_proxy  = "http://cache.ipea.gov.br:3128"
$env:https_proxy = "http://cache.ipea.gov.br:3128"
```

With the proxy set, `devtools::test("r-package")` gives **FAIL 0 | WARN 0 | SKIP 1 | PASS 323**
(verified 2026-08-31). `httr2::is_online()` returns `TRUE` even when the fetch will time out — it is
**not** a valid probe. Check `Sys.getenv("http_proxy")` first.

[LEARN:env] The **sandboxed Bash tool has no outbound network**; the PowerShell tool does. Run
networked R commands through PowerShell; treat a Bash-tool timeout as a sandbox artifact, not a
broken package.

[LEARN:env] Windows Server 2022, `L:\Proj_acess_oport\git_rafa\geobr`. **R 4.6.1 only** — no
`python`, `uv`, `gh`, `conda`, `.venv`; `covr` not installed. Python is edit-and-CI: never emit a
Python command as if it will run — report `SKIPPED — no local Python`.

[LEARN:env] Default branch is `master` (not `main`), remote `ipea/geobr`. History commits directly to
`master`; `/commit` pushes to the current branch and never auto-merges.

## Architecture gotchas

[LEARN:data] **R pins the data release; Python does not.** R reads `geobr_env$data_release`; Python
calls the GitHub API `releases/latest` *first*, falling back to the pinned `GEOBR_DATA_RELEASE`. So
Python can serve a **newer** data release than R at the same package version — the first thing to
check when the two disagree about available years.

[LEARN:data] **Caching differs by language, and this is the sharpest divergence.** R:
`fs::path_temp("geobr")`, per-session, dies with the session. Python: `~/.cache/geobr` (or
`$XDG_CACHE_HOME/geobr`), **persistent**, no expiry, no size cap, temp dir only as a `mkdir`-failure
fallback. A stale Python file under a superseded release survives reboots. *(Corrects an earlier
entry that claimed "session temp dir only" for both — true for R, false for Python.)*

[LEARN:data] The release tag is hardcoded in **five** places in **two** formats (`v2.0.0`,
`data_v2.0.0`): `r-package/R/onLoad.R:7`, `r-package/R/utils.R:4` (**dead** — assigned, never read),
`r-package/R/utils.R:380`, `python-package/geobr/utils.py:20`, `python-package/geobr/utils.py:24`.
A bump must touch every live copy; missing one gives a confusing 404, not a version error.

[LEARN:parity] **There are no R↔Python function-name exceptions.** All 31 exported readers match
exactly. Two R *files* are named differently from the functions they define (`read_favelas.R` →
`read_favela`, `read_quilombos.R` → `read_quilombola_land`), so **any filename-based comparison
reports two false gaps** — including the repo's own `helpers/diff_packages.py`. Compare `NAMESPACE`
exports against `geobr/__init__.py`. *(Corrects an earlier entry that recorded these as real naming
exceptions.)*

[LEARN:parity] Three **systematic** API divergences, verified across all 31 readers (2026-08-31):
`output` defaults to `"sf"` in R and `"gpd"` in Python; `verbose` defaults to `TRUE` in R and `False`
in Python; argument order differs (`output, showProgress, cache, verbose` vs `verbose, output,
show_progress, cache`), so positional calls are not portable. First argument matches in all 31.
These are real drift, not idiom — but changing a default is breaking, so they await a decision.

[LEARN:parity] **Python's filter fails open; R's aborts.** `read_filter_parquet_relation()` returns
the **unfiltered** relation when no branch matches and has no zero-row check, where R's
`filter_arrw()` aborts in both cases. An invalid code raises in R but yields an empty or full result
in Python — the silent-wrong-answer mode.

## Known defects (reported, awaiting maintainer decision — do not re-discover)

[LEARN:bug] `download_parquet()` `r-package/R/utils.R:432-435` — comment says "Halt function if
download failed" but the branch calls bare `invisible(NULL)` instead of `return(invisible(NULL))`.
Falls through to `geobr_open_dataset()` on a missing file. Still ends up `NULL`, but the error prints
**twice** and the code reads as if it short-circuits.

[LEARN:bug] `output` is validated inside `convert_output()`, **after** the download, in both
languages. Verified: a rejected `output` value still downloaded the full parquet.

[LEARN:bug] Python smells: `_simplified_attempts()` defined **twice identically**
(`utils.py:485`, `:490`); `convert_output()` docstring documents a `filter_code` param its signature
lacks; `_GEO_LOADERS` marks `indigenousland` with `year_param: "date"` while `read_indigenous_land()`
takes `year`; `CHANGELOG.md` announces `read_quilombola_lands()` but the function is singular.

[LEARN:meta] `python-package/pyproject.toml` declares `homepage = ".../ipeaGIT/geobr"`; the remote and
`r-package/DESCRIPTION` use `ipea/geobr`.

## Settled decisions (do not re-propose)

[LEARN:decision] **No `skip_if_offline()`.** All 38 R test files call `skip_on_cran()`; none call
`skip_if_offline()`, and the maintainer declined adding it (2026-08-31). Consequence: the R suite
needs a live connection locally, so an outage and a real regression look identical — check the proxy
before reading R failures as code failures. Python is the mirror image: CI runs `-m "not network"`
green, so its default suite genuinely is offline-safe.

[LEARN:decision] **Workflow surface was pruned 14 skills / 5 agents → 10 / 4 (2026-08-31).** Deleted
`/promote-memory` + `promote-memory-council` (read a `.claude/state/personal-memory.md` that does not
exist — two-tier memory governance is a *template* concern, not a single-maintainer project one),
`/context-status` (read a hook cache; no hooks installed), `/permission-check` (settings already allow
everything). `/compress-session` was merged into `/checkpoint`. Do not re-add these.

## Workflow

[LEARN:workflow] Rules only fire when their frontmatter `paths:` globs match real files. In this
monorepo every glob must be prefixed `r-package/` or `python-package/` — a root-relative glob
inherited from a single-package template silently matches **nothing**. This is what made the
inherited config inert; re-check it whenever a rule is added.

[LEARN:workflow] Plans, specs, session logs, and checkpoints live on disk under `quality_reports/`,
not only in the conversation.

[LEARN:workflow] Verify claims by running the thing, not by reading it. Every architecture claim in
CLAUDE.md's R section was confirmed by executing the functions; the Python section is explicitly
marked static-only because no interpreter exists here. Keep that distinction visible in what you write.
