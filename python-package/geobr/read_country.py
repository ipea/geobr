from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_country(
    year: int,
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download Brazil's national borders data.

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
        "country",
        year,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
