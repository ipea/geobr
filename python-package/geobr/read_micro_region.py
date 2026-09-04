from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_micro_region(
    year: int,
    code_micro: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download spatial data of micro region.

    Data at scale 1:250,000, using Geodetic reference system "SIRGAS2000" and CRS(4674)

    Parameters
    ----------
    {year}
    {code_micro}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """

    return read_geobr_v2(
        "microregions",
        year,
        code=code_micro,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
