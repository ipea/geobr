# Download geolocated data of addresses in Brazil

This function reads the data of the National Registry of Addresses for
Statistical Purposes (Cadastro Nacional de Enderecos para Fins
Estatisticos, CNEFE), organized by the Brazilian Institute of Geography
and Statistics (IBGE). The data brings the geographical coordinates (lat
lon) of every address surveyed in the Population Census, along with the
census tract and municipality each address belongs to, its postal code
(CEP), the type of building (`cod_especie`) and the precision level of
its coordinates (`nv_geo_coord`). More information available at
<https://www.ibge.gov.br/estatisticas/sociais/populacao/38734-cadastro-nacional-de-enderecos-para-fins-estatisticos.html>.

Note this is a very large data set: the 2022 CNEFE covers roughly 111
million addresses in a single 1.2 GB file. The file is downloaded in
full and only then filtered by `code_muni`, so the first call in an R
session takes a long time even when a single municipality is requested.
Subsequent calls reuse the cached file. Passing `output = "duckdb"`
avoids loading the result into memory.

## Usage

``` r
read_addresses(
  year,
  code_muni,
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

  The 7-digit code of a municipality. Alternatively, if a two-digit
  state code or a two-letter uppercase abbreviation of a state is passed
  (e.g. `33` or `"RJ"`), all data of that state are downloaded. Passing
  `code_muni = "all"` downloads the addresses of the whole country.
  Municipality codes can be consulted with the
  [`geobr::lookup_muni()`](https://ipea.github.io/geobr/reference/lookup_muni.md)
  function. Unlike in most `geobr` functions, this argument is
  **required and has no default**: reading the addresses of the whole
  country may exhaust memory, so the choice is left explicitly to the
  user.

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

# Read all addresses in a given municipality
add <- read_addresses(
  year = 2022,
  code_muni = 3304557
  )
#> ℹ Using year/date 2022

# Read all addresses in a given state, without loading them into memory
add_rj <- read_addresses(
  year = 2022,
  code_muni = "RJ",
  output = "duckdb"
  )
#> ℹ Using year/date 2022
```
