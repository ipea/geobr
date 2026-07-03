
# geobr: Download Official Spatial Data Sets of Brazil

<img align="right" src="https://github.com/ipea/geobr/blob/master/r-package/man/figures/geobr_logo_b.png?raw=true" alt="logo" width="140">
<img align="right" src="https://github.com/ipea/geobr/blob/master/r-package/man/figures/geobr_logo_y.png?raw=true" alt="logo" width="140">
<p align="justify">

geobr is a computational package to download official spatial data sets
of Brazil. The package covers a wide range of spatial data sets,
available at various geographic scales and for various years with
harmonized attributes, projection and fixed topology (see detailed list
of available data sets below).
</p>

The package is currently available in
[**R**](https://CRAN.R-project.org/package=geobr) and
[**Python**](https://pypi.org/project/geobr/).

| ***R*** | ***Python*** | ***Repo*** |
|----|----|----|
| [![CRAN/METACRAN Version](https://www.r-pkg.org/badges/version/geobr)](https://CRAN.R-project.org/package=geobr) <br /> [![CRAN/METACRAN Total downloads](https://cranlogs.r-pkg.org/badges/grand-total/geobr?color=blue)](https://CRAN.R-project.org/package=geobr) <br /> [![CRAN/METACRAN downloads per month](https://cranlogs.r-pkg.org/badges/geobr?color=yellow)](https://CRAN.R-project.org/package=geobr) <br /> [![Codecov test coverage](https://codecov.io/gh/ipea/geobr/branch/master/graph/badge.svg?flag=r)](https://app.codecov.io/gh/ipea/geobr/tree/master?flags%5B0%5D=r) <br /> [![Lifecycle: stable](https://img.shields.io/badge/lifecycle-stable-brightgreen.svg)](https://www.tidyverse.org/lifecycle/#stable) <br /> [![R build status](https://github.com/ipea/geobr/workflows/R-CMD-check/badge.svg)](https://github.com/ipea/geobr/actions) | [![PyPI version](https://badge.fury.io/py/geobr.svg)](https://badge.fury.io/py/geobr) <br /> [![Downloads](https://static.pepy.tech/badge/geobr)](https://pepy.tech/project/geobr) <br /> [![Downloads](https://static.pepy.tech/badge/geobr/month)](https://pepy.tech/project/geobr) <br /> [![Python Codecov test coverage](https://codecov.io/gh/ipea/geobr/branch/master/graph/badge.svg?flag=python)](https://app.codecov.io/gh/ipea/geobr/tree/master?flags%5B0%5D=python) <br /> [![Lifecycle: stable](https://img.shields.io/badge/lifecycle-stable-brightgreen.svg)](https://www.tidyverse.org/lifecycle/#stable) <br /> [![Python build status](https://github.com/ipea/geobr/workflows/Python-CMD-check/badge.svg)](https://github.com/ipea/geobr/actions) | <img alt="GitHub stars" src="https://img.shields.io/github/stars/ipea/geobr.svg?color=orange"> <br /> <br /> [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) |

## Installation R

``` r
# From CRAN
install.packages("geobr")

# or use the development version with latest features
utils::remove.packages('geobr')
remotes::install_github("ipea/geobr", subdir = "r-package")
```

obs. If you use **Linux**, you need to install a couple dependencies
before installing the libraries `sf` and `geobr`. [More info
here](https://github.com/r-spatial/sf#linux).

## Installation Python

[uv](https://docs.astral.sh/uv/) is the recommended installer. From your
project directory (run `uv init` first if you don’t have a
`pyproject.toml` yet):

``` bash
uv add geobr
```

Alternatively, with pip:

``` bash
pip install geobr
```

*Windows users:*

``` bash
conda create -n geo_env
conda activate geo_env  
conda config --env --add channels conda-forge  
conda config --env --set channel_priority strict  
conda install python=3 geopandas  
uv add geobr
```

# Basic Usage

The syntax of all `geobr` functions operate on the same logic so it
becomes intuitive to download any data set using a single line of code.
Like this:

## R, reading the data as an `sf` object

``` r
library(geobr)

# Read specific municipality at a given year
mun <- read_municipality(code_muni = 1200179, year = 2022)

# Read all municipalities of given state at a given year
mun <- read_municipality(code_muni = "RJ", year = 2022) # or
mun <- read_municipality(code_muni = 33, year = 2022)

# Read all municipalities in the country at a given year
mun <- read_municipality(code_muni="all", year = 2022)
```

More examples in the [intro
Vignette](https://cran.r-project.org/web/packages/geobr/vignettes/intro_to_geobr.html)

## Python, reading the data as a `geopandas` object

``` python
from geobr import read_municipality

# Read specific municipality at a given year
mun = read_municipality(code_muni=1200179, year=2017)

# Read all municipalities of given state at a given year
mun = read_municipality(code_muni=33, year=2010) # or
mun = read_municipality(code_muni="RJ", year=2010)

# Read all municipalities in the country at a given year
mun = read_municipality(code_muni="all", year=2018)
```

Since v1.0.0, the Python package uses a GeoParquet pipeline. For DuckDB workflows, use `query()` to load and
analyze snapshots directly in SQL.

## Python, DuckDB SQL and spatial analysis

Run SQL across geobr snapshots. Missing views are downloaded
automatically on first use.

``` python
from geobr import query, to_geopandas

# Filter a snapshot (auto-downloads states_2020 on first use)
query("""
    SELECT name_state, abbrev_state
    FROM states_2020
    WHERE abbrev_state = 'RJ'
""").df()

# Spatial join across datasets
query("""
    SELECT count(*) AS schools_in_amazon
    FROM schools_2020 s
    JOIN biomes_2019 b ON ST_Within(s.geometry, b.geometry)
    WHERE b.name_biome ILIKE '%Amaz%'
""").df()

# Round-trip to GeoPandas for plotting
gdf = to_geopandas("states_2020")
```

More examples in
[python-package/examples](https://github.com/ipea/geobr/tree/master/python-package/examples),
including
[duckdb_demo.ipynb](https://github.com/ipea/geobr/blob/master/python-package/examples/duckdb_demo.ipynb).

# Available datasets:

You can check all the data sets available with \``list_geobr()`

| Function | Geographies available | Source | Years available |
|:---|:---|:---|:---|
| read_amazon | Brazil’s Legal Amazon | MMA | 2019, 2020, 2021, 2022, 2024 |
| read_biomes | Biomes | IBGE | 2006, 2019, 2025 |
| read_census_tract | Census tract (setor censitário) | IBGE | 2000, 2010, 2022 |
| read_conservation_units | Environmental Conservation Units | MMA | 202402, 202503 |
| read_country | Country | IBGE | 1872, 1900, 1911, 1920, 1933, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2001, 2010, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_disaster_risk_area | Disaster risk areas | CEMADEN and IBGE | 2010 |
| read_favelas | Favelas and urban communities | IBGE | 2022 |
| read_health_facilities | Health facilities | CNES, DataSUS | 201704, 201707, 201710, 201801, 201804, 201807, 201810, 201901, 201904, 201907, 201910, 202001, 202004, 202007, 202010, 202101, 202104, 202107, 202110, 202201, 202204, 202207, 202210, 202301, 202304, 202307, 202310, 202401, 202404, 202407, 202410, 202501, 202504, 202507, 202510, 202601, 202604 |
| read_health_region | Health regions and macro regions | DataSUS | 1991, 1994, 1997, 2001, 2005, 2013, 2023, 2024, 2025 |
| read_immediate_region | Immediate region | IBGE | 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_indigenous_land | Indigenous lands | FUNAI | 2016, 2017, 2018, 2019, 2022, 2024, 2025 |
| read_intermediate_region | Intermediate region | IBGE | 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_meso_region | Meso region | IBGE | 2000, 2001, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022 |
| read_metro_area | Metropolitan areas | IBGE | 1970, 2001, 2002, 2003, 2005, 2008, 2009, 2010, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024 |
| read_micro_region | Micro region | IBGE | 2000, 2001, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022 |
| read_municipality | Municipality | IBGE | 1872, 1900, 1911, 1920, 1933, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2001, 2005, 2007, 2010, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_municipal_seat | Municipality seats (sedes municipais) | IBGE | 1872, 1900, 1911, 1920, 1933, 1940, 1950, 1960, 1970, 1980, 1991, 2010, 2022 |
| read_neighborhood | Neighborhood limits | IBGE | 2010, 2022 |
| read_polling_places | Voting places | TSE | 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024 |
| read_urban_concentrations | Urban concentration areas (concentrações urbanas) | IBGE | 2010 |
| read_pop_arrangements | Population arrangements (arranjos populacionais) | IBGE | 2010 |
| read_quilombola_lands | Quilombola lands officialy recognized | Incra | 202605 |
| read_comparable_areas | Historically comparable municipalities, aka áreas mínimas comparáveis (AMCs) | IBGE | temporarily suspended |
| read_region | Region | IBGE | 1872, 1900, 1911, 1920, 1933, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2001, 2010, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_schools | Schools | INEP | 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_semiarid | Semi Arid region | IBGE | 2005, 2017, 2021, 2022 |
| read_state | States | IBGE | 1872, 1900, 1911, 1920, 1933, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2001, 2010, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| read_statistical_grid | Statistical Grid (gridded population) | IBGE | 2010, 2022 |
| read_urban_area | Urban footprints | IBGE | 2005, 2015, 2019 |
| read_weighting_area | Census weighting area (área de ponderação) | IBGE | 2010 |

point_right: **All datasets use geodetic reference system “SIRGAS2000”,
CRS(4674).**

## Other support functions:

| Function | Action |
|----|----|
| `list_geobr` | List all datasets available in the geobr package |
| `lookup_muni` | Look up municipality codes by their name, or the other way around |
| `remove_islands` | Removes distant oceanic islands from Brazil |
| `grid_state_correspondence_table` | Loads a correspondence table indicating what quadrants of IBGE’s statistical grid intersect with each state |
| `cep_to_state` | Determine the state of a given CEP postal code |
| … | … |

Note 1. Data sets and Functions marked with “dev” are only available in
the development version of `geobr`.

Note 2. Most data sets are available at scale 1:250,000 (see
documentation for details).

# Contributing to geobr

If you would like to contribute to geobr and add new functions or data
sets, please check this
[guide](https://github.com/ipea/geobr/blob/master/CONTRIBUTING.md) to
propose your contribution.

------------------------------------------------------------------------

#### **Related projects**

As of today, there there are no other R or Python computational packages
similar to **geobr**. The **geobr** package makes different
contributions to the community, including for example:

- Access to a wider range of official spatial data sets, such as states
  and municipalities, census tracts, urbanized areas, etc
- A consistent syntax structure across all functions, making the package
  very easy and intuitive to use
- Access to spatial data sets with updated geometries for various years
- Harmonized attributes and geographic projections across geographies
  and years
- Option to download geometries with simplified borders for fast
  rendering
- Option to download geometries as geoarrow objects out of memory
- Stable version published on CRAN for R users, and on PyPI for Python
  users

#### **Similar packages for other countries/continents**

- Africa: [afrimapr](https://afrimapr.github.io/afrimapr.website/)
- Argentina: [geoAr](https://github.com/PoliticaArgentina/geoAr)
- Brazil: [geobr](https://ipea.github.io/geobr/)
- Canada:
  [cancensus](https://mountainmath.github.io/cancensus/index.html)
- Chile: [chilemapas](https://pacha.dev/chilemapas/)
- Czech Republic: [RCzechia](https://github.com/jlacko/RCzechia)
- Finland: [geofi](https://ropengov.github.io/geofi/)
- Kazakhstan: (geokz)\[<https://github.com/arodionoff/geokz>\]
- Peru: [mapsPERU](https://github.com/musajajorge/mapsPERU)
- Spain: [mapSpain](https://github.com/rOpenSpain/mapSpain/)
- UK: [geographr](https://github.com/britishredcrosssociety/geographr)
- Uruguay: [geouy](https://github.com/RichDeto/geouy)
- USA: [tigris](https://github.com/walkerke/tigris)
- Global (political administrative boundaries):
  [rgeoboundaries](https://github.com/wmgeolab/rgeoboundaries)

------------------------------------------------------------------------

# Credits <img align="right" src="https://github.com/ipea/geobr/blob/master/r-package/man/figures/ipea_logo.png?raw=true" alt="ipea" width="300">

Original shapefiles are created by official government institutions. The
**geobr** package is developed by a team at the Institute for Applied
Economic Research (Ipea), Brazil. The package received support from
Instituto Todos pela Saúde (ITpS). If you want to cite this package, you
can cite it as:

- Pereira, R.H.M.; Barbosa, R.J.; et. all (2026) **geobr: Download
  Official Spatial Data Sets of Brazil**. v2.0.0 GitHub repository -
  <https://github.com/ipea/geobr>.
