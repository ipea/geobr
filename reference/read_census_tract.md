# Download spatial data of census tracts

Data of census tracts (setores censitários) of the Brazilian Population
Census

## Usage

``` r
read_census_tract(
  year,
  code_tract,
  zone = "urban",
  simplified = TRUE,
  output = "sf",
  showProgress = TRUE,
  cache = TRUE,
  verbose = TRUE
)
```

## Arguments

- year:

  Numeric. Year of the data in `YYYY` format.

- code_tract:

  The 7-digit code of a municipality. Alternatively, if a two-digit
  state code or a two-letter uppercase abbreviation of a state is passed
  (e.g. `33` or `"RJ"`), all census tracts of that state are downloaded.
  Passing `code_tract = "all"` downloads all census tracts of the
  country. Municipality codes can be consulted with the
  [`geobr::lookup_muni()`](https://ipea.github.io/geobr/reference/lookup_muni.md)
  function. Unlike in most `geobr` functions, this argument is
  **required and has no default**: loading all census tracts of the
  country takes a long time and may exhaust memory, so the choice is
  left explicitly to the user.

- zone:

  For census tracts before 2010, 'urban' and 'rural' census tracts are
  separate data sets.

- simplified:

  Logic `FALSE` or `TRUE`, indicating whether the function should return
  the data set with 'original' spatial resolution or a data set with
  'simplified' geometry. Defaults to `TRUE`. For spatial analysis and
  statistics users should set `simplified = FALSE`. Borders have been
  simplified by removing vertices of borders using `st_simplify{sf}`
  preserving topology with a `dTolerance` of 100.

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

# Read all census tracts of a state at a given year
c <- read_census_tract(year = 2022, code_tract = "DF")
#> ℹ Using year/date 2022

# Read all census tracts of a municipality at a given year
c <- read_census_tract(year = 2022, code_tract = 5201108)
#> ℹ Using year/date 2022

# Read all census tracts of the country at a given year
c <- read_census_tract(year = 2022, code_tract = "all")
#> ℹ Using year/date 2022

# Read rural census tracts for years before 2007
c <- read_census_tract(
  year = 2000,
  code_tract = 5201108,
  zone = "rural"
  )
#> ℹ Using year/date 2000
```
