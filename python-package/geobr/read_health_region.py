import os
import warnings
from concurrent.futures import ThreadPoolExecutor

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon

from geobr.utils import read_geobr_v2
from geobr._output import convert_output
from geobr._duckdb_backend import duckdb_connection
from geobr._docstrings import docparams


def _group_columns(columns, geometry_level):
    """Columns kept through the aggregation for ``micro`` / ``macro``.

    Dropped columns are matched by prefix so that municipality-level variants
    such as ``code_muni6`` (present in the 1991-2013 files) go too. Keeping
    ``code_muni6`` in the grouping would silently defeat the aggregation.
    Mirrors the R side.
    """
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
    return [c for c in columns if not c.startswith(drop_prefixes)]


def _fill_holes(geom):
    return Polygon(geom.exterior) if isinstance(geom, Polygon) else geom


def _union_by_group(gdf: gpd.GeoDataFrame, group_cols: list) -> gpd.GeoDataFrame:
    """Union the geometries of each group, groups in parallel.

    ``shapely.union_all`` releases the GIL, so a thread pool over the groups
    gives real parallelism with no pickling: on the 2025 file (5 571
    municipalities -> 120 macro regions) the union drops from ~19 s serial to
    ~3.5 s on 8 threads, faster than DuckDB's parallel ``ST_Union_Agg``. Each
    group's union is independent of scheduling, so the result is deterministic.
    ``dropna=False`` keeps groups whose key is null, as SQL ``GROUP BY`` does.
    """
    geoms = np.asarray(gdf.geometry.values)
    keys, arrays = [], []
    for key, positions in gdf.groupby(group_cols, dropna=False, sort=True).indices.items():
        keys.append(key if isinstance(key, tuple) else (key,))
        arrays.append(geoms[positions])
    workers = max(1, min(os.cpu_count() or 1, len(arrays)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        unions = list(pool.map(shapely.union_all, arrays))
    frame = pd.DataFrame(keys, columns=group_cols)
    return gpd.GeoDataFrame(frame, geometry=gpd.GeoSeries(unions, crs=gdf.crs))


def _dissolve_remove_holes(gdf: gpd.GeoDataFrame, group_cols: list) -> gpd.GeoDataFrame:
    """Union geometries per group and remove holes from the result.

    The shapely twin of the SQL in the ``output="duckdb"`` branch below and of
    R's ``ddbs_union_agg() |> sf_remove_holes()``: union per group, split
    multipolygons into simple polygons, keep each exterior ring, union again.
    """
    dissolved = _union_by_group(gdf, group_cols)
    parts = dissolved.explode(index_parts=False, ignore_index=True)
    parts = parts.set_geometry(parts.geometry.map(_fill_holes), crs=gdf.crs)
    return _union_by_group(parts, group_cols)


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

    if output == "duckdb":
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
            return relation

        group_cols_str = ", ".join(_group_columns(relation.columns, geometry_level))

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

        return conn.sql(query)

    if output == "arrow" and geometry_level == "municipality":
        # Nothing to post-process: hand pyarrow's table straight through.
        return read_geobr_v2(
            "healthregions",
            year,
            code=code_state,
            simplified=simplified,
            output="arrow",
            show_progress=show_progress,
            cache=cache,
            verbose=verbose,
        )

    gdf = read_geobr_v2(
        "healthregions",
        year,
        code=code_state,
        simplified=simplified,
        output="gpd",
        show_progress=show_progress,
        cache=cache,
        verbose=verbose,
    )

    if geometry_level == "municipality":
        return convert_output(gdf, output)

    gdf = _dissolve_remove_holes(gdf, _group_columns(gdf.columns, geometry_level))

    return convert_output(gdf, output)
