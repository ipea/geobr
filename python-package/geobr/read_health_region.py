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

    cols = ", ".join('"' + c.replace('"', '""') + '"' for c in group_cols)

    # Aggregate results and remove holes: union the municipalities, flatten
    # the multipolygons into simple polygons, keep only each outer ring, and
    # recollect the cleaned parts into the final shapes.
    aggregated = relation.aggregate(
        f"{cols}, ST_Union_Agg(geometry) AS geom", cols
    )
    unwrapped_polygons = aggregated.project(
        f"{cols}, (UNNEST(ST_Dump(geom))).geom AS single_geom"
    )
    holes_removed = unwrapped_polygons.project(
        f"{cols}, ST_MakePolygon(ST_ExteriorRing(single_geom)) AS clean_geom"
    )
    relation = holes_removed.aggregate(
        f"{cols}, ST_Union_Agg(clean_geom) AS geometry", cols
    )

    return convert_output(relation, output, conn)
