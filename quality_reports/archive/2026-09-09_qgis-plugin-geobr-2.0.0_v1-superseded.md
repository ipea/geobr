# Plan — Update the QGIS plugin for geobr Python 2.0.0

**Status:** DRAFT — awaiting approval
**Date:** 2026-09-09
**Subject:** `qgis-plugin/geobr_qgis/` → sync with `python-v2.0.0`
**Plugin version:** 0.1.0 → 0.2.0 (stays `experimental=True`)

---

## 0. Verification basis

Everything below was read from source and git history in this repo. **Nothing was executed** —
this machine has no Python toolchain (`CLAUDE.md` § Commands), and the readers need network access
besides. Treat every behavioural claim as *accurate-to-source*, not empirically confirmed. §5 says
who verifies what, and where.

Anchors:

- `python-v2.0.0` = commit `5696dacf` (merge of #451). Confirmed against `origin` via `git ls-remote --tags`.
- The plugin was authored at `af2fb3ed` ("Make cache temporary and version update") — the last commit
  that touched **both** `qgis-plugin/` and `python-package/`.
- The delta the plugin has not absorbed is therefore `af2fb3ed..python-v2.0.0`, five commits:
  `10255ca5` docstrings · `c8624c3c` argument orders · `ff9d217a` point geography ·
  `eef9eaf8` python docs · `85130aa3` version + descriptions.

---

## 1. What changed in geobr 2.0.0, and what it does to the plugin

The plugin derives its Processing parameters from geobr's **source**, by `ast`, rather than by
importing it (`provider.py:103` `discover_readers`). That design absorbs additive change for free
and is why most of this delta costs nothing. It also means the plugin is coupled to geobr's *source
shape*, which is exactly what 2.0.0 altered.

| # | Change in geobr 2.0.0 | Evidence | Effect on the plugin | Severity |
|---|---|---|---|---|
| 1 | Shared parameter docs moved to a `@docparams` decorator that substitutes `{year}`, `{code_state}`, … **at import time** | `geobr/_docstrings.py:209-238`; every `read_*.py` | `ast.get_docstring()` (`provider.py:128`) reads the **undecorated source**, so `shortHelpString()` now renders literal `{year}` / `{code_state}` tokens in every algorithm's QGIS help panel | **CRITICAL** — user-visible regression |
| 2 | `read_health_region`'s `geometry_level` now works: aggregation drops columns by **prefix**, so `code_muni6` no longer survives the `GROUP BY` | `geobr/read_health_region.py:68-83`; `tests/test_read_health_region.py:26` | `_SKIP_PER_READER = {"read_health_region": {"geometry_level"}}` (`algorithm.py:61`) suppresses a control that is now correct — the plugin withholds working functionality | **MAJOR** |
| 3 | Argument order changed in all 31 readers for R parity — `verbose` moved to last | `tests/test_reader_argument_order.py` pins it | Absorbed automatically, but **parameter order in the QGIS dialog changes**. No functional break | MINOR (behavioural) |
| 4 | `simplified` removed from 5 point readers (`read_schools`, `read_municipal_seat`, `read_health_facilities`, `read_polling_places`, `read_statistical_grid`) | `tests/test_point_reader_signatures.py` | Absorbed automatically — the parameter simply stops appearing. Correct | none |
| 5 | `read_capitals` gained `year: int = 2010` | `geobr/read_capitals.py:6` | Absorbed automatically | none |
| 6 | `read_comparable_areas` gained `show_progress` / `cache` (accepted and discarded, `del show_progress, cache`) | `geobr/read_comparable_areas.py:54-57` | The comment at `algorithm.py:44-46` claiming it "declares none of them" is now **false**. The reader stays excluded, so no runtime effect | MINOR (stale comment) |
| 7 | Duplicate `_simplified_attempts` definition removed | `geobr/utils.py` diff | None — plugin never touched it | none |
| 8 | Version → 2.0.0; `GEOBR_DATA_RELEASE` still `"v2.0.0"` | `pyproject.toml:3`, `geobr/utils.py:20` | Plugin hardcodes no tag. Correct by construction | none |

### 1.1 Assumptions that 2.0.0 did **not** invalidate — verified, keep as-is

Each of these was re-checked against 2.0.0 source rather than assumed to still hold:

- **`_EXCLUDED_READERS = {"read_comparable_areas"}`** (`provider.py:39`) — still justified.
  `url_solver()` still calls `requests.get(url)` with **no timeout** (`geobr/utils.py:40`), and the
  reader is still on the legacy gpkg path (`download_gpkg`), which its own docstring now describes
  as "suspended". A hang there is uncancellable inside a Processing worker.
- **`_GEOBR_LOCK`** (`algorithm.py:40`) — `_CONN` is still a module-global DuckDB connection
  (`_duckdb_backend.py:11`), so concurrent reader calls still collide.
- **`_validate_code`** (`algorithm.py:243`) — `read_filter_parquet_relation` still falls through to
  `return rel` **unfiltered** when no pattern matches (`_duckdb_backend.py:561`). Pre-validation is
  still the only thing between a typo and a whole-country layer.
- **`_SKIP = {"macro"}`** (`algorithm.py:56`) — `macro=None` is still in `read_health_region`'s
  signature and still deprecated.
- **`_ENUM_ARGS`** (`algorithm.py:65`) — values still match upstream exactly: `zone` ∈
  {`urban`, `rural`} (`read_census_tract.py:32`), `geometry_level` ∈ {`municipality`, `micro`,
  `macro`} (`read_health_region.py:44`).
- **`_FORCED`** (`algorithm.py:47`) — `output` / `show_progress` / `cache` / `verbose` all still
  exist with the same meanings; the `k in declared` guard still handles readers that omit them.
- **Dependency bounds unchanged** — `geopandas<=1.1.2`, `shapely<=2.1.0` (`pyproject.toml:18-19`).
  QGIS 4.2.1 still ships 1.1.4 / 2.1.2, i.e. still outside geobr's declared bounds. The pandas-3
  `regex=False` fix **is** present (`geobr/utils.py:151-160, 395, 431-435`), so the README's
  "requires a geobr newer than 1.0.0" caveat is satisfied by 2.0.0 and should be restated in those
  terms.
- **`qgisMinimumVersion=3.40`** — geobr still requires Python ≥3.10 (`pyproject.toml:6`), so the
  floor's justification is unchanged.

---

## 2. Decisions taken (confirmed with the maintainer, 2026-09-09)

| Decision | Choice | Consequence to accept |
|---|---|---|
| Guard against an older geobr | **No version check.** Keep presence-only probing (`__init__.py:17`) | A user still on geobr 1.0.0 gets a `geometry_level` control that silently returns municipality-level data for all three settings (change #2 above), with no warning. This is a knowing trade for a smaller surface. Mitigated only by documentation — §3.5 |
| Plugin version / status | **0.2.0, `experimental=True` retained** | Plugin stays behind the "show experimental plugins" opt-in until exercised against 2.0.0 in a real QGIS |
| Scope | **Fixes + qgis-free discovery module + tests + CI** | Adds ~2 files and one workflow; buys a standing regression check on the AST coupling that caused change #1 |

---

## 3. Change set

Ordered so each phase is independently reviewable. Phases 1–2 are the actual breakage; 3–4 are the
structural work the scope decision bought; 5 is documentation.

### Phase 1 — Restore algorithm help text (change #1, CRITICAL)

**Problem.** `docparams` substitutes at *import* time; the plugin reads source and never imports.
Importing `geobr._docstrings` is not an option: it would execute `geobr/__init__.py` first, pulling
in pandas/geopandas/duckdb — the ~4 s warm / ~29 s cold cost the whole discovery design exists to
avoid.

**Fix.** Mirror the substitution by AST, consistent with the existing design. In the new
`discovery.py` (Phase 3):

1. `_shared_params(package_dir)` — AST-parse `_docstrings.py`, find the `PARAMS` assignment, and
   `ast.literal_eval` it. It is a flat `dict[str, str]` of literals, so this is safe. Return `{}` on
   `OSError`/`SyntaxError`/`ValueError`, or if the file is absent (a geobr 1.0.0 install — the
   no-version-check decision makes this path reachable, and it must degrade to today's behaviour,
   not crash).
2. `_render_doc(doc, params)` — reproduce `docparams` (`_docstrings.py:225-236`): for each key, if
   `"{" + name + "}"` occurs, detect the indentation of the line where the token sits alone,
   `textwrap.indent(block, indent).lstrip()`, plain `str.replace`. Unknown tokens are left
   untouched, exactly as upstream does.
3. `discover_readers()` calls `_render_doc(ast.get_docstring(node) or "", params)` at
   `provider.py:128`.

**Two details that matter.** `ast.get_docstring()` defaults to `clean=True`, so the common 4-space
indent is already stripped and tokens sit at column 0 — `textwrap.indent(block, "")` then places the
numpydoc block correctly. Upstream substitutes on the *raw* docstring at indent 4 and lets the
consumer clean it; the result is the same, but the plugin must not double-clean. And the token-vs-key
overlap is safe: `"{code_muni}"` is not a substring of `"{code_muni_required}"`, so replacement order
is irrelevant.

*Files:* `discovery.py` (new), `provider.py`.

### Phase 2 — Re-expose `read_health_region`'s `geometry_level` (change #2, MAJOR)

Delete `_SKIP_PER_READER` (`algorithm.py:59-61`) and its use at `algorithm.py:132`. `_ENUM_ARGS`
already carries the right options and default, so the parameter appears with no further work.
Keep `_SKIP = {"macro"}` — the reasoning there (an unset optional arrives as `""`, which is not
`None`, so the deprecation branch fires and overwrites `geometry_level`) is unaffected and still
load-bearing.

*Files:* `algorithm.py`.

### Phase 3 — Split discovery from QGIS (enables Phase 4)

`provider.py` imports `qgis.core` and `qgis.PyQt` at module scope, so nothing in it can be tested
without a QGIS runtime — which is why the Phase 1 regression went unnoticed. Move the pure-AST layer
into `geobr_qgis/discovery.py`, **importing nothing from `qgis`**:

- `ReaderSpec`, `_Required` / `REQUIRED`, `_EXCLUDED_READERS`
- `_package_dir`, `_parse`, `_exported_readers`, `_signature`, `discover_readers`
- the new `_shared_params`, `_render_doc`

`REQUIRED` moves out of `algorithm.py:33` (where it currently forces `provider.py` to import a
qgis-dependent module just to get a sentinel); `algorithm.py` and `provider.py` both import it from
`discovery.py`. `provider.py` keeps `GeobrProvider`; `algorithm.py` keeps everything else. Also move
`PIP_COMMAND` (`algorithm.py:35`) to `discovery.py` so `__init__.py`'s startup-path import
(`__init__.py:12`) no longer drags in `qgis.core` transitively through `algorithm.py`.

This is a move, not a rewrite: no behaviour changes in this phase.

*Files:* `discovery.py` (new), `provider.py`, `algorithm.py`, `__init__.py`.

### Phase 4 — Tests + CI

`qgis-plugin/tests/test_discovery.py`, plain pytest, **no QGIS import**, run against the
`python-package/geobr` source tree in this repo:

1. **No unsubstituted tokens** — for every discovered reader, `re.search(r"\{[a-z_]+\}", spec.doc)`
   finds nothing. This is the direct regression test for change #1, and mirrors
   `python-package/tests/test_docstrings.py:31`.
2. **Derived parameter table matches geobr's real signatures** — reuse the
   `R_ARGUMENT_ORDER` contract already pinned in `python-package/tests/test_reader_argument_order.py`
   and assert `discover_readers()` reproduces each reader's argument names in order. This is the
   guard against a future signature change drifting past the plugin.
3. **`REQUIRED` sentinel placement** — `read_census_tract.code_tract` and
   `read_statistical_grid.code_muni` have no default and must come back as `REQUIRED`;
   `read_capitals.year` must come back as `2010`.
4. **Exclusions and skips** — `read_comparable_areas` absent from discovery;
   `geometry_level` **present** for `read_health_region` (locks Phase 2 in).
5. **Graceful degradation** — `_shared_params()` on a directory with no `_docstrings.py` returns
   `{}` and `_render_doc` is a no-op, so a geobr 1.0.0 install still yields usable (if plainer) help.

`.github/workflows/qgis-plugin-check.yaml` — `pull_request` / `push` on paths
`qgis-plugin/**` **and** `python-package/geobr/**` (the second path is the point: a geobr signature
change should fail *this* job). Ubuntu, Python 3.12, `pip install pytest`, no geobr install needed —
discovery reads the sibling source tree. Adds a compileall/`ruff` syntax pass over `geobr_qgis/`.

*Files:* `qgis-plugin/tests/test_discovery.py` (new), `.github/workflows/qgis-plugin-check.yaml` (new).

### Phase 5 — Version, metadata and documentation

**`metadata.txt`**
- `version=0.1.0` → `0.2.0`; keep `experimental=True`.
- Prepend a `0.2.0` changelog entry: geobr 2.0.0 support; restored algorithm help text;
  `geometry_level` exposed for health regions; note the reader argument-order change.
- `about=`: change the install command to `pip install --user "geobr>=2.0.0"`. This is the only
  place the minimum is stated, given the no-version-check decision.

**`cache.py`** — every version string in this file is wrong. The persistent `~/.cache/geobr`
behaviour was geobr **1.0.0**; the per-session temp cache it contrasts against shipped in
**2.0.0**, not the "1.0.1" written at `cache.py:3, 37, 83`. Rewrite those references
(`cache.py:3-9, 28-45, 60, 77-93`). The `cache_dirs()` logic itself is correct and unchanged — it
deliberately matches only the legacy `…/geobr` directories, never a live `Temp/geobr_<random>`
session dir (`_cache.py:38`). No code change, docs only.

**`algorithm.py:44-46`** — correct the `_FORCED` comment (change #6): `read_comparable_areas` now
declares `show_progress`, `cache` and `verbose`, and the `k in declared` guard is what actually
makes the omission of `output` safe.

**`README.md`**
- Install: `pip install --user "geobr>=2.0.0"`.
- *Known limitations* → strike the `read_health_region` bullet entirely (fixed upstream, Phase 2).
- *Known limitations* → the pandas-3 / geopandas-bounds bullet: replace "requires a geobr newer than
  1.0.0" with "requires geobr ≥ 2.0.0", and keep the bounds warning — QGIS 4.2.1's geopandas 1.1.4 /
  shapely 2.1.2 are still outside geobr 2.0.0's declared pins.
- *Known limitations* → the caching bullet: "As of geobr 1.0.1" → "As of geobr 2.0.0".
- *Known limitations* → keep the `read_comparable_areas` and `qgis_process`/duckdb bullets verbatim;
  both were re-verified against 2.0.0 source (§1.1).
- *Layout* → add `discovery.py` and `tests/`.
- New sentence under *How it works*: the plugin reproduces geobr's `@docparams` substitution when
  reading docstrings from source, and CI checks it.

---

## 4. Files touched

| File | Phase | Change |
|---|---|---|
| `qgis-plugin/geobr_qgis/discovery.py` | 1, 3 | **new** — qgis-free AST discovery + docstring substitution |
| `qgis-plugin/geobr_qgis/provider.py` | 1, 3 | discovery moved out; keeps `GeobrProvider` |
| `qgis-plugin/geobr_qgis/algorithm.py` | 2, 3, 5 | drop `_SKIP_PER_READER`; import `REQUIRED`/`PIP_COMMAND` from `discovery`; comment fix |
| `qgis-plugin/geobr_qgis/__init__.py` | 3 | import `PIP_COMMAND` from `discovery` |
| `qgis-plugin/geobr_qgis/cache.py` | 5 | version references only |
| `qgis-plugin/geobr_qgis/metadata.txt` | 5 | 0.2.0, changelog, install command |
| `qgis-plugin/README.md` | 5 | install, limitations, layout |
| `qgis-plugin/tests/test_discovery.py` | 4 | **new** |
| `.github/workflows/qgis-plugin-check.yaml` | 4 | **new** |

No change to `python-package/` — geobr 2.0.0 is the fixed target here, not a thing to adjust.

---

## 5. Verification

**Runs in CI (Phase 4) — the only automated gate.** The five test groups in §3 Phase 4. This is
what actually proves Phases 1–3, and it is the deliverable that makes the next geobr release cheap
to absorb.

**Cannot run here — stated as SKIPPED, not faked.** No Python toolchain and no local QGIS on this
machine (`CLAUDE.md` § Commands). The following require the maintainer, in QGIS, with `geobr>=2.0.0`
installed into QGIS's own interpreter:

| # | Check | Expected |
|---|---|---|
| V1 | Open any algorithm's help panel | Prose parameter docs, **no `{year}`-style tokens** |
| V2 | `geobr:read_health_region`, RJ, `geometry_level=micro` | Fewer features than `municipality` (RJ: 9 health regions vs 92 municipalities) |
| V3 | `geobr:read_health_region`, RJ, `geometry_level=macro` | 1 feature |
| V4 | `geobr:read_schools` | No `Simplified` parameter in the dialog |
| V5 | `geobr:read_capitals` | `Year` present, defaulting to 2010 |
| V6 | Any reader, `code_state=ZZ` | Rejected before download, not a whole-country layer |
| V7 | Plugin loads with geobr 1.0.0 installed | Loads; help text plainer but not tokenised; `geometry_level` present but inert (the accepted cost of §2's no-version-check decision) |

V2/V3 are the ones that could still surprise us: the upstream fix is verified by
`test_read_health_region.py` only as "not empty", not as a feature-count reduction. If V2 returns 92
features for RJ, Phase 2 reverts and `_SKIP_PER_READER` comes back — that outcome is a geobr bug, not
a plugin bug, and would need an upstream issue.

---

## 6. Out of scope

- **Exposing `list_geobr`, `lookup_muni`, `query()`/`session()`.** geobr 2.0.0 exports a DuckDB
  power-user API and two non-spatial helpers. None returns a layer, so none maps onto a Processing
  algorithm without new UI. Separate proposal.
- **Relaxing geobr's `geopandas`/`shapely` pins** to cover what QGIS 4.2.1 ships. That is a
  `python-package/` decision with CRAN-adjacent parity implications, not a plugin change.
- **The `qgis_process` duckdb finalization crash.** Upstream duckdb/CPython, unchanged by 2.0.0,
  documented as a known limitation.
- **Publishing 0.2.0 to plugins.qgis.org.** Covered by
  `quality_reports/plans/2026-09-02_qgis-plugin-publication.md`; run that after V1–V7 pass.
- **Any commit.** Requires an explicit `/commit`.

---

## 7. Bookend

**Goal:** bring `qgis-plugin/` into agreement with geobr Python `python-v2.0.0` — fix what the
release broke, surface what it fixed, and leave a standing check so the next release does not
repeat this.

**Met when:** Phases 1–5 are applied, CI is green, and V1–V7 pass in QGIS with `geobr>=2.0.0`.
