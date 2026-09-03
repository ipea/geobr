# Plan — geobr QGIS Plugin

**Status:** APPROVED — v2, reconciled with adversarial review (see §8)
**Date:** 2026-09-01
**Target:** `qgis-plugin/geobr/` — a QGIS Processing provider wrapping `python-package/geobr`

---

## 0. Verified environment facts (measured, not assumed)

Probed `C:\Program Files\QGIS 3.42.1` on this machine:

| Fact | Value | Consequence |
|---|---|---|
| QGIS Python | 3.12.9 | geobr requires `>=3.10` ✓ |
| `geopandas` | 1.0.1 | geobr pins `>=1.0.0,<=1.1.2` ✓ already satisfied |
| `shapely` | 2.0.6 | pin `>=1.7.0,<=2.1.0` ✓ |
| `pyarrow` | 18.1.0 | pin `>=15.0.0` ✓ |
| `requests` | 2.31.0 | pin `>=2.25.1,<3` ✓ |
| `pyogrio` | 0.9.0 | `gdf.to_file()` is fast, no fiona needed |
| `pandas` / `numpy` | 2.2.2 / 1.26.4 | ✓ |
| **`duckdb`** | **MISSING** | **hard blocker** — imported at module scope in `_output.py`, `_duckdb_backend.py` |
| **`rapidfuzz`** | **MISSING** | **hard blocker** — `lookup_muni.py` does `from rapidfuzz.distance import Jaro` at module scope, and `__init__.py` imports it, so `import geobr` fails outright |
| GDAL | 3.10.2, **Parquet driver present** | OGR can open geobr's `.parquet` assets directly |
| `pip` / user-site | 25.0 / `%APPDATA%\Python\Python312\site-packages`, enabled | `pip install --user` works without admin, does not touch Program Files |
| `qgis_process-qgis.bat` | present | **headless verification is possible** — this plan can be tested, not just asserted |

**The missing set is exactly `{duckdb, rapidfuzz}`.** Every heavy geo dependency is already
in QGIS. `pip install --user geobr` resolves to installing only `duckdb`, `rapidfuzz`,
`html5lib` (+ maybe `lxml`) — it will **not** shadow QGIS's geopandas/shapely/pyarrow, because the
installed versions already satisfy geobr's bounds. This is the single most important fact in the
plan: the bootstrap is cheap and safe.

---

## 1. Architecture decision: Processing provider, not a dialog

Per the `qgis-syntax-plugins` decision tree, "add a Processing algorithm → Processing provider
plugin". geobr is definitionally *parameters in → one vector layer out*, which is what a Processing
algorithm is.

Choosing Processing over a bespoke `QDialog` buys, for free:

- parameter UI generated from declarations (no `.ui` files, no `pyuic5`, no `resources.qrc`)
- execution on a **worker thread** with progress bar + cancel, handled by the framework
- batch mode, Model Builder, and the `qgis_process` CLI, at zero extra cost
- result layers auto-loaded into the project, with history and logging

A hand-built dialog would be more code and strictly less capable.

### Rejected alternative — reimplementing metadata resolution in the plugin

GDAL's Parquet driver means the plugin *could* skip geobr entirely: hit the GitHub API, resolve the
asset, download, and `QgsVectorLayer(path, name, "ogr")`. **Rejected.** That makes the plugin a
*third* implementation of the release-sniffing contract alongside R and Python, in a repo whose
governing rule (`cross-language-parity.md`) is that drift between implementations is a defect. It
would also silently lose reader-specific post-processing — `read_municipality()`'s Lagoa dos
Patos/Mirim removal, `read_capitals()`'s composition over `read_municipal_seat()`.

**The plugin calls the public `read_*()` functions and nothing else.** No private geobr API
(`_cache`, `_filter`, `_output`, `_duckdb_backend`) is touched.

---

## 2. The core trick: one generic algorithm, driven by `inspect.signature`

30 readers do **not** get 30 classes. One `GeobrAlgorithm` is instantiated once per reader name and
builds its own parameters by introspecting the function's signature.

The signatures survey (read from source) shows a stable shape with catalogued exceptions:

