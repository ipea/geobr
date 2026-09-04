# log history of geobr package development in Python

-------------------------------------------------------
# Development version

**Bug fixes**

- Fixed `query()` and `session().read()` failing on point layers. Both resolve
  a geography through `_load_geo_dataset()`, which defaulted to
  `simplified=True` for every geography. The data release ships no simplified
  asset for the five point layers (`healthfacilities`, `municipalseats`,
  `pollingplaces`, `schools`, `statsgrid`), so `select_metadata_v2()` raised
  `ValueError: No simplified data for ... in year ...`. Four of the five were
  masked by `read_geobr_hybrid()`, which retries with the flag toggled, but
  `pollingplaces` is `v2_only` and takes the `read_geobr_v2()` branch, so
  `geobr.query("SELECT * FROM pollingplaces_2022")` failed outright. These
  geographies now resolve to the original geometry directly; passing
  `simplified=True` explicitly warns and reads the original geometry instead of
  failing.

- Removed a duplicate, identical definition of `utils._simplified_attempts()`.

- `read_health_region(geometry_level="micro"|"macro")` no longer groups by
  `code_muni6`. That column is present in the 1991-2013 files, and including it
  in the `GROUP BY` split every health region back into its municipalities, so
  the union aggregation silently did nothing for those years. Columns to drop
  are now matched by prefix, as R already did.

- `read_pop_arrangements()`'s `year` parameter was annotated
  `InterruptedError` instead of `int`.

**Breaking changes**

- `read_municipal_seat()`, `read_schools()` and `read_health_facilities()` no
  longer accept a `simplified` argument. These return point geometries, which
  have nothing to simplify, and the R package has never exposed the argument
  for them. All three now pass `simplified=False` into the download pipeline,
  matching R and matching the two point readers that already did this
  (`read_polling_places()`, `read_statistical_grid()`). Calls that passed
  `simplified` explicitly will now raise `TypeError`; positional calls that
  relied on the old argument order will silently bind one argument earlier, so
  prefer keyword arguments. `read_health_facilities()` already defaulted to
  `simplified=False`, so its behavior is unchanged for default callers.

- `read_intermediate_region()`'s second argument was misspelled
  `code_intermadiate` and is now `code_intermediate`, matching the R package.
  Calls that passed the old name as a keyword will raise `TypeError`;
  positional calls are unaffected.

- `read_statistical_grid()` arguments are now ordered
  `year, code_muni, output, show_progress, cache, verbose`, matching the R
  package and the other four point readers. `verbose` was previously third.
  Only calls that passed `verbose` positionally are affected; keyword calls
  are unchanged.

- **All 31 `read_*()` functions now take their arguments in the same order as
  the R package**, which is the canonical
  `<year|date>, <code_*>, [extras], simplified, output, show_progress, cache,
  verbose`. Python previously used two orders: 10 readers already matched R,
  while 21 hoisted `verbose` ahead of `output`. Only positional calls that
  reached `verbose`, `output`, `show_progress` or `cache` are affected;
  keyword calls are unchanged. The affected readers are `read_amazon()`,
  `read_biomes()`, `read_capitals()`, `read_census_tract()`,
  `read_conservation_units()`, `read_country()`, `read_health_region()`,
  `read_immediate_region()`, `read_indigenous_land()`,
  `read_intermediate_region()`, `read_meso_region()`, `read_metro_area()`,
  `read_micro_region()`, `read_municipality()`, `read_pop_arrangements()`,
  `read_region()`, `read_semiarid()`, `read_state()`,
  `read_urban_concentrations()` and `read_weighting_area()`.
  `tests/test_reader_argument_order.py` pins the R order for every reader so
  this cannot drift again.

- `read_conservation_units()` no longer accepts `code_state`. The conservation
  unit data set has no `code_state` or `abbrev_state` column, so the argument
  could not filter anything: `read_filter_parquet_relation()` silently returns
  the unfiltered relation when no code column matches. R has never exposed it.

- `read_capitals()` takes `year` as its first argument rather than its last,
  matching the `read_<geography>(year, ...)` shape used by every other reader.
  The default is unchanged (2010). R gained the same argument, which it
  previously hardcoded.

