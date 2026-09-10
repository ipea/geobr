# Plan — Rebuild the QGIS plugin on geobr Python 2.0.0

**Status:** v2 — APPROVED (adversarial review reconciled). v1 archived at
`quality_reports/archive/2026-09-09_qgis-plugin-geobr-2.0.0_v1-superseded.md`.
**Date:** 2026-09-09
**Subject:** `qgis-plugin/geobr_qgis/` → built on `python-v2.0.0`, and only on it
**Plugin version:** 0.1.0 → 0.2.0 (`experimental=True` retained)

---

## 0. The governing constraint

**The plugin targets geobr Python ≥ 2.0.0. Earlier versions are unsupported and untested.**

This replaces v1's "no version check, degrade gracefully on 1.0.0" position. Everything that
existed only to tolerate geobr 1.0.0 is **deleted**, not softened. That single decision removes more
of this plan than it adds.

## 0.1 How this plan was verified

Static analysis and git only. **Nothing was executed** — no Python toolchain and no QGIS on this
machine (`CLAUDE.md` § Commands). v1 was then attacked by an independent adversarial reviewer with
fresh context, which found two factual errors and five defects v1 declared verified. Both errors
were re-confirmed at source before being accepted:

- v1 claimed `read_capitals` **gained** `year: int = 2010`. False — `git show af2fb3ed:…/read_capitals.py`
  shows it already had it, as the *last* argument. v2.0.0 only moved it to first. **No plugin effect.**
- v1 claimed `simplified` was dropped from **5** point readers. It was dropped from **3**
  (`read_schools`, `read_municipal_seat`, `read_health_facilities`); `read_polling_places` and
  `read_statistical_grid` never had it. The "5" was the size of `POINT_READERS` in
  `python-package/tests/test_point_reader_signatures.py:18-24`, not the size of the delta.

Anchors that survived review unchanged: `python-v2.0.0` = `5696dacf`; the plugin was authored at
`af2fb3ed`; exactly five `python-package` commits landed after it inside the tag
(`10255ca5`, `c8624c3c`, `ff9d217a`, `eef9eaf8`, `85130aa3`).

---

## 1. What actually needs doing, and why

Two things geobr 2.0.0 broke or unblocked, and five defects that predate it but were wrongly
declared safe in v1.

| # | Issue | Evidence | Severity |
|---|---|---|---|
| 1 | **Help text is tokenised.** `@docparams` substitutes `{year}`, `{code_state}` … at **import** time (`_docstrings.py:209-238`). The plugin reads source by `ast` and never imports, so `ast.get_docstring()` (`provider.py:128`) yields raw tokens straight into `shortHelpString()` (`algorithm.py:125`) | every reader is decorated, e.g. `read_state.py:5`, `read_health_region.py:9` | **CRITICAL** |
| 2 | **Help text renders as a run-on paragraph even once fixed.** `shortHelpString()` is rendered as rich text; a numpydoc block (hanging indents, hard breaks) collapses | QGIS renders algorithm help through a rich-text widget | **MAJOR** |
| 3 | **`geometry_level` is suppressed but now works.** v2.0.0 drops aggregation columns by **prefix**, so `code_muni6` no longer survives the `GROUP BY` | `read_health_region.py:68-83`; was exact-match at `af2fb3ed`; mirrors `r-package/R/read_health_region.R:115-121` | **MAJOR** |
| 4 | **`_CODE_RE` admits values that reach the unfiltered fall-through.** A 3-digit code is not 7, not ≤2, and fails `len(str(code)) > 3` — so it lands on `return rel`, **unfiltered** | `algorithm.py:73` vs `_duckdb_backend.py:539-561` | **MAJOR** |
| 5 | **Comma lists dispatch on `codes[0]` only.** `RJ,33` → `WHERE abbrev_state IN ('RJ','33')` → returns RJ silently. README advertises comma lists (`README.md:82`) | `_duckdb_backend.py:533-538` | **MAJOR** |
| 6 | **Required `year` has no bounds.** 26 readers take a required `year`; the param is built with `defaultValue=None` and no `minValue`, so the spin box opens on its minimum and that value validates | `algorithm.py:140-148` | **MAJOR** |
| 7 | **`_explain`'s network branch misses most failures.** Keys on `"connection"`/`"timed out"`; `download_parquet` raises `ConnectionError("A file may have been corrupted…")` (`utils.py:456-459`) which matches neither, and `_download_file` swallows the real `Timeout` (`utils.py:336-337`) so `"timed out"` is unreachable | `algorithm.py:276-281` | MINOR |