```
read_<geo>(year|date, code_<level>="all", simplified=True, verbose=False,
           output="gpd", show_progress=True, cache=True)
```

Exceptions, all handled by the same generic mapper because it dispatches on *parameter name and
default type*, not on a per-reader table:

| Reader | Deviation |
|---|---|
| `read_conservation_units`, `read_health_facilities`, `read_quilombola_land` | first arg is `date`, not `year` |
| `read_census_tract` | extra `zone="urban"` |
| `read_health_region` | extra `geometry_level="municipality"`, `macro=None` |
| `read_municipality` | extra `keep_areas_operacionais=False` |
| `read_comparable_areas` | `start_year`/`end_year`; no `output`/`cache`/`show_progress` |
| `read_capitals` | no `simplified`; `year=2010` default |
| `read_polling_places` | no `simplified` |
| `code_*` spelling | `code_state`, `code_muni`, `code_meso`, `code_micro`, `code_immediate`, `code_intermadiate` (upstream typo), `code_tract` |

### Mapping rules

| Signature parameter | QGIS parameter | Note |
|---|---|---|
| `year`, `date`, `start_year`, `end_year` | `QgsProcessingParameterNumber` (Integer) | required when the function has no default |
| `code_*` | `QgsProcessingParameterString`, default `"all"` | accepts `"RJ"`, `33`, `3304557` — geobr infers the column |
| `bool` default (`simplified`, `keep_areas_operacionais`) | `QgsProcessingParameterBoolean` | default taken from the signature, so `simplified=False` readers stay correct |
| `zone` | `QgsProcessingParameterEnum` `["urban","rural"]` | |
| any other `str` default | `QgsProcessingParameterString` | optional when default is `None` |
| `cache` | `QgsProcessingParameterBoolean`, advanced, default `True` | |
| `output`, `show_progress`, `verbose` | **not exposed** — forced to `"gpd"`, `False`, `False` | `show_progress`'s tqdm bar is meaningless in QGIS; `feedback` replaces it |

**Why the year is a Number and not an Enum of available years:** populating an enum requires
`download_metadata_v2()`, a network call with a 60 s timeout. `loadAlgorithms()` runs at QGIS
startup, and `initAlgorithm()` runs when the algorithm is registered — so an enum would block the
QGIS UI for up to a minute on every launch, and break startup offline. geobr already raises a
`ValueError` that *lists the available years*; the algorithm surfaces that text through
`QgsProcessingException`. Cheaper, offline-safe, and self-updating.

---

## 3. Output: let geopandas write the file, let QGIS read it

```python
dest = self.parameterAsOutputLayer(parameters, "OUTPUT", context)
gdf.to_file(dest, driver="GPKG", layer=<reader name>)
return {"OUTPUT": dest}
```

No feature-by-feature WKB marshalling into a `QgsFeatureSink`. `pyogrio` writes the GeoPackage,
Processing loads the path and auto-adds it to the project. CRS (EPSG:4674, SIRGAS 2000) is carried
by the GeoDataFrame and preserved by the driver. This is ~4 lines where a sink-based
implementation would be ~40 and slower (one extra full copy).

---

## 4. File layout

```
qgis-plugin/geobr/
├── __init__.py       # classFactory(iface) only
├── metadata.txt      # hasProcessingProvider=yes
├── plugin.py         # GeobrPlugin: initGui/unload, provider registration, dep prompt
├── provider.py       # GeobrProvider(QgsProcessingProvider)
├── algorithm.py      # GeobrAlgorithm — the generic, signature-driven algorithm
├── catalog.py        # reader discovery + toolbox grouping + display names
├── deps.py           # dependency probe, guided pip install, QGIS proxy bridging
├── icon.png
├── LICENSE
└── README.md
```

### `catalog.py`

Reader discovery is **introspective, not a hand-maintained list**: iterate `geobr.__all__`, keep
names starting with `read_`. A reader added to geobr appears in QGIS with no plugin change — this is
the same anti-drift discipline `cross-language-parity.md` demands of R↔Python.

