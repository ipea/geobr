# geobr: Download Official Spatial Data Sets of Brazil 

<img align="right" src="https://github.com/ipea/geobr/blob/master/r-package/man/figures/geobr_logo_b.png?raw=true" alt="logo" width="140"> 
<img align="right" src="https://github.com/ipea/geobr/blob/master/r-package/man/figures/geobr_logo_y.png?raw=true" alt="logo" width="140">
<p align="justify">geobr is a computational package to download official spatial data sets of Brazil. The package includes a wide range of geospatial data in geopackage format (like shapefiles but better), available at various geographic scales and for various years with harmonized attributes, projection and topology (see detailed list of available data sets below). </p> 

## [READ FULL DOCS](https://github.com/ipea/geobr)

## Contribute

To start the development environment run

```sh
uv sync
```

Test with

`uv run pytest -n auto`

You can use a helper to translate a function from R.
If you want to add `read_biomes`, just run

```sh
uv run python helpers/translate_from_R.py read_biomes
```

It will scrape the original R function to get documentation and metadata.
It adds:
- default year
- function name
- documentation one liner
- larger documentation
- very basic tests

! Be aware that if the function that you are adding is more complicated than the template. So, always double check !

# Release new version

1. Update `version` in `pyproject.toml` and the `CHANGELOG.md`.
2. Commit and push to `master`.
3. Tag the release (the `python-v` prefix avoids conflicts with R package tags):

```sh
git tag python-v1.0.0
git push origin python-v1.0.0
```

4. The `Python-publish-PyPI` workflow will automatically build, test, and upload to PyPI.
