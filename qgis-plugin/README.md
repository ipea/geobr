# geobr for QGIS


geobr is a computational package to download official spatial data sets
of Brazil. The package covers a wide range of spatial data sets,
available at various geographic scales and for various years with
harmonized attributes, projection and fixed topology. This QGIS plugin 
exposes the [geobr](https://github.com/ipea/geobr) Python package as
Processing algorithms. geobr's readers — states, municipalities, census tracts, biomes,
indigenous lands, health facilities, schools, favelas, polling places — become algorithms in the Processing Toolbox.

Because they are Processing algorithms rather than a custom dialog, they work in **batch mode**, in
**Model Builder**, and from the **`qgis_process`** command line, and they run on a background
thread with a progress bar.

```bash
qgis_process run geobr:read_state -- YEAR=2020 CODE_STATE=RJ OUTPUT=/tmp/rj.gpkg
```

## Install

**1 — the plugin.** Install *geobr* from *Plugins → Manage and Install Plugins*, or copy
`geobr_qgis/` into your QGIS profile plugins directory (table below) and enable it there.

The plugin declares [qpip](https://github.com/opengisch/qpip) as a **plugin dependency**, so the
Plugin Manager offers to install it too. Accept: qpip reads this plugin's `requirements.txt` and
installs **duckdb**, the engine geobr runs on, into your QGIS profile
(`python/dependencies/<python version>`) the first time the plugin loads. This is the same
mechanism QDuckDB uses, so the two plugins share one duckdb. If you install by copying files, add
qpip from the Plugin Manager yourself, or put duckdb in the pip command of step 2.

**2 — the Python package.** The plugin does not vendor geobr; it calls the real one. It requires
**geobr 2.0.1 or newer**.

```bash
python -m pip install --user "geobr>=2.0.1"
```

Run this with *QGIS's* Python, not a system Python. On Windows that is
`"C:\Program Files\QGIS 3.xx\bin\python-qgis.bat" -m pip install --user "geobr>=2.0.1"`.

2.0.1 is a hard floor, not a preference: earlier releases pinned `geopandas<=1.1.2` and
`shapely<=2.1.0`, which QGIS 4.2.1 exceeds, so pip satisfied those ceilings by downgrading
QGIS's own copies (see *Known rough edges*).

QGIS already ships geopandas, shapely, pyarrow, pandas and requests, so in practice pip adds geobr
itself (plus the small `rapidfuzz` wheel on geobr 2.0.1; later releases drop it). pip cannot see
the duckdb that qpip installed, since qpip's directory is not a site-packages, so it installs a
second copy under `--user`. That is harmless: both are the same wheel, and qpip's copy sits first
on `sys.path` in the desktop app and, through the plugin's own fallback, in `qgis_process` too.
Without qpip, that pip copy is simply the one that gets used.

**QGIS 4 uses a different profile root than QGIS 3** (`QGIS4` instead of `QGIS3`), and nothing
carries over between them — a plugin installed for QGIS 3 is invisible to QGIS 4. Replace
`<ROOT>` below with `QGIS3` or `QGIS4` to match the version you are installing into.

| Platform | Plugins directory |
|---|---|
| Windows | `%APPDATA%\QGIS\<ROOT>\profiles\default\python\plugins` |
| Linux | `~/.local/share/QGIS/<ROOT>/profiles/default/python/plugins` |
| macOS | `~/Library/Application Support/QGIS/<ROOT>/profiles/default/python/plugins` |

Requires **QGIS 3.40+**. Verified on **QGIS 3.42.1** (Qt5, Python 3.12.9) and **QGIS 4.2.1** (Qt6,
Python 3.12.13) with identical results. The plugin needed no code changes for Qt6 — it uses the
`qgis.PyQt` compatibility layer and QGIS enums rather than Qt5-specific APIs.

The 3.40 floor is set by the dependency, not by the plugin: geobr requires Python 3.10 or newer, and
QGIS builds older than 3.40 ship Python 3.9, where `pip install geobr` simply refuses. Declaring an
earlier minimum would advertise a version on which the plugin can never work.

Note that `metadata.txt` also sets `qgisMaximumVersion=4.99`. Without an explicit maximum, QGIS
assumes `<major>.99`, so a plugin declaring a 3.x minimum is silently treated as incompatible with
QGIS 4 and never even appears in the plugin list.

## How it works

The plugin is a thin wrapper. It calls geobr's public `read_*()` functions and nothing else — no
private API, and no second implementation of geobr's release-sniffing and download logic. That
keeps it from drifting away from the R and Python packages.

Algorithm parameters are generated from each reader's **own signature**, read out of geobr's source
with `ast` at startup. Adding a reader to geobr makes it appear in QGIS with no change to this
plugin. Reading the source rather than importing the package keeps QGIS startup fast: `import geobr`
costs ~4 s warm and up to ~29 s cold because of pandas/geopandas/duckdb, so the real import is
deferred until you actually run an algorithm.

The year field is a drop-down of the years that data set offers, newest first and preselected,
according to geobr itself. The years a data set offers exist nowhere but in the data release, which
geobr lists at run time with `download_metadata_v2()`, so the plugin asks it. This is the one place
the plugin touches geobr outside a run, and it is kept off the startup path: the first time a geobr
dialog is opened in a session, the plugin imports geobr and fetches the listing (the same one the
run needs, so nothing is fetched twice); later dialogs reuse it. The drop-down's values are the
years themselves, not positions in the list, so `YEAR=2020` on the command line and in a saved
model keeps meaning 2020 as the list grows. If geobr is missing or the fetch fails, the field falls
back to a plain number box that opens empty and marked optional, a warning is logged, and the run
itself reports the real error.

The algorithm window is QGIS's own, handed back through `createCustomParametersWidget()` with one
change: it opens at least 700 px wide (or 90% of the screen). QGIS reopens the window at the size
it last had, and Processing's default is barely 500 px, half of it help panel. The floor applies
only while the window opens; after that it resizes freely, and QGIS remembers the size as it does
for any other algorithm. If that Processing internal ever moves, the plugin logs a warning and lets
Processing build the window itself, so only the opening width is lost.

Help text comes from the same place. Since 2.0.0, geobr writes `{year}`-style tokens in its reader
docstrings and substitutes them from a shared table when the package is imported — so reading the
source alone would show the tokens. `discovery.py` reproduces that substitution, and a test
(`tests/test_discovery.py`) fails if a future geobr changes it. That test suite runs in CI against
geobr's source in this repo, so a signature or docstring change upstream breaks the plugin's build
rather than a user's help panel.

## Layer names

A layer arrives in the legend named after the data it holds, not after the algorithm:
`municipalities_2020`, `states_2020`, `healthfacilities_202504`. The geography is the one geobr's
own metadata uses, so the name matches the release asset (`municipalities_2020.parquet`) and the
DuckDB view a geobr SQL query would address (`FROM municipalities_2020`).

Arguments that select a *different geometry* rather than a subset of one are part of the name, so
two such layers never collide: `censustracts_2000_urban` and `censustracts_2000_rural`, and
`healthregions_2013_municipality` / `_micro` / `_macro`.

This applies to the default *Create temporary layer* destination. If you type a filename, that
filename names the layer, as it does everywhere else in QGIS.

## Filtering by code

The `code_*` parameters accept what geobr accepts, and several values separated by commas:

| Value | Meaning |
|---|---|
| `all` | everything (default) |
| `RJ` | a two-letter state abbreviation |
| `33` | a two-digit state code |
| `3304557` | a seven-digit municipality code |
| `33,35` | several of the above |

Malformed values are rejected before the call, and so are **mixed lists** like `RJ,33`. Both matter,
because geobr fails quietly here rather than loudly: when it cannot match a code to a column it
returns the data **unfiltered** rather than raising, so a typo would otherwise give you a
whole-country layer where you asked for one state. And it picks the column from the *first* value
alone, then applies the rest to that same column — so `RJ,33` would silently return just RJ.

The check is a shape check, not a validity check: `ZZ` is a well-formed abbreviation and is passed
through, returning zero features rather than being rejected up front. The algorithm reports the
feature count in the log, so an unexpected result is visible either way.

## Known limitations

- **`qgis_process` exits with a crash code after a geobr run.** Importing `duckdb` into QGIS's
  embedded interpreter makes `qgis_process` die during Python finalization
  (`Fatal Python error: PyEval_SaveThread ... the GIL is released`, exit `0xC0000409`). This is an
  upstream `duckdb`/embedded-CPython interaction, not a fault in the algorithm: it happens *after*
  the layer is written, and the output file is complete and correct. Isolated by bisection — every
  other dependency (pandas, geopandas, pyarrow, pyogrio, numpy) finalizes cleanly, and
  `duckdb` alone reproduces it. If you script geobr in CI, check for the output file rather than
  trusting the exit code. Reproduced identically on QGIS 3.42.1 and 4.2.1, so it tracks duckdb
  rather than the QGIS version. **The QGIS desktop app is unaffected** — running geobr algorithms
  from the Processing Toolbox and then quitting QGIS 4.2.1 was confirmed clean by the maintainer,
  so this is a `qgis_process` teardown problem only.
- **QGIS ships a geo stack newer than geobr once declared** — QGIS 4.2.1 has geopandas 1.1.4,
  shapely 2.1.2 and pandas 3.0.3. Two separate problems came out of that, both fixed upstream.

  *The version bounds.* geobr ≤ 2.0.0 pinned `geopandas<=1.1.2` and `shapely<=2.1.0` — exact
  ceilings left by a Dependabot bump, not a compatibility finding. Because a user's
  site-packages precedes QGIS's own on `sys.path`, `pip install geobr` met those ceilings by
  installing older geopandas and shapely *over* QGIS's bundled copies, for QGIS itself and
  every other plugin; shapely is a compiled GEOS binding, so that was not a harmless
  downgrade. geobr 2.0.1 relaxed them to `geopandas>=1.0.0,<2` and `shapely>=1.7.0,<3`, and
  against QGIS 4.2.1 all nine of geobr's requirements are now already satisfied, so pip adds
  geobr alone. This is why the plugin requires **geobr ≥ 2.0.1**.

  *The pandas 3 kernel.* pandas 3 makes strings Arrow-backed, so geobr's regex
  `str.contains()` dispatched to
  `pyarrow.compute.match_substring_regex`, a kernel absent from QGIS's RE2-less pyarrow, and
  **every reader failed** with `AttributeError`. It surfaced only when the metadata cache had to be
  rebuilt, so a pre-existing `~/.cache/geobr` hid it. Fixed upstream in geobr by matching those
  literal strings with `regex=False`; verified on QGIS 4.2.1 and 3.42.1 from a cold cache.
  geobr is not otherwise pandas-3 audited, so treat further pandas-3 breakage as possible.
- **`zone` only applies to census tracts from 2007 and earlier.** Before 2010, urban and rural
  tracts were separate data sets; from 2010 on they are one, and geobr ignores the argument
  (`geobr/read_census_tract.py`). The control is still offered because it is real for the older
  years, but it does nothing for 2010 and 2022.
- **Codes are floating-point.** geobr deliberately types `code_muni`, `code_state` and friends as
  float (`geobr/constants.py`), so they arrive in GeoPackage as `Real` — `3304557.0`, not
  `3304557`. The plugin does not re-type them, because silently disagreeing with geobr's own output
  is worse than the cosmetic wart. Cast them in the field calculator if you need an integer join key.
- **Downloads cannot be cancelled mid-request.** geobr fetches in one blocking call, so *Cancel*
  takes effect between stages, not during a transfer.
- **`read_comparable_areas` is not exposed.** It is the only reader still on geobr's legacy gpkg
  download path, whose `url_solver()` calls `requests.get()` with **no timeout**. A Processing
  algorithm cannot be cancelled mid-request, so on a network that black-holes connections that call
  would hang until QGIS is restarted. It is excluded in `discovery.py` (`_EXCLUDED_READERS`) and
  returns once geobr fixes it. Every other reader uses the current parquet path.
- **qpip does not run under `qgis_process`.** It needs the GUI, so headless QGIS never puts
  `python/dependencies/<python version>` on `sys.path`. The plugin does it itself at load time
  (`add_qpip_path()` in `__init__.py`), inserting at the front exactly as qpip does, so a
  qpip-installed duckdb resolves identically in both. If qpip changes its layout, the fallback
  finds nothing and a run reports duckdb as missing, with the by-hand pip command.
- **Only self-contained wheels can go through qpip.** qpip installs with `pip --target`, which
  makes pip ignore every package already installed and reinstall all dependencies into the profile
  directory — at the front of `sys.path`. Listing geobr there would shadow QGIS's own geopandas,
  shapely, pandas, numpy and pyarrow with PyPI wheels, the same failure described above for
  geobr ≤ 2.0.0. So `requirements.txt` carries duckdb alone, and geobr stays a pip install.
- **Downloads are cached per session.** geobr 2.0.0 stores downloads and metadata in a fresh temp
  directory that it deletes when the Python process exits — the same behavior as the R package.
  Source updates are picked up on the next QGIS start, with no action needed. Within one session
  repeated reads are served from that session cache, but restarting QGIS re-downloads whatever the
  session uses, and a single year of census tracts exceeds 350 MB. The plugin does not expose
  geobr's `cache` argument, because `cache=False` does not refresh the *metadata* — the thing that
  actually goes stale.

- **Shapefile output truncates field names** to 10 characters. Prefer GeoPackage.

## Proxies

geobr downloads with `requests`, which reads `http_proxy`/`https_proxy` from the environment and
does not know about QGIS's network settings. The plugin bridges them: whatever you configure in
*Settings → Options → Network* is passed to geobr at run time.

If a read fails with a missing `st_aswkb` SQL function, DuckDB's `spatial` extension could not be
downloaded. Install it once from a working connection:

```bash
python -c "import duckdb; duckdb.connect().execute('INSTALL spatial')"
```

## Layout

```
geobr_qgis/
├── __init__.py       classFactory, plugin lifecycle, dependency probe, qpip path fallback
├── discovery.py      reader discovery (ast), docstring rendering, layer naming — imports no qgis
├── provider.py       the Processing provider
├── algorithm.py      the one algorithm class that serves every reader
├── requirements.txt  what qpip installs: duckdb only
└── metadata.txt      declares plugin_dependencies=qpip
tests/
├── conftest.py
├── test_discovery.py   runs without QGIS, against python-package/geobr
└── test_packaging.py   requirements.txt ↔ pyproject duckdb floor, metadata invariants
```

`discovery.py` is deliberately free of any `qgis` import: it is the only part of the plugin coupled
to geobr's *source shape*, so it is the part most likely to break when geobr changes, and it has to
be testable without a QGIS runtime. `.github/workflows/qgis-plugin-check.yaml` runs those tests on
any change to `qgis-plugin/**` **or `python-package/geobr/**`.

## License

MIT, same as geobr.