Display name: `read_metro_area` → `"Metro area"`. Grouping: a small static
`GROUPS: dict[str, str]` (Administrative / Environment / Health & education / Other) consulted with
`.get(name, "Other")`, so an unknown new reader still shows up rather than breaking.

### `deps.py`

- `missing() -> list[str]` — probe `geobr`, `duckdb`, `rapidfuzz` by import.
- `install_command()` → `[sys.executable, "-m", "pip", "install", "--user", "geobr"]`.
- **Never installs silently.** `initGui` pushes a message-bar warning with an *Install* button; the
  install runs in a `QgsTask`; on success the user is told to restart QGIS (`provider.refreshAlgorithms()`
  is called, but a fresh interpreter is the honest advice for a new C-extension).
- **Proxy bridging** (`apply_qgis_proxy()`): geobr uses `requests`, which reads `http_proxy` /
  `https_proxy` from the environment and is *blind* to QGIS's own proxy settings. Read
  `QgsSettings` `proxy/proxyEnabled|proxyHost|proxyPort|proxyUser|proxyPassword` and export them
  before calling geobr. Without this, every `read_*()` inside QGIS times out on an institutional
  network — which is precisely this maintainer's situation (`cache.ipea.gov.br:3128`).

### `plugin.py` — lifecycle discipline (per `qgis-syntax-plugins`)

- every GUI object created in `initGui()` is stored on `self` and removed in `unload()`
- `unload()` calls `processingRegistry().removeProvider(self.provider)` and removes the message-bar
  widget and any action
- `QAction`s get `setObjectName()` and `iface.mainWindow()` as parent
- **nothing in `processAlgorithm` touches `iface` or `QgsProject`** — it runs on a worker thread

---

## 5. Verification (executable here, not hypothetical)

1. `pip install --user duckdb rapidfuzz` into QGIS's user-site (additive; does not touch Program Files).
2. Import smoke test under `python-qgis.bat`: `import geobr`, then introspect all 30 readers and
   assert every parameter maps to a QGIS parameter type (catches a signature the mapper misses).
3. Deploy the plugin folder to
   `%APPDATA%\Roaming\QGIS\QGIS3\profiles\default\python\plugins\geobr`.
4. `qgis_process-qgis.bat plugins` → `geobr` listed; `qgis_process-qgis.bat list` → the geobr
   provider with its algorithms.
5. `qgis_process-qgis.bat run geobr:read_state -- YEAR=2020 OUTPUT=...gpkg` → assert 27 features,
   EPSG:4674. **Requires network + proxy.**
6. `ogrinfo` the output to confirm geometry and CRS.

Failures are reported with real output. Anything not run is reported as SKIPPED with the reason.

---

## 6. Explicit non-goals for v1

- No `lookup_muni` / `list_geobr` algorithms (they return tables, not layers) — v2.
- No bundled QML styles.
- No vendoring of geobr into the plugin; it is a declared dependency installed with pip.
- No publication to plugins.qgis.org in this change.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| User declines the pip install → plugin is inert | Provider loads with zero algorithms and a clear message-bar prompt; never raises at startup |
| A future geobr reader has a parameter the mapper can't type | Falls back to `QgsProcessingParameterString`; smoke test in §5.2 catches it at dev time |
| Long download blocks with no cancel | geobr's download is one blocking call; `feedback` reports stages but cannot interrupt mid-request. Documented, not hidden. |
| `gdf.to_file` fails on an exotic dtype | Coerce unsupported object columns to `str` before write, only if observed |

---

## 8. Reconciliation with the adversarial review (v2 — this is what gets built)

The adversary agreed the architecture is right (Processing provider + one signature-driven
algorithm + geopandas writes the file) and attacked the packaging, the file count, and correctness.
Accepted in full except where noted.

### 8.1 Accepted — correctness fixes

