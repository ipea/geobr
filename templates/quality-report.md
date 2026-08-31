<!-- Copy to quality_reports/merges/YYYY-MM-DD_[branch-name].md -->

# Quality Report — [branch-name] — YYYY-MM-DD

**Merged into:** main
**Scope:** [what this branch/PR changed]

## Release gate (`/r-package-check`)

| Check | Result |
|---|---|
| `R CMD check --as-cran` | E errors, W warnings, N notes (each justified below) — baseline is 0/0/0 |
| `devtools::test()` | P passed, F failed |
| Coverage (`covr`) | X% of exported functions; list any at 0% |
| roxygen completeness | [pass/fail — every exported fn has @param/@return/@examples] |

### NOTE justifications

- [NOTE text] → [why it's acceptable, or the `cran-comments.md` entry]

## r-package-reviewer findings

- Critical: [count] — [resolved / deferred]
- High: [count] — [resolved / deferred]

## Verdict

RELEASABLE / FIX-FIRST / POLICY-VIOLATION

## Data-release pin

- `geobr_env$data_release` (`r-package/R/onLoad.R:7`): [unchanged / bumped X → Y]
- `GEOBR_DATA_RELEASE` (`python-package/geobr/utils.py:20`): [unchanged / bumped X → Y]
- If bumped: NEWS.md entry written? user caches invalidated intentionally? — [yes/no]

## Follow-ups

- [anything deferred to a later PR]
