# CLAUDE.md — geobr

**Project:** geobr — download official spatial data sets of Brazil
**Maintainer:** Rafael H. M. Pereira (Ipea) · **Repo:** `ipea/geobr` · **Default branch:** `master`
**Packages:** R `r-package/` (v2.0.1, CRAN) · Python `python-package/` (v1.0.0, PyPI)

---

## Core Principles

- **Plan first** — enter plan mode before non-trivial tasks; plans should be reviewed by an adversarial agent that tries to check and simplify plan. Once there is a consensus, plans go to `quality_reports/plans/`
- **Verify after** — run the touched package's tests and report the real output, never "should work"
- **Two languages, one package** — an API change on one side is incomplete until the other matches
- **Minimal intervention** — change what the task requires, nothing adjacent
- **[LEARN] tags** — when corrected, append `[LEARN:category] wrong → right` to [MEMORY.md](MEMORY.md)

Cross-session context: [MEMORY.md](MEMORY.md). Plans, specs, session logs: [quality_reports/](quality_reports/).

---

## Data Architecture

**All data lives outside this repo**, as release assets in
[`ipea/geobr_prep_data`](https://github.com/ipea/geobr_prep_data/releases). No spatial data is
committed here. Every `read_*()` call resolves data at runtime:

```
release tag (data_release)
   → sniff the release's *.parquet asset names
   → parse each name into a metadata row: file_name → geo · year · simplified
   → filter by (geography, year, simplified) to pick one file
   → build the download URL and fetch to the local cache (session temp dir in R, `~/.cache/geobr` in Python)
   → open with arrow/duckdb, filter, return sf / GeoDataFrame / duckdb relation
```

**Metadata sniffing differs by language** — a known divergence, not a bug to "fix" casually:

| | R | Python |
|---|---|---|
| Sniff | scrapes `releases/expanded_assets/<tag>` HTML for `*.parquet` | GitHub API `releases/latest`, falling back to the pinned tag |
| Release resolution | **pinned** to `geobr_env$data_release` | **latest-first**, pinned tag only as fallback |
| Entry point | `download_metadata2()` — `r-package/R/utils.R:266` | `download_metadata_v2()` — `python-package/geobr/utils.py:335` |
| Cache | `fs::path_temp("geobr")` | `_cache.cached_path()` |

Because Python asks for `latest` first, it can serve a **newer data release than R** for the same
package version. Keep this in mind whenever the two packages disagree about available years.

**Caching differs by language, and this is the sharpest divergence between them.** R writes to
the **per-session** temp dir (`fs::path_temp("geobr")`), so its cache dies with the R session.
Python writes to a **persistent** user cache (`~/.cache/geobr`, or `$XDG_CACHE_HOME/geobr`,
falling back to the system temp dir only if `mkdir` fails), which never expires and has no size
cap. A stale Python file under a superseded data release therefore survives reboots — clear it
first when R and Python disagree. Both cache the metadata table itself, so the sniff runs once
per session. `cache = FALSE` forces a re-download.

**The release tag is currently hardcoded in five places, in two formats** (`v2.0.0` and `data_v2.0.0`):
`r-package/R/onLoad.R:7`, `r-package/R/utils.R:4` (dead — assigned, never read),
`r-package/R/utils.R:380`, `python-package/geobr/utils.py:20`, `python-package/geobr/utils.py:24`.
Bumping a data release means touching all live copies. See
[`data-release-conventions.md`](.claude/rules/data-release-conventions.md).

---

## Layout

```
geobr/
├── CLAUDE.md                # this file
├── MEMORY.md                # cross-session learnings
├── .claude/                 # rules, skills, agents
├── r-package/               # R package (DESCRIPTION, R/, man/, tests/testthat/, vignettes/)
├── python-package/          # Python package (pyproject.toml, geobr/, tests/, helpers/)
├── docs/                    # pkgdown site (generated — do not hand-edit)
├── .github/workflows/       # R-CMD-check, Python-CMD-check, pkgdown, test-coverage
├── quality_reports/         # plans, specs, session logs, audits, archive
└── templates/               # session log, quality report, spec templates
```

`r-package/man/`, `r-package/NAMESPACE`, and `docs/` are **generated**. Edit roxygen blocks and
re-document; never hand-edit the outputs.

---

## Commands

```bash
# --- proxy: REQUIRED before any networked R work on this machine ---
# (WinINET has it; libcurl does not. Without these, every read_*() times out.)
$env:http_proxy  = "http://cache.ipea.gov.br:3128"   # PowerShell
$env:https_proxy = "http://cache.ipea.gov.br:3128"

# --- R (runs locally: R 4.6.1) ---
Rscript -e 'devtools::document("r-package")'          # regenerate man/ + NAMESPACE
Rscript -e 'devtools::test("r-package")'              # testthat suite
Rscript -e 'devtools::check("r-package", args="--as-cran")'   # release gate (slow)
Rscript -e 'covr::package_coverage("r-package")'   # covr NOT installed here — install first

# --- Python (NOT available on this machine — see below) ---
cd python-package && uv sync --frozen
cd python-package && uv run pytest -n 2 -m "not network"      # offline suite, mirrors CI
cd python-package && uv run pytest -m network                 # hits the data server

# --- parity ---
cd python-package && python helpers/diff_packages.py   # read_* present in R but not Python
```

**Toolchain on this machine:** R 4.6.1 ✓ · `python` ✗ · `uv` ✗ · `gh` ✗ · `conda` ✗ · no `.venv`.
**Network:** behind `cache.ipea.gov.br:3128`. Export `http_proxy`/`https_proxy` before any
networked R command — libcurl ignores the WinINET setting that PowerShell honours. The
sandboxed Bash tool has no outbound network at all; run networked commands via PowerShell.
Python work here is **edit-and-CI**: changes are reviewed statically and verified by
`.github/workflows/Python-CMD-check.yaml` (ubuntu/macOS/windows × py3.10–3.13). A skill that needs
Python must say `SKIPPED — no local Python` rather than emit a command that fails.

---

## Conventions

| | Rule |
|---|---|
| **Writes** | R: session temp dir only. Python: the persistent user cache `~/.cache/geobr`. Neither writes to the working directory or the package library. |
| **Release tag** | Reference the named constant; never inline a version string in a new URL. |
| **Network tests** | R: `skip_on_cran()` everywhere; `skip_if_offline()` deliberately **not** used, so the R suite needs a live connection locally (323 pass with the proxy set). Python: `@pytest.mark.network`; CI runs `-m "not network"`. |
| **R deps** | `@importFrom` or `pkg::fun()` in `R/`. Never `library()`/`require()` in package code. |
| **Python deps** | Declared in `pyproject.toml`, locked in `uv.lock`. CI runs `--frozen` — a dep change needs a relock. |
| **Public surface** | `read_*` is public in both packages. Python `_cache` / `_filter` / `_output` / `_duckdb_backend` are private. |
| **Parity** | A new/changed `read_*` argument lands on both sides, with the same name and default. |
| **Errors** | Actionable and typed: `cli::cli_abort()` in R, a real exception in Python. Never a silent empty result. |

---

## Installed Workflow Surfaces

**Rules** (`.claude/rules/`) — auto-load on matching paths:
`r-package-conventions` · `python-package-conventions` · `data-release-conventions` ·
`cross-language-parity` · `plan-first-workflow` · `session-logging` · `orchestrator-protocol` ·
`model-routing` · `prompt-shaping` · `summary-parity`

**Skills** (`.claude/skills/`):
- *Release gates:* `/r-package-check` · `/py-package-check` · `/parity-check`
- *Review:* `/review-r` · `/deep-audit` · `/diagnose`
- *Workflow:* `/commit` · `/checkpoint` · `/learn` · `/new-skill`

**Agents** (`.claude/agents/`):
`r-package-reviewer` · `python-package-reviewer` · `r-reviewer` · `verifier`

---

## Commit Policy

`/commit` stages, runs the **touched-package gate** (R changed → document-drift + `devtools::test()`;
Python changed → offline pytest if a toolchain exists, else an explicit SKIPPED), commits, and pushes
to the current branch. It does **not** auto-merge and does not require `gh`. Never commits
`.claude/settings.local.json` or credentials.


---

## R Package Architecture

Every `read_*()` is a thin, declarative wrapper over one shared pipeline. The reader itself holds
almost no logic — it names a geography, then delegates. `read_municipality()` is the reference
implementation; read it before changing any other reader.

### R overall workflow of functions

| # | Step | Function (`R/utils.R`) | Notes |
|---|---|---|---|
| 1 | Sniff the release, build a metadata table | `download_metadata2()` :266 | Scrapes `releases/expanded_assets/<data_release>` for `*.parquet`; parses each **filename** into `geo` / `year` / `simplified`. Shape is `file_name / geo / year / simplified` (505 rows across 28 geographies at `v2.0.0` — expect this to move with each data release). Cached as a parquet, so it runs once per session. |
| 2 | Filter the metadata to one row | `select_metadata()` :91 → `select_year_input()` :38 → `select_geometry_type()` :17 | Subsets on `geo`, then `year`, then `simplified`. An unavailable year aborts **here**, before any download, listing the years that do exist. |
| 3 | Download to the session cache | `download_parquet()` :349 | GitHub release URL, falling back to `ipea.gov.br`. Writes to `fs::path_temp("geobr")`. With `cache = TRUE` an existing file is reused; returns a lazy handle via `geobr_open_dataset()` (duckspatial), never a materialised table. |
| 4 | Filter rows | `filter_arrw()` :208 | Lazy `dplyr::filter()` on the duckdb relation. Returns early and unfiltered when `code = "all"`. Zero matches aborts. |
| 5 | Convert to the output format | `convert_output()` :471 | `"sf"` → `sf::st_as_sf()` · `"arrow"` → nanoarrow stream → `arrow::as_arrow_table()` · `"duckdb"` → returned as-is (lazy). |

Steps 3–5 are lazy until step 5: the duckdb relation is only materialised when `output = "sf"`.
That is what makes `output = "duckdb"` viable for the large data sets.

**`filter_arrw()` infers the column from the value**, which is why one `code_muni` argument accepts
four things. The checks are sequential (not `else if`), so the **last** match wins:

| Input | Detected column | Example |
|---|---|---|
| `"all"` | — returns early, no filter | `code_muni = "all"` |
| 2-letter uppercase abbreviation | `abbrev_state` | `"RJ"` → 92 municipalities |
| 2-digit state code | `code_state` | `33` → 92 municipalities |
| numeric, >3 digits | first column matching `^code_` | 6-digit legacy codes |
| exactly 7 digits | `code_muni` | `1200179` → 1 row |

### Canonical signature

```r
read_<geography>(year, code_<level> = "all", simplified = TRUE, output = "sf",
                 showProgress = TRUE, cache = TRUE, verbose = TRUE)
```

Argument order and defaults are a **contract across all 31 exported readers** — keep it. Shared parameter
docs live in `man/roxygen/templates/*.R` and are pulled in with `@template`, so a wording change
propagates to every reader; never paste a `@param` that has a template.

**Family variations** (all deliberate — do not "normalise" them):

- **`date` instead of `year`** (`YYYYMM`): `read_conservation_units`, `read_health_facilities`.
- **No `simplified`** — point geometries have nothing to simplify: `read_municipal_seat`,
  `read_polling_places`, `read_schools`, `read_statistical_grid`, `read_health_facilities`.
- **No `output`** — returns `sf` only: `read_comparable_areas` (also takes `start_year`/`end_year`).
- **No `year`**: `read_capitals`, which is *composed* rather than piped — it builds a hardcoded
  data.frame of the 27 capitals and calls `read_municipal_seat()`.
- **Extra arguments**: `read_census_tract(zone)`, `read_health_region(geometry_level, macro)`,
  `read_municipality(keep_areas_operacionais)`.
- **`year = NULL` default**: `read_state` only.

### Invariants and gotchas

- **Two failure styles coexist.** `select_metadata()` and `download_parquet()` signal failure by
  returning `NULL` (with a `cli` alert), so every reader repeats
  `if (is.null(x)) return(invisible(NULL))`. Deeper helpers (`select_year_input`, `filter_arrw`,
  `convert_output`) `cli_abort()` instead. Match the surrounding style rather than introducing a third.
- **`output` is validated late** — inside `convert_output()`, *after* the download. A typo
  (`output = "geojson"`) costs a full file download before it errors. Validating at entry would be a
  cheap improvement.
- **`convert_output()` is where CRS materialises**: returns `EPSG:4674` (SIRGAS 2000). Classes:
  `sf tbl_df tbl data.frame` · `duckspatial_df tbl_duckdb_connection …` · `Table ArrowTabular …`.
- **`select_metadata()` returns a data.frame, not a scalar.** Today each (geo, year, simplified)
  triple resolves to exactly one row, and `download_parquet()` assumes it. A duplicate asset name
  upstream would silently pass a length-2 vector into a single-file download.
- **Helpers read their arguments from the caller's frame** — `parent.frame()$year`,
  `parent.frame()$verbose`, `parent.frame()$temp_arrw`. Renaming a local variable inside a reader can
  therefore break a helper without any visible call-site change.
- **`# nocov start` / `# nocov end` wraps most of `utils.R`** — deliberate, since these paths need the
  network. Do not treat the resulting coverage numbers as a quality signal.
- **duckdb writes extensions to `~/.duckdb`**, outside the session temp dir. That is duckdb's own
  behaviour, not geobr's — but it is the one thing that escapes the temp-dir-only rule.

## Python Package Architecture

Same five steps as R, but the shared pipeline is a **named function** rather than a convention:
every reader delegates to `read_geobr_v2()`. Filtering is **DuckDB SQL**, not `dplyr`.

> Verified by reading the source only — this machine has no Python toolchain, so none of the
> runtime behaviour below was executed. Treat it as accurate-to-source, not empirically confirmed.

### Python overall workflow of functions

| # | Step | Function | Notes |
|---|---|---|---|
| 1 | Sniff the release, build a metadata table | `download_metadata_v2()` — `utils.py:336` | GitHub **API** (`releases/latest`), not HTML scraping. Falls back to the pinned `GEOBR_DATA_RELEASE` only if `latest` yields no parquet assets. `@lru_cache(maxsize=1)` + a cached parquet. Same derived columns as R: `file_name` / `geo` / `year` / `simplified`, plus `download_url`. |
| 2 | Filter the metadata to one row | `select_metadata_v2()` — `utils.py:389` | Returns a `pd.Series`. Raises `ValueError` listing available geographies/years. Takes a `zone` argument R lacks (census tracts). |
| 3 | Download to the cache | `download_parquet()` — `utils.py:423` | Release URL then `IPEA_FALLBACK_BASE`. Raises `ConnectionError` on failure. **Cache is `~/.cache/geobr`, not a temp dir** — see below. |
| 4 | Filter rows | `read_filter_parquet_relation()` — `_duckdb_backend.py:476` | Registers the parquet as a DuckDB view, then builds a `WHERE` clause. Lazy relation. |
| 5 | Convert to the output format | `convert_output()` — `_output.py:15` | `"gpd"` → WKB round-trip into a `GeoDataFrame` (+ `enforce_types`) · `"arrow"` → `to_arrow_table()` · `"duckdb"` → relation as-is. |

`read_geobr_v2()` (`utils.py:445`) chains all five. Readers pass `output="duckdb"` into it and call
`convert_output()` themselves afterwards, so a reader can post-process the relation in SQL first —
that is exactly how `read_municipality()` drops the Lagoa dos Patos / Lagoa Mirim polygons.

### Two things R does not have

- **`read_geobr_hybrid()`** (`utils.py:495`) — tries the v2 parquet pipeline, then falls back to the
  **legacy gpkg** path on `ValueError` / `ConnectionError` / `KeyError`, retrying with `simplified`
  toggled. `_GEO_LOADERS` (`_duckdb_backend.py:19`) records, per geography, the v2 name, the gpkg
  name, and whether it is `v2_only`. This legacy fallback has no R counterpart.
- **A SQL interface.** `query()` (`_duckdb_backend.py:393`) runs arbitrary SQL and **auto-resolves
  missing tables**: `SELECT * FROM municipalities_2020` downloads and registers that snapshot on the
  spot (bounded by `_MAX_RESOLUTIONS = 10`). A bare `FROM municipalities` picks a year and warns.
  `session()` / `GeoBrDuckDB` (`:525`) give an isolated connection; `to_geopandas()` (`:440`)
  converts a relation or view.

### Canonical signature — and where it diverges from R

```python
read_<geography>(year, code_<level>="all", simplified=True, verbose=False,
                 output="gpd", show_progress=True, cache=True)
```

The first argument matches R in **all 31 readers** (including `date` for `read_conservation_units`,
`read_health_facilities`, `read_quilombola_land`). Three divergences are **systematic**, not
one-offs:

| | R | Python | Scope |
|---|---|---|---|
| `output` default | `"sf"` | `"gpd"` | all 30 readers that take `output` |
| allowed `output` | `sf` / `arrow` / `duckdb` | `gpd` / `arrow` / `duckdb` | — |
| `verbose` default | `TRUE` | `False` | **all 31 readers** |
| progress argument | `showProgress` | `show_progress` | snake_case — idiomatic, not a defect |
| argument order | `… output, showProgress, cache, verbose` | `… verbose, output, show_progress, cache` | positional calls are not portable |

The first three are genuine API drift: the same call returns a differently-named type and is silent
in one language and chatty in the other. Decide deliberately before "fixing" either side — changing
a default is a breaking change for existing users.

### Invariants and gotchas

- **The cache is persistent and lives in the user's home** — `~/.cache/geobr`, or
  `$XDG_CACHE_HOME/geobr`, falling back to `tempfile.gettempdir()/geobr` **only if `mkdir` fails**
  (`_cache.py:9`). This is the sharpest divergence from R, whose cache dies with the session. It
  never expires and has no size cap, so a stale file under a superseded data release persists across
  sessions and reboots — the first thing to clear when Python and R disagree.
- **An unmatched code returns everything, silently.** `read_filter_parquet_relation()` tries
  abbreviation → 7-digit `code_muni` → ≤2-digit `code_state` → other `code_*`; if nothing matches it
  returns the **unfiltered** relation, and there is no zero-row check. R's `filter_arrw()` aborts in
  both cases. So an invalid code yields an empty or full result in Python where R raises.
- **The column is chosen from `codes[0]`** — a mixed-type list (`["RJ", 3304557]`) is dispatched on
  its first element and the rest are interpolated into that column's `WHERE`.
- **`_filter.filter_by_code()` is a second, independent filter implementation** (pandas, on
  GeoDataFrames, `_filter.py:38`) used by the legacy gpkg path. Two filters must agree; the SQL one
  is the v2 path.
- **The DuckDB connection is module-global** (`_CONN`, `_duckdb_backend.py:11`) and views are
  registered into it by name (`{geo}_{year}`). Tests must call `_reset_shared_connection()`; use
  `session()` for isolation.
- **`_setup_connection()` swallows every exception** when installing/loading `spatial` and `httpfs`
  (`:134`). If the spatial extension fails to load, the failure surfaces much later as a confusing
  SQL error rather than at connection time.
- **CRS**: `to_geopandas()` hardcodes `EPSG:4674`; `convert_output()` reads `ST_CRS(geometry)` and
  falls back to `EPSG:4674`.
- **Known code smells:** `_simplified_attempts()` is defined **twice, identically**
  (`utils.py:485` and `:490`); `convert_output()`'s docstring documents a `filter_code` parameter its
  signature does not have; `_GEO_LOADERS` marks `indigenousland` with `year_param: "date"` while
  `read_indigenous_land()` actually takes `year`.
