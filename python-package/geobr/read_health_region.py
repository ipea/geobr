import warnings

from geobr.utils import read_geobr_v2
from geobr._output import convert_output
from geobr._duckdb_backend import duckdb_connection
from geobr._docstrings import docparams


@docparams
def read_health_region(
    year: int,
    code_state: str = "all",
    geometry_level: str = "municipality",
    macro=None,
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download Brazilian health region data.

    Parameters
    ----------
    {year}
    {code_state}
    {geometry_level}
    {macro}
    {simplified}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """
    if macro is not None:
        warnings.warn(
            "The `macro` argument is deprecated. Use `geometry_level` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        geometry_level = "macro" if macro else "municipality"

    allowed = ("municipality", "micro", "macro")
    if geometry_level not in allowed:
        raise ValueError(
            f"`geometry_level` must be one of: {list(allowed)}. Got: {geometry_level!r}"
        )

    relation = read_geobr_v2(
        "healthregions",
        year,
        code=code_state,
        simplified=simplified,
        output="duckdb",
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )

    conn = duckdb_connection()

    if geometry_level == "municipality":
        return convert_output(relation, output, conn)

    all_cols = relation.columns

    # Columns dropped before aggregating, matched by prefix so that
    # municipality-level variants such as `code_muni6` (present in the
    # 1991-2013 files) are dropped as well. Keeping `code_muni6` in the
    # GROUP BY would silently defeat the aggregation. Mirrors the R side.
    if geometry_level == "micro":
        drop_prefixes = (
            "geometry", "code_muni", "name_muni",
            "code_health_macroregion", "name_health_macroregion",
        )
    else:
        drop_prefixes = (
            "geometry", "code_muni", "name_muni",
            "code_health_region", "name_health_region",
        )

    group_cols = [c for c in all_cols if not c.startswith(drop_prefixes)]

    group_cols_str = ", ".join(group_cols)

    # Aggregate results and remove holes
    query = f"""
        WITH aggregated AS (
            -- perform the standard union aggregation
            SELECT
                {group_cols_str},
                ST_Union_Agg(geometry) AS geom
            FROM relation
            GROUP BY {group_cols_str}
        ),
        unwrapped_polygons AS (
            -- flatten multipolygons into separate rows of simple polygons
            SELECT
                {group_cols_str},
                (UNNEST(ST_Dump(geom))).geom AS single_geom
            FROM aggregated
        ),
        holes_removed AS (
            -- remove holes from the simple polygons using the outer ring
            SELECT
                {group_cols_str},
                ST_MakePolygon(ST_ExteriorRing(single_geom)) AS clean_geom
            FROM unwrapped_polygons
        )
        -- recollect the cleaned parts back into the final shapes
        SELECT
            {group_cols_str},
            ST_Union_Agg(clean_geom) AS geometry
        FROM holes_removed
        GROUP BY {group_cols_str};
        """

    relation = conn.sql(query)

    return convert_output(relation, output, conn)