| # | Fix | Verified how |
|---|---|---|
| 1 | **Plugin folder must be `geobr_qgis`, not `geobr`.** QGIS prepends the plugins dir to `sys.path` and imports the folder as a top-level module, so a folder named `geobr` would shadow the library. Provider `id()` stays `"geobr"`, so `qgis_process run geobr:read_state` is unaffected. | reasoning; deterministic |
| 2 | `createInstance()` must return `GeobrAlgorithm(self._spec)` — the default would yield an unparameterised instance | Processing API contract |
| 3 | Derive the OGR driver from the destination extension, not a hardcoded `"GPKG"` | measured: `QgsVectorFileWriter.driverForExtension` → gpkg/shp/geojson/parquet all resolve |
| 4 | Validate `code_*` (`all` / 2 letters / digits), split on commas, guard the zero-row case, and report the feature count — geobr returns the **unfiltered** relation on an unmatched code | confirmed in `_duckdb_backend.py:476-522` and CLAUDE.md |
| 6 | Gate every forced kwarg on `k in signature` — `read_comparable_areas` has no `output`/`cache`/`show_progress` and would raise `TypeError` | confirmed by signature survey |
| 7 | **Skip `macro`.** `parameterAsString` returns `""` for an unset optional; `read_health_region` tests `if macro is not None`, so `""` silently overrides the user's `geometry_level` | confirmed by reading `read_health_region.py:34-40` |
| 8 | `threading.Lock` around the reader call — geobr's DuckDB connection is a process-global registering views by name | confirmed `_duckdb_backend.py:11` |
| 10 | `shortHelpString()` from the reader docstring | free |

### 8.2 Accepted — cuts

`plugin.py`, `catalog.py`, `deps.py` merge away (7 Python files → 3). The `GROUPS` dict, the
`cache` parameter, the guided pip-install button, and the dev-mode `sys.path` hook are all cut.
The `cache` cut is the interesting one: `download_metadata_v2()` returns the cached metadata
parquet unconditionally and takes no `cache` argument, so `cache=False` does **not** refresh the
year list — the exact thing a user toggling it would be trying to fix. A knob that doesn't do what
its name says, replicated across 30 algorithms, is worse than no knob. The README documents
clearing `~/.cache/geobr` instead.

### 8.3 Overridden — startup cost is CRITICAL, not LOW

The adversary rated "importing geobr at startup" as LOW and asked only that it be measured.
**Measured, it is disqualifying:**

```
import geobr — warm: 3.9s (pandas 2.42 + geopandas 0.80 + requests 0.55 + duckdb 0.08)
             — cold: 28.6s observed once on this machine
geobr itself:  0.04s — the cost is entirely its dependency stack
```

Imposing 4–29 s on every QGIS launch, for every installed user, whether or not they ever run a
geobr algorithm, is not shippable. But `loadAlgorithms()` needs signatures at startup.

**Resolution — read the signatures without importing the package.**
`importlib.util.find_spec("geobr")` *locates* the package without executing it; `ast.parse` then
extracts `__all__` and each reader's arguments and docstring from source.

```
find_spec (no import):          0.001s   — pandas NOT imported afterwards
ast signature extraction:       0.458s   — 31 readers, 0 failures
```

Two orders of magnitude cheaper, and it **keeps** the anti-drift property: signatures still come
from geobr's source, never from a table in the plugin. The real `import geobr` moves into
`processAlgorithm`, where the user is already waiting on a download and the cost is paid once per
session, on a worker thread, behind a progress message.

### 8.4 Overridden — the DuckDB spatial probe moves from startup to the error path

The adversary's BUG 5 is real (`convert_output` needs `ST_AsWKB`, and `_setup_connection`
swallows a failed `INSTALL spatial`), but probing it at startup with `LOAD spatial` measured
**3.46 s** and can trigger DuckDB's auto-install — i.e. a network call during QGIS launch. Instead
the algorithm catches the failure and rewrites the cryptic `st_aswkb does not exist` into an
actionable message. Zero startup cost; the guidance appears exactly when it is needed.

### 8.5 Kept deliberately, against a plausible objection

- **`read_comparable_areas` ships.** It is the one reader on the legacy gpkg path, whose
  `url_solver()` calls `requests.get()` with **no timeout** (`utils.py:41`) — a real hang risk on a
  proxied network. Dropping a public dataset is the bigger loss; the risk is documented in the
  README and the reader is verified live in §5.