### 1.1 Re-verified and deliberately unchanged

Each was re-checked against 2.0.0 source, not assumed:

- **`_EXCLUDED_READERS = {"read_comparable_areas"}`** — `url_solver()` still calls `requests.get(url)`
  with no timeout (`utils.py:40`, bare `except: continue`), against `timeout=500`/`60` at `:308`,
  `:352`, `:367`. Still uncancellable inside a Processing worker. **Keep.**
- **`_GEOBR_LOCK`** — `_CONN` is still module-global (`_duckdb_backend.py:11`), views still registered
  by `{geo}_{year}` into it (`utils.py:485`). **Keep.**
- **`_SKIP = {"macro"}`** — keep the skip, **rewrite the reason**. v1's stated rationale (an unset
  optional arrives as `""`, which is truthy-not-`None`) is false: `_collect` already drops empty
  strings (`algorithm.py:238-240`). The real hazard is that `macro` is string-typed, so *any* value a
  user types is truthy and silently overrides `geometry_level` (`read_health_region.py:36-42`).
- **`_ENUM_ARGS`** — values still exact: `zone` ∈ {urban, rural} (`read_census_tract.py:31`),
  `geometry_level` ∈ {municipality, micro, macro} (`read_health_region.py:44`). **Keep.**
- **`_FORCED`** — all four still correct. `cache=True` is *more* right under 2.0.0, not less: the
  cache is now a per-session `mkdtemp` deleted at exit (`_cache.py:37-39`), so repeated reads inside
  one QGIS session are served from disk with **zero** staleness risk. **Keep.**
- **`DEPENDENCIES = ("geobr", "duckdb", "rapidfuzz")`** — correct in effect. `rapidfuzz` is imported
  at package-import time via `lookup_muni.py:4`, `duckdb` via `_duckdb_backend.py:9`; `lxml`/`html5lib`
  are declared in `pyproject.toml` but imported nowhere in `geobr/*.py`, so they cannot break
  `import geobr`. **Keep unchanged.**
- **Dependency bounds** — `geopandas<=1.1.2`, `shapely<=2.1.0` (`pyproject.toml:18-19`) still exclude
  what QGIS 4.2.1 ships (1.1.4 / 2.1.2). The pandas-3 `regex=False` fix is present
  (`utils.py:151-160, 395, 431-435`). README keeps the bounds warning, drops the 1.0.0 conditional.

---

## 2. Phases

### Phase 0 — Delete (first, because it shrinks everything after)

**0.1 — Delete `qgis-plugin/geobr_qgis/cache.py` entirely (154 lines).** Also drop its import
(`provider.py:23`) and unconditional registration (`provider.py:154-156`), and `README.md:136-143`.

The whole file exists to clean up `~/.cache/geobr`, which **only geobr 1.0.0 ever wrote**. geobr
2.0.0's `cache_dir()` is `Path(tempfile.mkdtemp(prefix="geobr_"))` (`_cache.py:37`) with `atexit`
teardown (`:39`) and a 30-day sweep of abandoned dirs (`:43-52`) — there is no 2.0.0 state for this
algorithm to clean. It is registered unconditionally, so a permanent toolbox entry would serve a
one-time historical chore forever; and it is a file-deleting code path aimed at a directory its own
help text admits is shared with other tools (`cache.py:88-91`). Under the v2.0.0-only constraint it
is pure liability.

Nothing is lost but discoverability, recovered in one README sentence: *geobr ≤ 1.0.0 cached
persistently in `~/.cache/geobr`; geobr 2.0.0 does not use it — if you ever ran the old version,
delete that directory once.*

**0.2 — Delete `_SKIP_PER_READER`** (`algorithm.py:55-61`) and its use (`:132`), plus the
`read_health_region` bullet at `README.md:112-118`. Closes issue #3.

**0.3 — Delete every 1.0.0 accommodation** from v1: the "graceful degradation" test, verification
item V7, and `README.md:109-111`'s "requires a geobr newer than 1.0.0 — on 1.0.0 the plugin works on
QGIS 4 only while a cache built elsewhere survives".

### Phase 1 — `discovery.py`: fix the help text, and make the AST layer testable

