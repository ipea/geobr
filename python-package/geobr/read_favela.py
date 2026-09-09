"""Download spatial data of favelas and urban communities."""

from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_favela(
    year: int,
    code_muni: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download favelas and urban communities (IBGE).

    Parameters
    ----------
    {year}
    {code_muni}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """
    return read_geobr_v2(
        geography="favelas",
        year=year,
        code=code_muni,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
