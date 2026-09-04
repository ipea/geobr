# geobr (development version)



**Bug fixes**

- Requires duckdb (>= 1.5.1)

**Documentation**

- Fixed the documentation of `code_muni` in `read_statistical_grid()`. It was
  pulled from the shared roxygen template, which states that `code_muni = "all"`
  is the default. In this function `code_muni` is required and has no default,
  deliberately, because loading the grid for the whole country is slow and may
  exhaust memory.

- `read_census_tract()` now documents that `code_tract` is required and has no
  default, for the same reason. These two functions are the only readers that
  do not default to downloading the whole country.


# geobr v2.0.1

**Bug fixes**

- Moves the {arrow} package from "Suggests" to "Imports".
- Fix bug in `read_immediate_region()` which was hardcoded to read state 11 by mistake. Closes [#436](https://github.com/ipea/geobr/issues/436).
- The function `remove_islands()` now correctly drops the arquipelago de Trindade e Martim Vaz
- Fix documentation of arguments `year` and `date`.
- Make the internal function that downloads geobr metadata more robust and removes the dependency from piggyback
- More informative message when a municipality does not have neighborhood data. Closes [#424](https://github.com/ipea/geobr/issues/424).


# geobr v2.0.0

**New functions**

- `read_favela()` with data of favelas and urban communities (source: IBGE) Closes [#387](https://github.com/ipea/geobr/issues/387).
- `read_polling_places()` with data of polling places (source: TSE) Closes [#184](https://github.com/ipea/geobr/issues/184) and [#242](https://github.com/ipea/geobr/issues/242).
- `read_quilombola_lands()` with data of officially recognized quilombola lands (source: INCRA) [Closes #242](https://github.com/ipea/geobr/issues/242).
- `remove_islands()` to remove islands from Brazil. Closes [#412](https://github.com/ipea/geobr/issues/412).

**Breaking changes**

- The `year` and `date` arguments can no longer be `NULL`; they must be explicitly 
specified. This change is intentional and is meant to encourage users to be more 
mindful of historical changes in the data.
- The `geom` column has been renamed to `geometry` for consistency
- The `read_health_region()` has been completely rewritten to allow users return 
more detailed output if needed
- Functions like `read_schools()` and `read_health_facilities()` now use a 
combination of official spatial coordinates and coordinates found using the 
[{geocodebr}](https://github.com/ipea/geocodebr/) package to improve spatial 
accuracy. See documentation of these functions.
- The function `lookup_muni()` now has a `year` parameter. Closes [#401](https://github.com/ipea/geobr/issues/401).
- The function and data `read_comparable_areas()` will be going under  major 
changes. For now, this function is temporarily suspended.
- The only year available so far for the functions `read_urban_concentrations()` 
and `read_pop_arrangements()`is 2010, and not 2015.

**Major changes**

- Data files are now saved in `.parquet`. This improved performance to download 
and to read files, and allow integration with ducdkDB via {duckspatial} and with
Arrow via {gearrow}. Closes [#290](https://github.com/ipea/geobr/issues/290)
- Most functions have a new argument `output`, which allow users to choose the
output format. `"sf"` returns an `sf` to memory (default),  `"duckdb"` returns a 
lazy spatial table backed by DuckDB via the duckspatial package, and `"arrow"` 
returns an Arrow dataset. Both `"duckdb"` and `"arrow"` support out-of-memory 
processing of large data sets.
- All functions have a new argument `verbose`. If `TRUE` (the default), the 
function prints informative messages and shows download progress bar. If `FALSE`,
the function is silent. Closes [#400](https://github.com/ipea/geobr/issues/400).
- The function `list_geobr()` now has a boolean argument `wide`, so users can 
choose whether the output should be presented in wide or long format.
- The function `lookup_muni()` now uses probabilistic match to find municipality
names that users might input with typos. Closes [#406](https://github.com/ipea/geobr/issues/406).
- The following functions now include the column `code_state` to allow users 
to filter the data directly in the function call: `read_indigenous_land()`,
`read_metro_area()`, `read_pop_arrangements()` and `read_urban_concentrations()`.
- The following functions now include the column `code_muni` to allow users 
to filter the data directly in the function call: `read_disaster_risk_area()`,
`read_health_facilities()`, `read_neighborhood`(), `read_statistical_grid()` and 
`read_schools()`.


**Minor changes**

- Several data fixes and data updates, addressing the following issues: 182, 247, 
249, 250, 267, 333, 340, 361, 369, 379, 384, 388, 389, 390, 391, 393, 404, 407.

**New co-author**

- Rogerio Barbosa

**New contributors**

- Cecilia do Lago
- Arthur Bazolli
- Filipe Cavalcanti
- Lucas Gelape
- Rafael Lopes
- Vinicius Oike

**New funding / institutional support**

- Instituto Todos pela Saúde (ITpS)



# geobr v1.9.1

**Minor changes**

- The `read_municipality()` has a new parameter `keep_areas_operacionais`, which allows users to control wether the data should keep the polygons of Lagoas dos Patos and Lagoa Mirim in the State of Rio Grande do Sul (considered as areas estaduais operacionais). The default `FALSE` drops these two polygons. Closes #176.
- Functions now include a `cache` parameter that allows users to decide whehter to keep files in cache or to force downloading them again. At the moment, files are only cached during the R session, but this is a step towards a future version of {geobr} when files  will be based on permanent caching.
- Now using `curl::multi_download()` to download files in parallel
- Removed dependency on the {httr} package
- {geobr} now imports {fs} to use robust cross-platform file system operations
- Simplified and streamlined internal functions




# geobr v1.9.0

**Major changes**

- Function `read_health_facilities()` now has a new parameter `date`, which will allow users to access data for different dates of reference. The plan is to have at least one update of this data set per year. Closes #334.
- Functions `read_urban_area()` and `read_metro_area()` now have a new parameter `code_state`, which will allow users to filter selected states. Closes #338

**Bug fix**

- Using `data.table::rbindlist()` to rind data was throwing errors when some observations were of class `POLYGONS` and others were `MULTIPOLYGONS`. This has now been replaced with `dplyr::bind_rows()` at a very small performance penalty. Closes #346.

**New data**

- schools for 2023
- health facilities for 202303
- census tracts for 2020 and 2022


# geobr v1.8.2 

**CRAN request**

- Fixed issue to make sure geobr uses suggested packages conditionally

**Minor changes**

- Fixed non-ASCII characters in data `geobr::grid_state_correspondence_table()`



# geobr v1.8.1

**CRAN request**

- geobr now uses suggested packages conditionally



# geobr v1.8.0

**New function**

- `read_capitals()` to download either a spatial `sf` object with the location of the municipal seats (sede dos municipios) of state capitals, or a `data.frame` with the names of codes of state capitals. [Closes #243](https://github.com/ipea/geobr/issues/243)

**Minor changes**

- Update intro vignette to show how to use geobr together with the new [**censobr**](https://ipea.github.io/censobr/index.html) sister package.

**Bug fixes**

- fixed bug from conflict between `sf` and `data.table` that was messing with plot extent. [Closes #284](https://github.com/ipea/geobr/issues/284).
- fixed bug from conflicts between `plotly` and `data.table`. [Closes #279](https://github.com/ipea/geobr/issues/279).
- fixed bug in `cep_to_state()` function. [Closes #317](https://github.com/ipea/geobr/issues/317).
- fixed bug in progress bar. [Closes #154](https://github.com/ipea/geobr/issues/154).
- The `lookup_muni()` and `download_metadata()` functions are now more robust to internet connection failures.


# geobr v1.7.0

**Major changes**

- All data sets are now simultaneously stored on github and on Ipea's server. The package first tries to download the data from Ipea's server. In case Ipea's link is off line for some reason, then the package tries to download the data from github. For users, the effect of this change is that the package is much more stable and less vulnerable to instabilities in data server connection.

**Minor changes**

- Started using package documentation templates with Roxygen
- Reduced a lot of code redundancy
- Important update tothe `check_connection()` function





# geobr v1.6.6

**Minor changes**

- another attempt to make geobr fail gracefully when there is no connection to server.
- Improved documentation of `read_statistical_grid()` Closed #289.



# geobr v1.6.5

**Minor changes**

- Remove packages cruland readr from geobr dependencies.
- geobr now fails gracefully when server connection times out. Closed #259.

**Bug fixes**

- Fixed check_connection() that was failing on Linux. Closed #269.




# geobr v1.6.6

**bug fixes**

- Attempt to make package "fail gracefully".




# geobr v1.6.5

**bug fixes**

- Attempt to make package "fail gracefully".



# geobr v1.6.4

**bug fixes**

- Fixed bug crashing on Solaris.





# geobr v1.6.3

**bug fix**

- Fixed bug with `readr` v2.0 that was crashing on Solaris.




# geobr v1.6.2

**Minor changes**

- Added package `crul` to geobr dependencies.




# geobr v1.6.1

**Minor changes**

- Improved `check_connection()` to fail gracefully. Return message, no error.



# geobr v1.6.0

**New data sets/functions**

- From v1.6 onwards, `geobr` stores downloaded in temporary cache in `tempdir()`. Closes #225.
- New function `read_comparable_areas` to read historically comparable municipalities, aka Areas minimas comparaveis (AMCs). Closes issue #17
- New data set of macro regions og health, which can be accessed using the new `macro` parameter added to `read_health_region()` function. Closes issue #219.
- New internal support function `is_online()`to check internet connection with Ipea server. Closes #229
- New data/function `read_urban_concentrations`. Closes #232
- New data/function `read_pop_arrangements`. Closes #231
- updated data sets for 2020:
  * Country
  * Regions
  * States
  * Micro regions
  * Meso regions
  * Immediate regions
  * Intermediate regions
  * Municipalities
  * Census tracts
- Updated data of indigenous land March 2021
  
**Minor changes**

- Improved package test coverage to 99.16%.
- Improved documentation considering `Roxygen: list(markdown = TRUE)`
- fix column names of `grid_state_correspondence_table`
- Improve warning message regarding connection to geobr server at Ipea
- Fix `read_municipality` when reading a state abbreviation before 1991.



# geobr v1.5-1

**Minor changes**

- Fixed unnecessary warning about internet connection. Closes #200.



# geobr v1.5

**New data sets/functions**

- new function `read_schools` to read the schools data - closes issue #190 (added in 2020-10).
- data of `census_tracts` 2017 from the agricultural census - closes issue #171 (added in 2020-11).
- new function `cep_to_state` to determine the state of a given CEP postal code 
(added in 2021-01).

**Minor changes**

- geobr now automatically detects if there is an internet connection problem and throws an error. Closes issue #178
- imports `data.table` to use `rbindlist` and improve package speed when downloading data for the whole country. Closes issue #199.
- new intro vignette for Python users



# geobr v1.4

**New data sets/functions**

- data set `read_health_region` to read the health regions - closes issue #149 (added in 2020-07).
- updated 2019 data sets of `intermediate`, `immediate` `micro` and `meso` regions, `states` and `municipalities`.

**Minor changes**

- improved documentation of argument `simplified`
- included documentation of argument `zone` in the `read_census_tract` function
- `read_municipality()` function now also takes additional inputs for data sets before 1992. Closes issue #163 (added in 2020-06)
- harmonized the `st_geometry_type()` of data sets to `MULTIPOLYGON`, when appropriate. Closes issues #41 #151  #135 #172
- fix typo in `geobr::grid_state_correspondence_table`. Closes #187
- argument `tp` fully deprecated and replaced with `simplified`. No more warning message
- sample data with life expectancy of Brazilian states in 2017. To be used in vignette



# geobr v1.3 (2020-03-30)

**New data sets/functions**

- data set `read_neighborhood` to read neighborhood limits of Brazilian municipalities - closes issue #104 (added in 2020-03).

**Major changes**

- New argument `showProgress` to display progress bar. Defaults to `TRUE`
- Argument `tp` was deprecated and replaced by argument `simplified` that needs to be either `TRUE` or `FALSE`. This should only affect user who have previously used `tp=TRUE`, who now should write `simplified=FALSE`

**Minor changes**

- reorganization of internal support functions to reduce code redundancy
- substantial improvment in test coverage of functions
- substantial improvment in test coverage of functions
- modified package tests using new format of `crs` objects. Following `sf` package update `v0.9-0`



# geobr v1.2 (2020-02-20)

**New data sets/functions**

- data set `read_metro_area` to read official metropolitan areas - closes issue #2 (added in 2019-12).
- data set `read_municipal_seat` to read the spatial coordinates of municipal seats- closes issue #86 (added in 2019-12).
- function `lookup_muni` to look up municipality codes by their name, or the other way around. closes issue #58 (added in 2019-12)
- function `list_geobr` to list all the datasets available in geobr - Closes issue #57.
  
**Major changes**

- MAJOR change of `geobr` to read `geopackage` files, instead of `.rds`. A structural change that will make it easier to maintain both versions of geobr in R and Python  (2020-02)
- All functions now have an additional argument `tp` as in data 'type'. This argument defaults to read data sets with 'simplified' borders, what makes the package much more efficient for downloading and plotting the data. Closes issue #76 (2020-02)
- Pretty much all functions now download the data for the entire country as a default. Closes issue #77. The only exceptions are `read_statistical_grid` and `read_census_tract`. These two functions do take a really long time to load the data for the whole country and it might crash R due to memory limits, so the user must be more 'aware' about her choice (2020-02)

**Minor changes**

- New utils.R script containing support functions to reduce code redundancy (2020-02)




# geobr v1.1

**New data sets/functions**

- data set `read_indigenous_land` to read official data of indigenous lands of all ethnicities according to stage of demarcation - closes issue #47 (2019-09-04).
- data set `read_disaster_risk_area` to read official data of areas exposed to risks of geodynamic and hydro-meteorological disasters capable of triggering landslides and floods - closes issue #14 (added in 2019-09-24).
- data set `read_biomes` to read official data of polygons of all of all biomes present in Brazilian territory - closes issue #45 (added in 2019-09-24).
- data set `read_amazon` to read official data of Brazil's Legal Amazon - closes issue #38 (added in 2019-10-07).
-  data set `read_conservation_units` to read official data of Environmental Conservation Units - closes issue #59 (added in 2019-10-08).
-  data set `read_urban_area` to read official data of urban footprint of Brazilian cities - closes issue #52 (added in 2019-10-17).
- data set of biomes (2019) available at scale 1:250.000. (added in 2019-10-31) - closes issue #72
- data set of `read_intermediate_region` (2017) (added in 2019-11-28)
- data set of `read_immediate_region` (2017) (added in 2019-11-28)
- function `download_metadata` simply the download of df with data set addresses.

**Minor changes**

* Changes to `read_region` function to improve speed and remove `dplyr`dependency (added in 2019-10-22).
* Shows a single download progress bar when `*_code="all"`. This fixes the output of vignette and closes issue #42 (2019-08-05)




# geobr v1.0

- Launch of **geobr** v1.0 on [CRAN](https://CRAN.R-project.org/package=geobr) with the following data sets:
  * Country
  * States
  * Regions
  * Meso regions
  * Micro regions
  * Municipalities
  * Census weighting areas
  * Census tracts
  * Statistical Grid 
