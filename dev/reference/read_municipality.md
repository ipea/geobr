# Download spatial data of Brazilian municipalities

Brazilian municipalities

## Usage

``` r
read_municipality(
  year,
  code_muni = "all",
  simplified = TRUE,
  output = "sf",
  showProgress = TRUE,
  cache = TRUE,
  verbose = TRUE,
  keep_areas_operacionais = FALSE
)
```

## Arguments

- year:

  Numeric. Year of the data in `YYYY` format.

- code_muni:

  The 7-digit code of a municipality. If `code_muni = "all"` (Default),
  the function downloads all the data available in the country.
  Alternatively, if a two-digit state code or a two-letter uppercase
  abbreviation of a state is passed (e.g. `33` or `"RJ"`), all data of
  that state are downloaded. Municipality codes can be consulted with
  the
  [`geobr::lookup_muni()`](https://ipea.github.io/geobr/dev/reference/lookup_muni.md)
  function.

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

- keep_areas_operacionais:

  Logic. Whether the function should keep the polygons of Lagoas dos
  Patos and Lagoa Mirim in the State of Rio Grande do Sul (considered as
  areas estaduais operacionais). Defaults to `FALSE`.

## Value

An `"sf" "data.frame"` OR an `ArrowObject`

## Examples

``` r
# Read specific municipality at a given year
mun <- read_municipality(code_muni = 1200179, year = 2017)
#> ℹ Using year/date 2017

# Read all municipalities of a state at a given year
mun <- read_municipality(code_muni = 33, year = 2010)
#> ℹ Using year/date 2010
mun <- read_municipality(code_muni = "RJ", year = 2010)
#> ℹ Using year/date 2010

# Read all municipalities of the country at a given year
mun <- read_municipality(code_muni = "all", year = 2018)
#> ℹ Using year/date 2018
```