- **Codes stay `float`.** `constants.py` `DataTypes` types `code_muni`/`code_state` as `"float"`
  *deliberately*, so they land in GeoPackage as `Real` (`3304557.0`). Silently re-typing them in the
  plugin would be the plugin diverging from geobr — precisely what §1 refuses to do. Documented as
  a known artifact instead.

### 8.6 Final file list

```
qgis-plugin/geobr_qgis/
├── __init__.py    classFactory + GeobrPlugin (initGui/unload) + dependency probe
├── provider.py    GeobrProvider + AST-based reader discovery (no geobr import)
├── algorithm.py   GeobrAlgorithm — parameter mapping, validation, proxy, write
├── metadata.txt   hasProcessingProvider=yes
├── icon.svg · LICENSE · README.md
```

---

## 9. Verification results (executed, QGIS 3.42.1)

| Check | Result |
|---|---|
| Deps installed into QGIS user-site | `duckdb 1.5.5`, `rapidfuzz 3.14.6`; then `pip install -e python-package` added `geobr 1.0.0` + `html5lib`, `webencodings`. **No shadowing** of QGIS's geopandas/shapely/pyarrow, as predicted. |
| Discovery cost | `discover_readers()` → **31 readers in 0.018 s**, with `geobr` and `pandas` confirmed *not* in `sys.modules`. The startup-cost fix works. |
| Provider registration | `qgis_process list` → all **31** algorithms under `geobr:` |
| Generated UI | `qgis_process help geobr:read_state` shows `YEAR` (number), `CODE_STATE` (string, default `all`), `SIMPLIFIED` (boolean) and the reader's docstring as help |
| `read_state YEAR=2020 CODE_STATE=RJ` | 1 feature, MultiPolygon, EPSG:4674, correct fields |
| `read_municipality YEAR=2020 CODE_MUNI=33` | **92 features** — matches the documented ground truth for RJ |
| `read_biomes YEAR=2019` | 7 features |
| `read_country YEAR=2020` | 1 feature, EPSG:4674 |
| Code validation | `CODE_STATE=@@bad` rejected with the intended actionable message, before any download |
| `initProcessing()` | **Bug found and fixed during verification** — QGIS calls `initProcessing()`, not `initGui()`, in headless mode; without it the plugin failed to start under `qgis_process`. `iface` is `None` there, so the message-bar call is now guarded. |

### 9.1 Two defects found that are *not* in the plugin

1. **`duckdb` crashes `qgis_process` at interpreter finalization.**
   `Fatal Python error: PyEval_SaveThread ... the GIL is released`, exit `0xC0000409`, *after* the
   output is written correctly. Isolated by bisecting the import inside a real run: `os`, `numpy`,
   `pandas`, `pyarrow`, `rapidfuzz`, `pyogrio`, `geopandas` all exit cleanly (code 1, the expected
   validation error); `duckdb` and `geobr` both reproduce the crash. An embedded `QgsApplication`
   with `initQgis()`/`exitQgis()` does *not* crash, so it is specific to `qgis_process` teardown.
   **Desktop-QGIS shutdown behaviour is unverified** — the GUI test had to be killed, and its `-1`
   exit code is the kill, not a crash. Documented in the README; not worked around, because the
   alternative (running geobr in a subprocess) trades a cosmetic exit-code problem for real
   fragility in locating a Python interpreter cross-platform.

2. **`read_health_region` ignores `geometry_level`** — a geobr bug, reproduced outside QGIS.
   For RJ in 2013 it returns 92 features at `municipality`, `micro` *and* `macro`, although the data
   contains 9 distinct `code_health_region` and 1 `code_health_macroregion`. Cause: the aggregation
   in `read_health_region.py` groups by every column it does not explicitly exclude, and
   `code_muni6` (92 distinct values) is not in either exclusion list, so the `GROUP BY` never
   collapses. Left unfixed here — it is a geobr change with an R-parity question attached.

---

## 10. Port to QGIS 4.2.1 (2026-09-02)

