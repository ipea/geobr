---
name: diagnose
description: Root-cause a failing or wrong geobr call with a disciplined check-the-environment-first loop instead of guessing. Use when the user says "why is this failing", "read_* returns nothing", "could not download geobr metadata", "this worked yesterday", "R and Python disagree", "debug this download", or pastes a user bug report. Tuned to geobr's real failure modes: proxy, stale cache, release-tag drift, upstream re-release, and code-dispatch surprises. Use `--no-fix` to localize without editing.
author: geobr
version: 2.0.0
argument-hint: "[symptom, file, or pasted error] [--no-fix]"
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Write"]
effort: high
---

# `/diagnose` — root-cause a geobr failure

Most geobr failures are **environmental, not code**. Work the ladder in order — each rung is cheaper
than the one below it, and the top two explain the large majority of reports.

**Never skip to reading package source before rung 1 and 2 come back clean.** That is the mistake
this skill exists to prevent.

---

## Rung 1 — Network and proxy

The single most common cause. `httr2::is_online()` returns `TRUE` even when the fetch will time out,
so **it is not a reliable probe** — test the real endpoint.

```r
Sys.getenv("http_proxy"); Sys.getenv("https_proxy")
curl::curl_fetch_memory("https://github.com/ipea/geobr_prep_data/releases/expanded_assets/v2.0.0")$status_code
```

- Timeout with empty proxy vars on a corporate network → **found it.** libcurl ignores the WinINET
  proxy that browsers and PowerShell honour. On the maintainer's machine:
  `http_proxy` / `https_proxy` = `http://cache.ipea.gov.br:3128` (see MEMORY.md).
- In this Claude Code session specifically: the **sandboxed Bash tool has no outbound network**.
  Run networked commands through PowerShell before concluding anything.

Symptom signature: `Could not download geobr metadata`, or a wall of test failures where every
`read_*` returns `NULL`.

## Rung 2 — Stale cache

Second most common, and the classic "it worked yesterday".

```r
fs::path_temp("geobr") |> list.files()          # R: per-session
```
```python
from geobr._cache import cache_dir; print(list(cache_dir().glob("*")))   # ~/.cache/geobr: PERSISTENT
```

R's cache dies with the session; **Python's does not** — it survives reboots with no expiry and no
size cap. A file cached under a superseded `data_release` is served indefinitely. Clear it, or pass
`cache = FALSE`, and re-run.

This is also the first thing to check when **R and Python disagree** about available years or row
counts.

## Rung 3 — Release-tag drift

```bash
grep -n "data_release\|v2\.0\.0\|data_v2" r-package/R/onLoad.R r-package/R/utils.R
grep -n "GEOBR_DATA_RELEASE\|IPEA_FALLBACK_BASE" python-package/geobr/utils.py
```

The tag is hardcoded in five places in two formats. A partial bump reads metadata from one release
and files from another — surfacing as a **404 on a plausible-looking filename**, not a version error.

Also remember the structural divergence: **R pins the tag; Python asks `releases/latest` first.**
Publishing a new `geobr_prep_data` release changes Python's behaviour immediately and R's not at all.
That alone explains many R-vs-Python mismatches.

## Rung 4 — Upstream data change

```r
m <- geobr:::download_metadata2(); subset(m, geo == "<geography>")
```

The metadata table is derived **entirely from asset filenames**. If `geobr_prep_data` re-released an
asset, renamed one, or changed the naming convention, the parsed `geo` / `year` / `simplified`
columns shift silently in both packages. Compare the geography's rows against what the user expects
before suspecting the reader.

## Rung 5 — Code dispatch

Only now read the source. The usual suspects:

- **`filter_arrw()` (R) picks the column from the value.** Sequential `if`s, last match wins. A code
  of unexpected width lands on the wrong `code_*` column.
- **Python's filter fails open.** `read_filter_parquet_relation()` returns the **unfiltered** relation
  when no branch matches and has no zero-row check, where R's `filter_arrw()` aborts. So an invalid
  code raises in R but yields an empty or full result in Python.
- **`output` is validated after the download** in both languages — a bad `output` value is not the
  cause of a download failure.
- **Argument defaults differ across languages**: `output` is `"sf"` in R and `"gpd"` in Python;
  `verbose` is `TRUE` in R and `False` in Python.

---

## Method

1. **Reproduce.** Get the exact call, the exact error, and `sessionInfo()` (R) or `uv pip list`
   (Python). A report you cannot reproduce is a rung-1 problem until proven otherwise.
2. **Minimise.** Reduce to the smallest failing call — usually one geography, one year, `code = "all"`.
3. **Work the ladder.** Rungs 1 → 5, in order. Record which rungs came back clean.
4. **Confirm the cause** by making the symptom appear and disappear on demand. A fix you cannot
   toggle is a guess.
5. **Fix**, unless `--no-fix`. Package source changes need maintainer sign-off — propose, do not
   apply, when the fix lands in `r-package/R/` or `python-package/geobr/`.

## Output

```markdown
## Diagnosis — <symptom>

**Reproduced:** yes / no (<how>)
**Minimal case:** `<call>`

| Rung | Result |
|---|---|
| 1 Network/proxy | clean / **CAUSE** — <detail> |
| 2 Stale cache | clean / **CAUSE** — <detail> |
| 3 Release tag | clean / **CAUSE** — <detail> |
| 4 Upstream data | clean / **CAUSE** — <detail> |
| 5 Code dispatch | clean / **CAUSE** — `file:line` |

**Root cause:** <one sentence>
**Toggle confirmed:** <how the symptom was made to appear and disappear>
**Fix:** applied / proposed (package source — needs sign-off) / not needed (environment)
```

When the root cause lands in package source (rung 5), also save the report to
`quality_reports/diagnoses/YYYY-MM-DD_<slug>.md` — those are the ones worth a record. Environment
causes (rungs 1-2) belong in chat only; they are not repository history.

If every rung comes back clean, say so plainly and stop. An unexplained failure reported honestly is
worth more than a plausible story.
