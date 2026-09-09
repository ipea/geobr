from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_disaster_risk_area(
    year: int,
    code_muni: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download official disaster risk area data (IBGE / CEMADEN).

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
        "disasterriskareas",
        year,
        code=code_muni,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
