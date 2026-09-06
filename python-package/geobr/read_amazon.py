from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams

@docparams
def read_amazon(
    year: int,
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download official Brazil's Legal Amazon data (Brazilian Ministry of Environment - MMA).

    Parameters
    ----------
    {year}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """

    return read_geobr_v2(
        "amazonialegal",
        year,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
