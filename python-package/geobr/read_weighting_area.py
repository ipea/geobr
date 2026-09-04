from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_weighting_area(
    year: int,
    code_weighting: str = "all",
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """Download Census Weighting Areas (area de ponderacao) data of the Brazilian Population Census.

    Parameters
    ----------
    {year}
    {code_weighting}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """

    return read_geobr_v2(
        "weightingareas",
        year,
        code=code_weighting,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )

