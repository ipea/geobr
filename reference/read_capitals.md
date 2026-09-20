# Download data of state capitals

This function downloads either a spatial `sf` object with the location
of the municipal seats (sede dos municipios) of state capitals, or a
`data.frame` with the names and codes of state capitals. Data downloaded
for year 2010.

## Usage

``` r
read_capitals(output = "sf", showProgress = TRUE, cache = TRUE, verbose = TRUE)
```

## Arguments

- output:

  String. Type of object returned by the function. Defaults to `"sf"`,
  which loads the data into memory as an sf object. Alternatively,
  `"duckdb"` returns a lazy spatial table backed by DuckDB via the
  duckspatial package, and `"arrow"` returns an Arrow dataset. Both
  `"duckdb"` and `"arrow"` support out-of-memory processing of large
  data sets.

- showProgress:

  Logical. Defaults to `TRUE` display progress bar.

- cache:

  Logical. Whether the function should read the data cached locally,
  which is faster. Defaults to `cache = TRUE`. By default, `geobr`
  stores data files in a temporary directory that exists only within
  each R session. If `cache = FALSE`, the function will download the
  data again and overwrite the local file.

- verbose:

  A logical. If `TRUE` (the default), the function prints informative
  messages and shows download progress bar. If `FALSE`, the function is
  silent.

## Value

An `"sf" "data.frame"` OR an `ArrowObject`

## Examples

``` r
# Read spatial data with the  municipal seats of state capitals
capitals_sf <- read_capitals(output = "sf")
#> ℹ Using year/date 2010
```
