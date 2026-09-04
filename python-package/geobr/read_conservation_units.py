from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_conservation_units(
    date: int,
    code_state: str = "all",
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """Download conservation unit polygons (MMA).

    Parameters
    ----------
    {date}
    {code_state}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """
    return read_geobr_v2(
        "conservationunits",
        date,
        code=code_state,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
