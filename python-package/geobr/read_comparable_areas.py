from geobr.utils import select_metadata, download_gpkg
from geobr._docstrings import docparams


@docparams
def read_comparable_areas(
    start_year=1970,
    end_year=2010,
    simplified=True,
    show_progress=True,
    cache=True,
    verbose=False,
):
    r"""Download spatial data of historically comparable municipalities

    This function downloads the shape file of minimum comparable area of
    municipalities, known in Portuguese as 'Areas minimas comparaveis (AMCs)'.
    The data is available for any combination of census years between 1872-2010.
    These data sets are generated based on the Stata code originally developed by
    \doi{10.1590/0101-416147182phe}{Philipp Ehrl}, and translated
    into `R` by the `geobr` team.

    Years available:
        1872,1900,1911,1920,1933,1940,1950,1960,1970,1980,1991,2000,2010

    Parameters
    ----------
    {start_year}
    {end_year}
    {simplified}
    {show_progress}
    {cache}
    {verbose}

    Returns
    -------
    gpd.GeoDataFrame
        Minimum comparable areas (AMCs) for the requested period.

    Raises
    ------
    Exception
        If parameters are not found or not well defined

    Example
    -------
    >>> from geobr import read_comparable_areas

    # Read comparable areas for a given period
    >>> df = read_comparable_areas(start_year=1970, end_year=2010)
    """

    # `show_progress` and `cache` are accepted for signature parity with the R
    # package, where they are likewise unused while the gpkg download path for
    # this data set is suspended.
    del show_progress, cache

    years_available = [
        1872,
        1900,
        1911,
        1920,
        1933,
        1940,
        1950,
        1960,
        1970,
        1980,
        1991,
        2000,
        2010,
    ]

    if (start_year not in years_available) or (end_year not in years_available):
        raise ValueError(
            "Invalid `start_year` or `end_year`."
            f"It must be one of the following: {years_available}"
        )

    metadata = select_metadata("amc", year=start_year, simplified=simplified)

    metadata = metadata.query(f'download_path.str.contains("{start_year}_{end_year}")')

    gdf = download_gpkg(metadata)

    return gdf