**Why the split is justified, not architecture.** `provider.py:19-20` imports `qgis.core`/`qgis.PyQt`
at module scope and `:22` imports `REQUIRED` from `algorithm.py`, which imports ten `Qgs*` symbols.
So *nothing* in the AST layer can be imported without a QGIS runtime — which is exactly why a
CRITICAL regression in `shortHelpString()` shipped unnoticed. The only alternative is a `conftest`
that stubs `sys.modules["qgis.core"]` with a fake exposing all ten names, which rots the moment an
eleventh is imported. The split is a pure move with no behaviour change.

New `qgis-plugin/geobr_qgis/discovery.py`, **importing nothing from `qgis`**, holding:
`ReaderSpec`, `_Required`/`REQUIRED`, `_EXCLUDED_READERS`, `_package_dir`, `_parse`,
`_exported_readers`, `_signature`, `discover_readers`, plus two new functions.

`PIP_COMMAND` **stays in `algorithm.py`.** v1 claimed moving it would stop `__init__.py` dragging in
`qgis.core` transitively — false: `__init__.py:11` already imports `qgis.core` directly, one line
above the `algorithm` import.

1. **`_shared_params(package_dir)`** — AST-parse `_docstrings.py`, find the `PARAMS` `Assign`,
   `ast.literal_eval` it (a flat `dict[str, str]` of literals). `except (OSError, SyntaxError,
   ValueError, AttributeError, TypeError): return {}` — as a guard against a *future* geobr moving
   the file, with no 1.0.0 rationale.
2. **`_render_doc(doc, params)`** — mirror `_docstrings.py:225-236`: per key, if `"{"+name+"}"` is
   present, detect the indent of the line where the token sits alone,
   `textwrap.indent(block, indent).lstrip()`, plain `str.replace`; unknown tokens left untouched.
   Do **not** re-clean — `ast.get_docstring(clean=True)` has already put tokens at column 0, so
   `textwrap.indent(block, "")` seats the numpydoc block correctly (verified). Then, for issue #2,
   `html.escape()` the result and wrap it in `<pre>` so the rich-text widget preserves the layout.
   *(Whole-document `<pre>` rather than splitting on the numpydoc header — same outcome, less
   machinery. V1 confirms the rendering; the fallback if `<pre>` renders badly is `<br>`-joining.)*
3. **`discover_readers(package_dir=None)`** — an explicit `package_dir` makes the tests
   deterministic without any `sys.path` manipulation for geobr; `None` keeps the QGIS runtime path
   through `_package_dir()`.
4. **Widen the except tuple** in `discover_readers` to `(OSError, SyntaxError, AttributeError,
   TypeError)`. `_exported_readers` does `node.value.elts` unguarded (`provider.py:65`); `__all__` is
   a list literal today, but a future `sorted(...)` would raise `AttributeError` past the current
   `except (OSError, SyntaxError)` and take `loadAlgorithms()` down with it.

`provider.py` keeps only `GeobrProvider`; `algorithm.py` imports `REQUIRED` from `.discovery`.

### Phase 2 — Correctness fixes in `algorithm.py`

5. **Issue #4** — `_CODE_RE` → `^(all|[A-Za-z]{2}|\d{1,2}|\d{4,})$`. Excludes only the *provably*
   unmatchable 3-digit case. 4–6-digit codes stay legal: they are legitimate for
   `code_meso`/`code_micro`/`code_immediate`/`code_weighting` via the length-matching branch
   (`_duckdb_backend.py:552-559`), so narrowing further would reject valid input.
6. **Issue #5** — `_validate_code` classifies each comma-separated part (alpha-2 / ≤2-digit /
   7-digit / other-numeric) and rejects the list if the classes differ, naming the offending part.
7. **Issue #6** — bound the numeric parameters: `date` → `minValue=187201, maxValue=999912`
   (`YYYYMM`); `year`/`start_year`/`end_year` → `minValue=1872, maxValue=9999`. 1872 is geobr's own
   earliest year (`read_comparable_areas.py:60`).
8. **Issue #7** — `_explain`'s network branch also matches `isinstance(exc, ConnectionError)`.
9. **Comments** — rewrite `_SKIP`'s rationale (§1.1) and `_FORCED`'s (`algorithm.py:44-46`), which
   claims `read_comparable_areas` "declares none of them"; it now declares `show_progress`, `cache`
   and `verbose` (`read_comparable_areas.py:53-56`).