The maintainer upgraded to the latest stable QGIS, so the plugin was retargeted. **No Python code
changed.** Two packaging facts did the damage, and both fail silently:

| Problem | Symptom | Fix |
|---|---|---|
| `metadata.txt` had no `qgisMaximumVersion` | QGIS assumes `<major>.99`, so a `qgisMinimumVersion=3.22` plugin is treated as incompatible with QGIS 4 — it never appears in `qgis_process plugins` at all, with no error | `qgisMaximumVersion=4.99` |
| QGIS 4 uses a **new profile root** | `%APPDATA%\QGIS\QGIS4\...`, not `QGIS3\...`; the QGIS 3 deployment is invisible to QGIS 4 | deploy to both roots |

### Environment comparison

| | QGIS 3.42.1 | QGIS 4.2.1 "Belem do Para" |
|---|---|---|
| Python | 3.12.9 | 3.12.13 |
| Qt / PyQt | 5 | **6.11.0 / 6.11.0** |
| geopandas / shapely / pandas | 1.0.1 / 2.0.6 / 2.2.2 | **1.1.4 / 2.1.2 / 3.0.3** |

The Qt5 to Qt6 move cost nothing because the plugin uses the `qgis.PyQt` shim and QGIS enums, never
Qt5-specific APIs. `QgsProcessingParameterNumber.Integer` still resolves under QGIS 4.

### Results - identical across both versions

`read_state YEAR=2020 CODE_STATE=RJ` -> 1 feature · `read_municipality CODE_MUNI=33` -> 92 ·
`read_biomes YEAR=2019` -> 7 · all EPSG:4674 · 31 algorithms registered.

### New risk

QGIS 4.2.1 ships **geopandas 1.1.4 and shapely 2.1.2, both above geobr's declared upper bounds**
(`<=1.1.2`, `<=2.1.0`), plus pandas 3.0.3. It works today, but this is outside geobr's supported
matrix — the pins exist because the geo stack breaks on minor releases
(`python-package-conventions.md` §2). Worth deciding on the geobr side whether to widen them.

### Not fixed

The duckdb finalization crash reproduces identically on QGIS 4.2.1, confirming it tracks duckdb
rather than the QGIS version.

---

## 11. GUI verification (2026-09-02) — CLOSED

Headless testing could not be extended to the desktop app on this machine. Three delivery
mechanisms failed, and the reasons are worth recording:

| Attempt | Outcome |
|---|---|
| `qgis-bin.exe --code script.py` | never ran — launching the binary directly skips `qgis.bat`'s `o4w_env.bat` / `qt6_env.bat` setup, so `QGIS_PREFIX_PATH`, `QT_PLUGIN_PATH` and PATH are unset and Python never initialises |
| relaunch via `qgis.bat` (correct environment) | GUI opened fully and responsive ("Untitled Project — QGIS"), no modal dialog, but `startup.py` still never executed |
| minimal dependency-free `startup.py` probe | did not fire in 100 s — **QGIS 4.2.1 does not execute `<profile>/python/startup.py`** |

The GUI was confirmed to be using the targeted profile (`QGIS4.ini` written during the run) with
`geobr_qgis=true` in `[PythonPlugins]`, so the plugin was configured to load; only observation was
impossible. All test artifacts were removed from the user profile afterwards.

**Verified manually by the maintainer on QGIS 4.2.1: everything runs smoothly.** That covers the
surface automation could not reach — the Processing Toolbox entries, the Qt6 parameter dialog, the
result layer loading into the project, and a clean application shutdown.

The shutdown result is the significant one: it confirms the duckdb finalization crash is specific to
`qgis_process` teardown and **does not affect the desktop app**. The README previously recorded that
as unverified and has been corrected.

### Status: the plugin is verified end-to-end

Headless on QGIS 3.42.1 and 4.2.1 (31 algorithms; `read_municipality CODE_MUNI=33` → 92;
EPSG:4674), and interactively in the QGIS 4.2.1 GUI. Remaining known issues are the two upstream
defects in §9.1 — the duckdb/`qgis_process` teardown crash and geobr's `read_health_region`
`geometry_level` bug — neither of which is in the plugin.
