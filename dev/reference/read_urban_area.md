# Download spatial data of urbanized areas in Brazil

This function reads the official data on the urban footprint of
Brazilian cities. Original data by the Brazilian Institute of Geography
and Statistics (IBGE) For more information about the methodology, see
details at
<https://biblioteca.ibge.gov.br/visualizacao/livros/liv100639.pdf>

## Usage

``` r
read_urban_area(
  year,
  code_muni = "all",
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

## Value

An `"sf" "data.frame"` OR an `ArrowObject`

## Examples

``` r
# Read urban footprint of Brazilian cities in an specific year
d <- read_urban_area(year = 2015)
#> ℹ Using year/date 2015
```