`start_year`/`end_year` stay in `_YEAR_ARGS` (`algorithm.py:63`) although their only consumer is
excluded — they cost nothing and are correct if that reader is ever re-enabled.

### Phase 3 — Tests + CI

**The trap v1 fell into.** v1 said the tests would "read the sibling source tree, no geobr install
needed". False: `_package_dir()` uses `importlib.util.find_spec("geobr")` (`provider.py:42-50`), which
returns `None` when geobr is not installed, so `discover_readers()` returns `[]`, every parametrised
test collects **zero cases and passes green**. A suite that cannot fail is worse than none. Fixed by
Phase 1's explicit `package_dir` **and** by making the count assertion first.

`qgis-plugin/tests/conftest.py` — puts `qgis-plugin/geobr_qgis` on `sys.path` so `discovery` imports
as a **top-level module**. It cannot be imported as `geobr_qgis.discovery`, because
`geobr_qgis/__init__.py:11` imports `qgis.core`.

`qgis-plugin/tests/test_discovery.py` — four tests, not v1's five groups:

1. `test_discovery_is_not_empty` — `assert len(specs) == 30` (31 `read_*` in `__all__` minus the
   exclusion). **Load-bearing:** this is what fails if discovery silently returns nothing.
2. `test_no_unsubstituted_tokens` — no `\{[a-z_]+\}` survives in any spec's doc. The direct
   regression test for issue #1; mirrors `python-package/tests/test_docstrings.py:28-33`.
3. `test_anchor_signatures` — six hand-picked assertions covering every shape `_signature` must
   handle, **not** a copy of the 31-row table (that contract already lives in
   `python-package/tests/test_reader_argument_order.py` and would drift if duplicated):
   `read_census_tract.code_tract is REQUIRED`; `read_statistical_grid.code_muni is REQUIRED`;
   `read_capitals.year == 2010` and is first; `read_municipality`'s last param is
   `keep_areas_operacionais`; `simplified` absent from `read_schools`; `read_health_facilities`
   starts with `date`.
4. `test_exclusions` — `read_comparable_areas` is not discovered.

Plus `test_help_is_html` for issue #2 on one anchor reader.

`.github/workflows/qgis-plugin-check.yaml` — ubuntu, Python 3.12, `pip install pytest`, then
`pytest qgis-plugin/tests` and `python -m compileall qgis-plugin/geobr_qgis` (the only check that
touches `algorithm.py`/`provider.py`/`__init__.py` at all in a QGIS-free runner). Triggers on
`qgis-plugin/**`, `python-package/geobr/**` — *that second path is the point: a geobr signature
change must fail the plugin's job* — and the workflow file itself. **No ruff**: there is no ruff
config anywhere in this repo, and adding a linter as a side effect of a sync is scope creep.

### Phase 4 — Metadata and documentation

10. **`metadata.txt`** — `version=0.2.0`; keep `experimental=True`; install command →
    `pip install --user "geobr>=2.0.0"`; changelog entry (restored help text, `geometry_level`
    exposed, reader argument order changed, cache-clearing algorithm removed).