- `read_census_tract()` now requires `code_tract`; it previously defaulted to
  `"all"`. Downloading every census tract in the country is slow and may
  exhaust memory, which is why R has always required it.
  `read_census_tract(year=2022)` now raises `TypeError`; pass
  `code_tract="all"` to keep the old behavior.

- `read_urban_area()` defaults to `simplified=True`, matching R and every other
  reader. It defaulted to `False`, so callers who did not pass the argument
  were downloading the full-resolution geometry.

- `read_comparable_areas()` accepts `show_progress` and `cache` for signature
  parity with R. As in R, both are currently unused: the gpkg download path for
  this data set is suspended.

**Documentation**

- Every `read_*()` function now documents all of its arguments in full. The
  shared options (`year`, `date`, `code_*`, `simplified`, `output`,
  `show_progress`, `cache`, `verbose`) were previously collapsed into an
  undescribed `"Standard geobr options."` line in 29 of the 31 readers, so
  their meaning was not available from `help()` or IDE hover. The text is
  ported from the roxygen templates in `r-package/man/roxygen/templates/`,
  adapted where the two packages genuinely differ (`output="gpd"` vs `"sf"`,
  `verbose=False` vs `TRUE`, `show_progress` vs `showProgress`).

- The descriptions live once in the new private module `geobr/_docstrings.py`
  and are interpolated into each reader by the `@docparams` decorator at
  import time, mirroring how roxygen `@template` works on the R side. A
  wording change now propagates to all readers at once.

- Fixed incorrect argument documentation found while porting:
  `read_municipal_seat()` and `read_urban_area()` documented a
  `code_weighting` argument they do not have (it is `code_muni`);
  `read_comparable_areas()` documented a non-existent `year` argument and
  omitted `start_year` / `end_year`, and its example was not runnable;
  `read_capitals()` described the default `output` as `"sf"` rather than
  `"gpd"`.

-------------------------------------------------------
# 1.0.1 version

**Bug fixes**

- Fixed `AttributeError: module 'pyarrow.compute' has no attribute
  'match_substring_regex'`, which made **every** `read_*()` function fail on
  pandas 3 when the installed pyarrow was built without RE2. Under pandas 3
  strings are Arrow-backed, so a regex `str.contains()` dispatches to a pyarrow
  kernel that such builds do not provide. Because the failure was in
  `download_metadata_v2()`, it only appeared when the metadata cache had to be
  rebuilt, so an existing `~/.cache/geobr` could mask it indefinitely. The
  affected calls all match literal strings and now pass `regex=False`
  (`utils.py`: `select_simplified()`, `download_metadata_v2()`, and the
  `zone` filter in `select_metadata_v2()` used by `read_census_tract()`).
  Found while running geobr inside QGIS 4.2.1, which ships pandas 3.0.3 and an
  RE2-less pyarrow.

- The download cache is now temporary, matching the behavior of the R
  package: parquet and metadata files are stored in a session-specific
  directory under the system temp folder and are removed when the Python
  process exits. Previously, files persisted in `~/.cache/geobr` across
  sessions, so data updated at the source was not picked up unless the user
  cleared the cache manually. Cache directories left behind in
  `~/.cache/geobr` by previous versions are no longer used and can be safely
  deleted.

-------------------------------------------------------
# 1.0.0

Update the python package to match the R 2.0.0 version. 

**New functions**

- `read_favela()` with data of favelas and urban communities (source: IBGE) .
- `read_polling_places()` with data of polling places (source: TSE).
- `read_quilombola_lands()` with data of officially recognized quilombola lands (source: INCRA).
- `remove_islands()` to remove islands from Brazil.

**Breaking changes**

