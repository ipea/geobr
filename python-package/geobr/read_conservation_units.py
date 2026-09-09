from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_conservation_units(
    date: int,
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download conservation unit polygons (MMA).

    Parameters
    ----------
    {date}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """
    return read_geobr_v2(
        "conservationunits",
        date,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
