# geobr for QGIS

A QGIS plugin that exposes the [geobr](https://github.com/ipea/geobr) Python package as
Processing algorithms. Every geobr reader — states, municipalities, census tracts, biomes,
indigenous lands, health facilities, schools, favelas, polling places — becomes an algorithm in the
Processing Toolbox.

Because they are Processing algorithms rather than a custom dialog, they work in **batch mode**, in
**Model Builder**, and from the **`qgis_process`** command line, and they run on a background
thread with a progress bar.

```bash
qgis_process run geobr:read_state -- YEAR=2020 CODE_STATE=RJ OUTPUT=/tmp/rj.gpkg
```

## Install

**1 — the Python package.** The plugin does not vendor geobr; it calls the real one.

```bash
python -m pip install --user geobr
```

Run this with *QGIS's* Python, not a system Python. On Windows that is
`"C:\Program Files\QGIS 3.xx\bin\python-qgis.bat" -m pip install --user geobr`.

QGIS already ships geopandas, shapely, pyarrow, pandas and requests, so in practice pip only adds
`duckdb` and `rapidfuzz` (both are hard requirements — geobr imports them at module scope, so
`import geobr` fails outright without them).

**2 — the plugin.** Copy `geobr_qgis/` into your QGIS profile plugins directory and enable *geobr*
in *Plugins → Manage and Install Plugins*.

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

## Filtering by code

The `code_*` parameters accept what geobr accepts, and several values separated by commas:

| Value | Meaning |
|---|---|
| `all` | everything (default) |
| `RJ` | a two-letter state abbreviation |
| `33` | a two-digit state code |
| `3304557` | a seven-digit municipality code |
| `33,35` | several of the above |

Anything else is rejected before the call. This matters: when geobr cannot match a code to a
column it returns the data **unfiltered** rather than raising, so a typo would otherwise give you a
whole-country layer where you asked for one state. The algorithm also reports the feature count in
the log, so an unexpected fallthrough is visible.

## Known limitations

- **`qgis_process` exits with a crash code after a geobr run.** Importing `duckdb` into QGIS's
  embedded interpreter makes `qgis_process` die during Python finalization
  (`Fatal Python error: PyEval_SaveThread ... the GIL is released`, exit `0xC0000409`). This is an
  upstream `duckdb`/embedded-CPython interaction, not a fault in the algorithm: it happens *after*
  the layer is written, and the output file is complete and correct. Isolated by bisection — every
  other dependency (pandas, geopandas, pyarrow, pyogrio, rapidfuzz, numpy) finalizes cleanly, and
  `duckdb` alone reproduces it. If you script geobr in CI, check for the output file rather than
  trusting the exit code. Reproduced identically on QGIS 3.42.1 and 4.2.1, so it tracks duckdb
  rather than the QGIS version. **The QGIS desktop app is unaffected** — running geobr algorithms
  from the Processing Toolbox and then quitting QGIS 4.2.1 was confirmed clean by the maintainer,
  so this is a `qgis_process` teardown problem only.
- **QGIS 4.2.1 ships a geo stack outside geobr's declared bounds** — geopandas 1.1.4 (geobr pins
  `<=1.1.2`), shapely 2.1.2 (pins `<=2.1.0`) and pandas 3.0.3. In testing, `read_state`,
  `read_municipality` and `read_biomes` returned byte-identical feature counts to QGIS 3.42.1, so
  it works today, but geobr does not claim support for these versions and a future geopandas or
  pandas change could break it without warning.
- **`read_health_region` is offered at municipality level only.** geobr accepts a `geometry_level`
  argument but ignores it: the `micro`/`macro` aggregation groups by every column it does not
  explicitly exclude, and `code_muni6` survives that `GROUP BY`, so all three levels return one
  feature per municipality (92 for RJ, where the data holds 9 health regions and 1 macroregion).
  Rather than expose a control that silently does nothing, the plugin does not offer the parameter.
  The municipality-level output is correct. This is a bug in geobr itself
  (`geobr/read_health_region.py`), reproduced outside QGIS; the parameter returns once it is fixed.
- **Codes are floating-point.** geobr deliberately types `code_muni`, `code_state` and friends as
  float (`geobr/constants.py`), so they arrive in GeoPackage as `Real` — `3304557.0`, not
  `3304557`. The plugin does not re-type them, because silently disagreeing with geobr's own output
  is worse than the cosmetic wart. Cast them in the field calculator if you need an integer join key.
- **Downloads cannot be cancelled mid-request.** geobr fetches in one blocking call, so *Cancel*
  takes effect between stages, not during a transfer.
- **`read_comparable_areas` uses geobr's legacy download path**, whose HTTP call has no timeout. On
  a network that black-holes connections it can hang until QGIS is restarted. The other 30 readers
  use the current parquet path.
- **Stale cache.** geobr caches downloads in `~/.cache/geobr` with no expiry. If a dataset looks
  out of date, delete that directory. The plugin does not expose a `cache` toggle, because geobr's
  `cache=False` does not refresh the *metadata* — the thing that actually goes stale.
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
├── __init__.py    classFactory, plugin lifecycle, dependency probe
├── provider.py    reader discovery (ast) + the Processing provider
├── algorithm.py   the one algorithm class that serves every reader
└── metadata.txt
```

## License

MIT, same as geobr.
