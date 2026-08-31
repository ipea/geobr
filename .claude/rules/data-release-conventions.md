---
paths:
  - "r-package/R/**/*.R"
  - "r-package/tests/**/*.R"
  - "python-package/geobr/**/*.py"
  - "python-package/tests/**/*.py"
---

# Data Release & Download Architecture

**geobr ships no data.** Every data set is a release asset in
[`ipea/geobr_prep_data`](https://github.com/ipea/geobr_prep_data/releases), resolved at runtime. This
rule states the invariants that keep that resolution correct, cheap, and CRAN-legal.

---

## 1. The pipeline

```
release tag  →  sniff *.parquet asset names  →  metadata table  →  filter  →  download  →  open
                                                (file_name → geo · year · simplified)
```

| Stage | R | Python |
|---|---|---|
| Sniff | `download_metadata2()` — `r-package/R/utils.R:266` | `download_metadata_v2()` — `python-package/geobr/utils.py:335` |
| Mechanism | scrape `releases/expanded_assets/<tag>` for `/[^"]+\.parquet` | GitHub API `releases/latest`, fallback to pinned tag |
| Filter | `select_metadata()` → `select_year_input()` → `select_geometry_type()` | `select_metadata_v2()` |
| Fetch | `download_parquet()` — httr2, with an `ipea.gov.br` fallback URL | `download_*` — requests, same fallback |
| Cache | `fs::path_temp("geobr")` | `_cache.cached_path()` |

The metadata table is derived **entirely from asset filenames** — `geo` is the leading token, `year`
the first digit run, `simplified` a substring test. A change to the naming convention upstream in
`geobr_prep_data` silently reshapes this table in both packages. Treat filename parsing as a public
contract with the data repo, not as an implementation detail.

## 2. The release tag is one logical constant, currently copied five times

| Location | Symbol / form |
|---|---|
| `r-package/R/onLoad.R:7` | `geobr_env$data_release <- 'v2.0.0'` — **the live R constant** |
| `r-package/R/utils.R:4` | `geobr_data_release <- 'v2.0.0'` — **dead: assigned, never read** |
| `r-package/R/utils.R:380` | `".../geobr/data_v2.0.0/"` — fallback URL, `data_` prefixed form |
| `python-package/geobr/utils.py:20` | `GEOBR_DATA_RELEASE = "v2.0.0"` |
| `python-package/geobr/utils.py:24` | `IPEA_FALLBACK_BASE = ".../data_v2.0.0"` |

**Rules:**
- Never inline a version string into a **new** URL. Reference the named constant.
- A data-release bump touches every **live** copy above. Missing one produces a package that reads
  metadata from one release and files from another — which fails as a confusing 404, not as a
  version error.
- `geobr_data_release` in `utils.R:4` is dead code. Do not add references to it; removing it is a
  separate, deliberate change.

## 3. Known divergence: R pins, Python chases latest

R resolves assets for **exactly** `geobr_env$data_release`. Python asks the GitHub API for
`releases/latest` first, and only falls back to `GEOBR_DATA_RELEASE` when that yields no parquet
assets. **Consequence:** publishing a new `geobr_prep_data` release changes Python's behaviour
immediately and R's not at all.

This is load-bearing behaviour, not an obvious bug — do not "harmonise" it as a drive-by fix. If a
task requires touching it, surface the choice (pin Python, or unpin R) as a decision for the
maintainer.

## 4. Filesystem contract

- **Cache location is language-specific — do not "unify" it without a decision.** R:
  `fs::path_temp("geobr")`, per-session, dies with the session. Python: `_cache.cache_dir()` →
  `~/.cache/geobr` (or `$XDG_CACHE_HOME/geobr`), persistent across sessions, no expiry, no size
  cap. Neither may write to the working directory or the package library. On the R side the
  temp-dir rule is CRAN policy, not taste.
- The cached metadata parquet makes the sniff **once per session**; a stale cache under a superseded
  release tag is the single most common cause of "this worked yesterday". Clearing the cache — the
  temp dir in R, `~/.cache/geobr` in Python — is the first diagnostic step, not the last.
- `cache = FALSE` must actually force a re-download, not read the cached file.

## 5. Failure modes must be loud

A failed sniff, a failed download, or a filter that matches zero rows must produce an **actionable,
typed** failure naming what was unavailable:

- R: `cli::cli_abort()` / `cli::cli_alert_danger()` + `invisible(NULL)`, following the established
  pattern in `utils.R`.
- Python: a real exception (`ConnectionError`, `ValueError`) listing the available values —
  `select_metadata_v2()` is the model to copy.

**Never return an empty `sf` / `GeoDataFrame` to signal failure.** A silent empty result becomes a
wrong map in someone's paper.

## 6. Tests

R marks every test with `skip_on_cran()`, which covers CRAN. It deliberately does **not** use
`skip_if_offline()`, so the R suite requires a live connection locally. Python marks its online
tests `@pytest.mark.network` and CI runs `-m "not network"`, so the Python default suite is
offline-safe. The asymmetry is intentional — **do not propose adding `skip_if_offline()` to the
R tests.** What it costs you: in an R run, a network outage and a real regression look the same,
so confirm connectivity (and the proxy, see MEMORY.md) before reading failures as regressions.

## Cross-references

- [`r-package-conventions.md`](r-package-conventions.md) · [`python-package-conventions.md`](python-package-conventions.md)
- [`cross-language-parity.md`](cross-language-parity.md)
- [`../skills/diagnose/SKILL.md`](../skills/diagnose/SKILL.md) — stale-cache and re-release triage.
