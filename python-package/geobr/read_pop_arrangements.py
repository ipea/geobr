from geobr.utils import read_geobr_v2
from geobr._output import convert_output
from geobr._duckdb_backend import duckdb_connection
from geobr._docstrings import docparams


@docparams
def read_pop_arrangements(
    year: InterruptedError,
    code_state: str = "all",
    simplified: bool = True,
    verbose: bool = False,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
):
    """Download population arrangements (IBGE).

    Parameters
    ----------
    {year}
    {code_state}
    {simplified}
    {verbose}
    {output}
    {show_progress}
    {cache}

    """
    relation = read_geobr_v2(
        "poparrangements",
        year,
        code=code_state,
        simplified=simplified,
        output="duckdb",
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )

    conn = duckdb_connection()

    relation = conn.sql(
        "SELECT * FROM relation WHERE code_pop_arrangement IS NOT NULL"
    )

    return convert_output(relation, output, conn)
