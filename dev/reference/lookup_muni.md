# Look up municipality codes and names

Input a municipality **name** *or* **code** and get the names and codes
of the municipality.

## Usage

``` r
lookup_muni(year, name_muni = NULL, code_muni = NULL)
```

## Arguments

- year:

  Numeric. Year of the data in `YYYY` format.

- name_muni:

  The municipality name to be looked up.

- code_muni:

  The municipality code to be looked up.

## Value

A `data.frame` with 13 columns identifying the geographies information
of that municipality.

A `data.frame`

## Details

Only available from 2010 Census data so far

## Examples

``` r
# Look for municipality Rio de Janeiro
mun <- lookup_muni(
  name_muni = "Rio de Janeiro",
  year = 2022
  )
#> duckdb keeps downloaded extensions and secrets in a temporary directory:
#> ℹ /tmp/RtmpiTrgwM/duckdb
#> This is removed when the R session ends.
#> • Extensions are re-downloaded each session.
#> • Secrets are lost.
#> ℹ Run duckdb(shared_home = TRUE) (or create ~/.duckdb) to keep them (suitable for most users).
#> ℹ Run duckdb(shared_home = FALSE) to accept the temporary directory (and silence this message).
#> ℹ See ?duckdb_storage for details and alternatives.
#> ℹ Using year/date 2022

# Look for a given municipality code
mun <- lookup_muni(
  code_muni = 3304557,
  year = 2022
  )
#> ℹ Using year/date 2022

# Get the lookup table for all municipalities
mun_all <- lookup_muni(
  name_muni = "all",
  year = 2022
  )
#> ℹ Using year/date 2022

# Or:
mun_all <- lookup_muni(
  code_muni = "all",
  year = 2022
  )
#> ℹ Using year/date 2022
```
