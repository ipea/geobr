from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_intermediate_region(
    year: int,
    code_intermadiate: str = "all",
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    r"""Download Brazil's Intermediate Geographic Areas data (IBGE).

    The intermediate Geographic Areas are part of the geographic division of
    Brazil created in 2017 by IBGE. These regions were created to replace the
    "Meso Regions" division. Data at scale 1:250,000, using Geodetic reference
    system "SIRGAS2000" and CRS(4674)

    Parameters
    ----------
    {year}
    {code_intermadiate}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """

    return read_geobr_v2(
        "intermediateregions",
        year,
        code=code_intermadiate,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
