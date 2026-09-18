from geobr.utils import read_geobr_v2
from geobr._docstrings import docparams


@docparams
def read_addresses(
    year: int,
    code_muni,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download geolocated data of addresses in Brazil (CNEFE/IBGE).

    Reads the National Registry of Addresses for Statistical Purposes (Cadastro
    Nacional de Enderecos para Fins Estatisticos, CNEFE), organized by IBGE. The
    data brings the spatial coordinates (lat lon) of every address surveyed in
    the Population Census, along with the census tract and municipality each
    address belongs to, its postal code (CEP), the type of building
    (``cod_especie``) and the precision level of its coordinates
    (``nv_geo_coord``).

    Note this is a very large data set: the 2022 CNEFE covers roughly 111
    million addresses in a single 1.2 GB file. The file is downloaded in full
    and only then filtered by ``code_muni``, so the first call in a session
    takes a long time even when a single municipality is requested. Subsequent
    calls reuse the cached file. Passing ``output="duckdb"`` returns a lazy
    relation instead of loading the result into memory.

    Parameters
    ----------
    {year}
    {code_muni_required}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """

    return read_geobr_v2(
        "cnefe",
        year,
        code=code_muni,
        simplified=False,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )
