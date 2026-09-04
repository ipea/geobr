from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams

@docparams
def read_statistical_grid(
    year: int,
    code_muni,
    verbose=False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """Download IBGE statistical grid data.

    Parameters
    ----------
    {year}
    {code_muni}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """

    return read_geobr_v2(
        "statsgrid",
        year,
        code=code_muni,
        simplified=False,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