- The `year` and `date` arguments can no longer be `NULL`; they must be explicitly 
specified. This change is intentional and is meant to encourage users to be more 
mindful of historical changes in the data.
- The `read_health_region()` has been completely rewritten to allow users return 
more detailed output if needed
- Functions like `read_schools()` and `read_health_facilities()` now use a 
combination of official spatial coordinates and coordinates found using the 
[{geocodebr}](https://github.com/ipea/geocodebr/) package to improve spatial 
accuracy. See documentation of these functions.
- The function `lookup_muni()` now has a `year` parameter. 
- The function and data `read_comparable_areas()` will be going under  major 
changes. For now, this function is temporarily suspended.
- The only year available so far for the functions `read_urban_concentrations()` 
and `read_pop_arrangements()`is 2010, and not 2015.

**Major changes**

- Data files are now saved in `.parquet`. This improved performance to download 
and to read files, and allow integration with ducdkDB and with Arrow. 
- Most functions have a new argument `output`, which allow users to choose the
output format. `"gpd"` returns an `GeoDataFrame` to memory (default),  `"duckdb"` returns a 
lazy spatial table backed by DuckDB, and `"arrow"` 
returns an Arrow dataset. Both `"duckdb"` and `"arrow"` support out-of-memory 
processing of large data sets.
- All functions have a new argument `verbose`. If `TRUE`, the 
function prints informative messages and shows download progress bar. If `FALSE` (the default),
the function is silent.
- The function `list_geobr()` now has a boolean argument `wide`, so users can 
choose whether the output should be presented in wide or long format.
- The function `lookup_muni()` now uses probabilistic match to find municipality
names that users might input with typos.
- The following functions now include the column `code_state` to allow users 
to filter the data directly in the function call: `read_indigenous_land()`,
`read_metro_area()`, `read_pop_arrangements()` and `read_urban_concentrations()`.
- The following functions now include the column `code_muni` to allow users 
to filter the data directly in the function call: `read_disaster_risk_area()`,
`read_health_facilities()`, `read_neighborhood`(), `read_statistical_grid()` and 
`read_schools()`.


**New co-author**

- Camila Brito


# 0.3.0 (unreleased)

Preparation to update the python package to match the R 2.0.0 version.

## Foundation (Phase 0)
* Core dependencies include `pyarrow`, `duckdb` and `rapidfuzz` (Arrow/DuckDB output and fuzzy `lookup_muni`)
* Parquet v2.0.0 download pipeline (`download_metadata_v2`, `download_parquet`, disk cache)
* Shared helpers: `_filter`, `_output`, `_cache`, `read_geobr_v2`, `read_geobr_hybrid`

### Phase 1 — Agent 1
* `read_capitals`, `read_favela`, `read_polling_places`, `read_quilombola_land`
* `cep_to_state`, `remove_islands`

### Phase 1 — Agent 2
* `code_muni` filtering: `read_schools`, `read_health_facilities`, `read_neighborhood`, `read_disaster_risk_area`, `read_statistical_grid`
* `keep_areas_operacionais` on `read_municipality`

### Phase 1 — Agent 3
* `code_state` filtering: `read_indigenous_land`, `read_metro_area`, `read_pop_arrangements`, `read_urban_concentrations`, `read_conservation_units`
* Default year 2010 for pop arrangements / urban concentrations

### Phase 1 — Agent 4
* `lookup_muni(year=...)`, fuzzy name match via rapidfuzz
* `list_geobr(wide=)` returns DataFrame
* `read_health_region(geometry_level=, code_state=)`

### Phase 1 — Agent 5
* `output="duckdb"` and `output="arrow"` via `convert_output`

-------------------------------------------------------

# 0.1.10
* Enforces correct data types to certain variables (issue #260)
* Changes package manager to poetry
* Fixes testing bugs

# 0.1.9
* Adds read_schools
* Adds read_comparable_areas
* Adds read_urban_concentrations
* Adds read_intermediate_region
* updates read_health_region
# v0.1.7

* Adds read_health_region.py

# v0.1.6

* Adds read_neighborhood.py

# v0.1.5 

* Expecting to Launch **geobr** v0.1 to pip with the following data sets:

 * list_geobr.py
 * lookup_muni.py
 * read_amazon.py
 * read_biomes.py
 * read_census_tract.py
 * read_conservation_units.py
 * read_country.py
 * read_disaster_risk_area.py
 * read_health_facilities.py
 * read_immediate_region.py
 * read_indigenous_land.py
 * read_meso_region.py
 * read_metro_area.py
 * read_micro_region.py
 * read_municipal_seat.py
 * read_municipality.py
 * read_region.py
 * read_semiarid.py
 * read_state.py
 * read_urban_area.py
 * read_weighting_area.py
 * utils.py


-------------------------------------------------------
