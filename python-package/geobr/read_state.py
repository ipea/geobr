from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_state(
    year: int,
    code_state: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download spatial data of Brazilian states.

    Parameters
    ----------
    {year}
    {code_state}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """

    return read_geobr_v2(
        "states",
        year,
        code=code_state,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
