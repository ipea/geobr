── R CMD check results ──────────────────────────────────────────────────────────────────────────────────────────────────── geobr 2.1.0 ────
Duration: 19m 17.1s

0 errors ✔ | 0 warnings ✔ | 0 notes ✔

Removed non-standard files/directories found at top level

obs. all urls work fine on the browser.

# geobr v2.1.0

**New features**

- New function `read_addresses()`, which reads the geolocated addresses of the
  National Registry of Addresses for Statistical Purposes (CNEFE), organized by
  IBGE. Like `read_statistical_grid()` and `read_census_tract()`, its
  `code_muni` argument is required and has no default, because the data covers
  roughly 111 million addresses. Closes [367](https://github.com/ipea/geobr/issues/367).

**Minor changes**

- Updated suggests to use geoarrow (>= 0.4.4),
- Fixed the documentation of `code_muni` in `read_statistical_grid()`. It was
  pulled from the shared roxygen template, which states that `code_muni = "all"`
  is the default. In this function `code_muni` is required and has no default,
  deliberately, because loading the grid for the whole country is slow and may
  exhaust memory.
- `read_census_tract()` now documents that `code_tract` is required and has no
  default, for the same reason. These two functions are the only readers that
  do not default to downloading the whole country.
- Requires duckdb (>= 1.5.1)

**Bug fixes**

- geobr now fallsback to ipea servers whenever users cannot access github servers. Closes [447](https://github.com/ipea/geobr/issues/447)
- `lookup_muni()`: fixed a SQL error when the fuzzy name match received a name with an apostrophe (e.g. "Santa Barbara d'Oest"). The fuzzy match now returns all candidate matches instead of recycling silently, and closes its DuckDB connection. Dropped the `glue` dependency.
- `cep_to_state()`: fixed the Minas Gerais CEP range, which was reversed so every MG CEP raised "CEP not found".
- `read_country()`, `read_region()`, `read_pop_arrangements()` and `read_urban_concentrations()` now return `NULL` when the metadata download fails, like the other readers, instead of erroring.
- `read_health_region()` now honours `output = "duckdb"` when `geometry_level` is `"micro"` or `"macro"`. These levels aggregate geometries in memory, and the result was returned as an `sf` whatever `output` asked for.
- `read_capitals()` now passes `cache` and `verbose` on to `read_municipal_seat()`. Both arguments were documented but ignored, so `cache = FALSE` had no effect and `verbose = FALSE` still printed a message.
- `list_geobr()` listed two functions that do not exist (`read_favelas`, `read_quilombola_lands`) and omitted `read_capitals`. The catalogue now matches the exported readers exactly. It also returns `NULL` when the metadata download fails, and rejects a non-scalar `wide` instead of silently returning long format.

