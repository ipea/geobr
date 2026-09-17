from geobr.utils import read_geobr_v2
from geobr._output import convert_output
from geobr._duckdb_backend import duckdb_connection
from geobr._docstrings import docparams


@docparams
def read_pop_arrangements(
    year: int,
    code_state: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download population arrangements (IBGE).

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
    if output == "duckdb":
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

        return conn.sql(
            "SELECT * FROM relation WHERE code_pop_arrangement IS NOT NULL"
        )

    if output == "arrow":
        import pyarrow.compute as pc

        table = read_geobr_v2(
            "poparrangements",
            year,
            code=code_state,
            simplified=simplified,
            output="arrow",
            show_progress=show_progress,
            cache=cache,
            verbose=verbose,
        )
        return table.filter(pc.is_valid(table["code_pop_arrangement"]))

    gdf = read_geobr_v2(
        "poparrangements",
        year,
        code=code_state,
        simplified=simplified,
        output="gpd",
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )

    gdf = gdf[gdf["code_pop_arrangement"].notna()]

    return convert_output(gdf, output)
