# Download geolocated data of health facilities

Data comes from the National Registry of Health Facilities (Cadastro
Nacional de Estabelecimentos de Saude - CNES), originally collected by
the Brazilian Ministry of Health. The spatial coordinates used in geobr
are a combination of the coordinates produced by the original data
producer and the coordinates found via geocoding with the geocodebr
package <https://CRAN.R-project.org/package=geocodebr>. Whenever the
distance between the coordinates from both sources is smaller than 800
meters, geobr uses coordinates from the data producer. When the distance
between the two sources is greater than 800 meters and the results from
geocodebr have a precision level finer than 800 meters, geobr uses the
coordinates from geocodebr. When the coordinates from the original
source are missing, geobr also uses geocodebr coordinates, regardless of
precision level. The source of the spatial coordinates used in each
observation is registered in the data in a specific column
`coords_source`. Additional columns indicating the precision level of
geocodebr geocoding are also included in the data.

## Usage

``` r
read_health_facilities(
  date,
  code_muni = "all",
  output = "sf",
  showProgress = TRUE,
  cache = TRUE,
  verbose = TRUE
)
```

## Arguments

- date:

  Numeric. Date of the data in `YYYYMM` format.

- code_muni:

  The 7-digit code of a municipality. If `code_muni = "all"` (Default),
  the function downloads all the data available in the country.
  Alternatively, if a two-digit state code or a two-letter uppercase
  abbreviation of a state is passed (e.g. `33` or `"RJ"`), all data of
  that state are downloaded. Municipality codes can be consulted with
  the
  [`geobr::lookup_muni()`](https://ipea.github.io/geobr/dev/reference/lookup_muni.md)
  function.

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
# Read health facilities of a given state
h <- read_health_facilities(
  date = 202601,
  code_muni = "PA"
  )
#> ℹ Using year/date 202601

# Read all health facilities of the whole country
h <- read_health_facilities(date = 202601)
#> ℹ Using year/date 202601
```
