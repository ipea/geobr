from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_health_facilities(
    date: int,
    code_muni: str = "all",
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download geolocated health facility data (CNES).

    Parameters
    ----------
    {date}
    {code_muni}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """
    return read_geobr_v2(
        "healthfacilities",
        date,
        code=code_muni,
        simplified=False,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
