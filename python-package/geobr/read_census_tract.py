from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_census_tract(
    year: int,
    code_tract: str = "all",
    zone="urban",
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """Download spatial data of census tracts (setores censitários) of the Brazilian Population Census.

    Parameters
    ----------
    {year}
    {code_tract}
    {zone}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """

    allowed = ("urban", "rural")
    if zone not in allowed:
        raise ValueError(
            f"`zone` must be one of: {list(allowed)}. Got: {zone!r}"
        )

    zone_name = None

    if year <= 2007:
        zone_name = zone

    return read_geobr_v2(
        "censustracts",
        year,
        code=code_tract,
        simplified=simplified,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
        zone=zone_name
    )
