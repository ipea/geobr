---
name: parity-check
description: Check R↔Python API parity across geobr's two packages — which read_* functions exist on one side but not the other, and where matched functions disagree on argument names, defaults, or the metadata key they resolve. Use when the user says "check parity", "do R and Python match", "is the python side up to date", "API drift", or after changing a public reader on one side. Read-only; produces a report, never edits.
author: geobr
version: 1.0.0
argument-hint: "[function name, or blank for all]"
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Write"]
effort: high
---

# `/parity-check` — R ↔ Python API Drift

geobr is one package implemented twice. This skill finds where the two implementations have drifted.

**Input:** `$ARGUMENTS` — a single function (`read_municipality`) to check one pair, or blank to
sweep everything.

**Read-only.** It reports drift; it does not fix it. Which side is correct is a maintainer decision.

---

## Constraints

- Follow [`cross-language-parity.md`](../../rules/cross-language-parity.md) — in particular §4,
  **what is not required to match**. Do not report native-idiom differences as drift.
- No interpreter needed. This is a source-reading skill, so it works on a machine with neither R nor
  Python available.

---

## Phase 1: Function-set difference

Enumerate the readers on both sides from the **exported names**, not the filenames — two R files
are named differently from the functions they define, so a filename diff reports false gaps:

```bash
# R: exported functions (authoritative), not file names
grep -oE "^export\(read_[a-z_]+\)" r-package/NAMESPACE | sed "s/export(//; s/)//" | sort > /tmp/r_fns.txt
# Python: exported names
grep -oE "read_[a-z_]+" python-package/geobr/__init__.py | sort -u > /tmp/py_fns.txt
comm -23 /tmp/r_fns.txt /tmp/py_fns.txt   # R only
comm -13 /tmp/r_fns.txt /tmp/py_fns.txt   # Python only
comm -12 /tmp/r_fns.txt /tmp/py_fns.txt   # matched
```

The repo's own helper does the R-only direction and is worth running for cross-checking:

```bash
cd python-package && python helpers/diff_packages.py   # needs Python; skip if absent
```

The repo helper compares **filenames**, so it reports two false gaps every run —
`read_favelas.R` defines `read_favela` and `read_quilombos.R` defines `read_quilombola_land`.
Discard those two; they are file-naming quirks, not missing functions.

Also confirm the Python side actually **exports** each reader from `geobr/__init__.py`. A module that
exists but is not exported is invisible to users, which is a parity gap in practice.

## Phase 2: Signature comparison (the part the helper cannot do)

For each matched pair, read both implementations and extract:

- **R:** the `function(...)` argument list in `r-package/R/<fn>.R`, with defaults; and the
  `select_metadata(geography = "...")` key.
- **Python:** the `def <fn>(...)` signature in `python-package/geobr/<fn>.py`, with defaults; and the
  `geography` / metadata key passed to `select_metadata_v2()`.

Compare:

| Check | Drift if... |
|---|---|
| Argument names | An argument exists on one side only |
| Argument order | Positional order differs (breaks positional calls) |
| Defaults | `year`, `simplified`, `cache`, `showProgress`/`verbose` differ |
| Metadata key | The two resolve different `geo` values → **different data** |
| Default year | The hardcoded default year differs between sides |

**Do not flag:** `sf` vs `GeoDataFrame` returns; `showProgress` (R) vs `verbose` (Python) where that
naming is already established across the whole package; message wording; internal helper names.

## Phase 3: Release-tag consistency

Both packages must target the same data release:

```bash
grep -n "data_release\|v2\.0\.0" r-package/R/onLoad.R r-package/R/utils.R
grep -n "GEOBR_DATA_RELEASE\|IPEA_FALLBACK_BASE" python-package/geobr/utils.py
```

Report each live copy and whether they agree. Remember the structural divergence documented in
[`data-release-conventions.md`](../../rules/data-release-conventions.md) §3: **R pins the tag,
Python asks for `releases/latest` first.** Equal constants therefore do not guarantee equal
behaviour — say so whenever a year mismatch is in play.

## Phase 4: Report

Save to `quality_reports/audits/parity_check_[YYYY-MM-DD].md`:

```markdown
# R ↔ Python Parity — [date]

## Summary
- Matched readers: N
- R only: N · Python only: N
- Signature drift: N functions
- Release tag: CONSISTENT / DIVERGENT

## Missing functions
| Function | Present in | Missing from | Changelog records it? |
|---|---|---|---|

## Signature drift
| Function | Argument | R | Python | Severity |
|---|---|---|---|---|

## Metadata-key drift  (highest severity — the two sides return different data)
| Function | R geo key | Python geo key |
|---|---|---|

## Release tag
| Location | Value |
|---|---|

## Not drift (checked, correct as-is)
[Native-idiom differences confirmed intentional — so the next run does not re-raise them.]

## Verdict
IN PARITY / DRIFT — N gaps, of which N are recorded in a changelog
```

Severity: a **metadata-key** mismatch is Critical (silently different data). A **missing function**
or a **changed default** is Major. An argument-order difference is Major. Naming already established
across the package is Minor or not a finding at all.

---

## Important

- **Report, never fix.** Which side is right — and whether Python should be pinned or R unpinned —
  is the maintainer's call.
- **A recorded gap is not a failure.** Parity may lag deliberately if `NEWS.md` or `CHANGELOG.md`
  says so; note it as recorded and move on.
- **Always fill the "Not drift" section.** Without it, every run re-litigates the same intentional
  `sf`/`GeoDataFrame` differences.
