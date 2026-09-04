from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_semiarid(
    year: int,
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """ Download official data of Brazilian Semiarid region (IBGE).

    Parameters
    ----------
    {year}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """
    return read_geobr_v2(
        "semiarid",
        year,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
