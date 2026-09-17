from geobr.utils import read_geobr_v2
from geobr._output import convert_output
from geobr._duckdb_backend import duckdb_connection
from geobr._docstrings import docparams

# IBGE operational water areas in RS (Lagoa dos Patos / Lagoa Mirim) — code_muni placeholders
_RS_OPERATIONAL_CODES = [4300001, 4300002]


@docparams
def read_municipality(
    year,
    code_muni="all",
    simplified=True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose=False,
    keep_areas_operacionais=False,
):
    """Download shape files of Brazilian municipalities.

    Parameters
    ----------
    {year}
    {code_muni}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}
    {keep_areas_operacionais}

    """

    if output == "duckdb":
        relation = read_geobr_v2(
            "municipalities",
            year,
            code=code_muni,
            simplified=simplified,
            output="duckdb",
            show_progress=show_progress,
            cache=cache,
            verbose=verbose,
        )

        conn = duckdb_connection()

        if not keep_areas_operacionais and "code_muni" in relation.columns:
            exclude_codes = ", ".join([f"'{c}'" for c in _RS_OPERATIONAL_CODES])
            relation = conn.sql(
                f"SELECT * FROM relation WHERE CAST(code_muni AS BIGINT) NOT IN ({exclude_codes})"
            )

        return relation

    if output == "arrow":
        # Filter on the Arrow table directly: decoding WKB to shapely only to
        # re-encode it would cost seconds on the full-resolution file.
        import pyarrow as pa
        import pyarrow.compute as pc

        table = read_geobr_v2(
            "municipalities",
            year,
            code=code_muni,
            simplified=simplified,
            output="arrow",
            show_progress=show_progress,
            cache=cache,
            verbose=verbose,
        )
        if not keep_areas_operacionais and "code_muni" in table.column_names:
            codes = pa.array([float(c) for c in _RS_OPERATIONAL_CODES], type=pa.float64())
            is_operational = pc.is_in(pc.cast(table["code_muni"], pa.float64()), value_set=codes)
            table = table.filter(pc.fill_null(pc.invert(is_operational), True))
        return table

    gdf = read_geobr_v2(
        "municipalities",
        year,
        code=code_muni,
        simplified=simplified,
        output="gpd",
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )

    if not keep_areas_operacionais and "code_muni" in gdf.columns:
        gdf = gdf[~gdf["code_muni"].isin(_RS_OPERATIONAL_CODES)]

    return convert_output(gdf, output)