11. **`README.md`** — install `>=2.0.0`; delete the `read_health_region` and cache-clearing bullets;
    replace the pandas-3 bullet's 1.0.0 conditional with a flat "requires geobr ≥ 2.0.0" while
    keeping the geopandas/shapely bounds warning; soften `README.md:84`'s "Anything else is rejected"
    to match what the regex actually delivers (issue #4); note that `zone` only takes effect for
    census years ≤ 2007 (`read_census_tract.py:37-40`) — inert otherwise; keep the
    `read_comparable_areas`, `qgis_process`/duckdb, float-codes and Shapefile bullets verbatim;
    update Layout (drop `cache.py`, add `discovery.py`, `tests/`); one line on reproducing
    `@docparams` and the CI check.
12. **`CLAUDE.md`** — its "Python Package Architecture" section still describes the cache as
    persistent in `~/.cache/geobr`, "never expires and has no size cap", and calls it "the sharpest
    divergence" from R. That is 1.0.0 behaviour; `_cache.py:26-52` has been a per-session `mkdtemp`
    with `atexit` teardown since. Any future session reasoning from that paragraph starts from a
    false model. Correct it.

---

## 3. Files touched

| File | Phase | Change |
|---|---|---|
| `qgis-plugin/geobr_qgis/cache.py` | 0 | **deleted** |
| `qgis-plugin/geobr_qgis/discovery.py` | 1 | **new** — qgis-free AST discovery, docstring substitution, HTML |
| `qgis-plugin/geobr_qgis/provider.py` | 0, 1 | discovery moved out; cache algorithm unregistered |
| `qgis-plugin/geobr_qgis/algorithm.py` | 0, 2 | drop `_SKIP_PER_READER`; code/year validation; `_explain`; comments |
| `qgis-plugin/geobr_qgis/metadata.txt` | 4 | 0.2.0, changelog, install command |
| `qgis-plugin/README.md` | 0, 4 | install, limitations, layout |
| `qgis-plugin/tests/conftest.py` | 3 | **new** |
| `qgis-plugin/tests/test_discovery.py` | 3 | **new** |
| `.github/workflows/qgis-plugin-check.yaml` | 3 | **new** |
| `CLAUDE.md` | 4 | correct the stale Python-cache paragraph |

`__init__.py` is untouched. No change to `python-package/` — geobr 2.0.0 is the fixed target.

---

## 4. Verification

**Automated (Phase 3) — the only gate that runs anywhere.** The five tests above, in CI.

**Manual — requires the maintainer, in QGIS, with `geobr>=2.0.0`.** Cannot run here: no Python
toolchain, no QGIS, and the readers need network.

| # | Check | Expected |
|---|---|---|
| V1 | Any algorithm's help panel | Prose parameter docs — **no `{year}` tokens**, and readable layout rather than one collapsed paragraph |
| V2 | `read_health_region`, RJ, `geometry_level=micro` | Fewer features than `municipality` (RJ: 9 health regions vs 92 municipalities) |
| V3 | `read_health_region`, RJ, `geometry_level=macro` | 1 feature |
| V4 | `read_schools` | No `Simplified` parameter |
| V5 | Any reader, `code_state=331` | **Rejected before download** (issue #4). Note `ZZ` is *not* pre-rejected — two letters are a legal shape; it downloads, returns zero rows, and errors at `algorithm.py:216-220` |
| V6 | Any reader, `code_state=RJ,33` | Rejected as a mixed-shape list (issue #5) |
| V7 | Any reader's `Year` field | Opens on a plausible value, not the spin box's minimum |

**V2/V3 remain the only real check on upstream's `geometry_level` fix.** The upstream test
(`tests/test_read_health_region.py:25-28`) asserts only `not gdf.empty` and never counts features,
and the prefix-based drop only removes `geometry|code_muni*|name_muni*` plus the other level's health
columns — any other municipality-varying column in the parquet would still defeat the `GROUP BY`.
Nothing in-repo enumerates that column set, so it is unverifiable statically. If V2 returns 92
features for RJ, revert Phase 0.2 and open an upstream geobr issue; that is a geobr bug, not a
plugin bug.

---

## 5. Out of scope

- **Exposing `list_geobr`, `lookup_muni`, `query()`/`session()`** — none returns a layer.
- **Relaxing geobr's `geopandas`/`shapely` pins** to cover QGIS 4.2.1 — a `python-package/` decision.
- **The `qgis_process` duckdb finalization crash** — upstream, unchanged by 2.0.0.
- **Upstream bug worth an issue, not a plugin fix:** `download_metadata_v2`'s pinned-tag fallback
  builds rows without `download_url` (`utils.py:362-375`), which `read_geobr_v2` then dereferences
  (`:480`) → bare `KeyError`. The plugin would surface it opaquely.
- **`external_deps=geobr` in `metadata.txt`** — not a key plugins.qgis.org recognises; leave it.
- **Publishing 0.2.0** — see `quality_reports/plans/2026-09-02_qgis-plugin-publication.md`, after V1–V7.
- **Any commit** — requires an explicit `/commit`.

---

## 6. Bookend

**Goal:** rebuild `qgis-plugin/` on geobr Python 2.0.0 alone — delete what only served older
versions, fix what 2.0.0 broke, expose what it fixed, close five real validation holes, and leave a
CI check that fails when geobr's source shape drifts again.

**Met when:** Phases 0–4 applied, CI green, V1–V7 pass in QGIS with `geobr>=2.0.0`.
