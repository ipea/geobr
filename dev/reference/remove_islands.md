# Remove islands from Brazil

Removes Brazilian islands that are approximately more than 20 km from
the mainland coast. This is useful when analyses or data visualization
should focus on the continental territory of Brazil and exclude distant
oceanic islands.

## Usage

``` r
remove_islands(x)
```

## Arguments

- x:

  An 'sf' object with CRS EPSG:4674. Usually an object returned from
  other geobr functions, such as
  [`read_country()`](https://ipea.github.io/geobr/dev/reference/read_country.md),
  `read_states()`,
  [`read_municipality()`](https://ipea.github.io/geobr/dev/reference/read_municipality.md),
  or similar functions.

## Value

An `sf` data frame with the same attributes as `x`, but with distant
islands removed from the geometry.

## Examples

``` r
library(geobr)
library(sf)
#> Linking to GEOS 3.10.2, GDAL 3.4.1, PROJ 8.2.1; sf_use_s2() is TRUE

br <- read_country(year = 1991)
#> ℹ Using year/date 1991

br_no_islands <- remove_islands(br)

plot(br)
```
