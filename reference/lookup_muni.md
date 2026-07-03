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
#> duckdb: caching downloaded extensions in the package library:
#> ℹ /home/runner/work/_temp/Library/duckdb/extensions
#> ℹ This is removed when the package is re-installed; see `?duckdb_storage` to choose a different location.
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
