from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_immediate_region(
    year: int,
    code_immediate: str = "all",
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """ Download Brazil's Immediate Geographic Areas data (IBGE).

     The Immediate Geographic Areas are part of the geographic division of
     Brazil created in 2017 by IBGE to replace the "Micro Regions" division.
     Data at scale 1:250,000, using Geodetic reference system "SIRGAS2000"
     and CRS(4674)

    Parameters
    ----------
    {year}
    {code_immediate}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """

    return read_geobr_v2(
        "immediateregions",
        year,
        code=code_immediate,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
