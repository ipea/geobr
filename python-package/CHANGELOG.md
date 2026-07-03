# log history of geobr package development in Python

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
