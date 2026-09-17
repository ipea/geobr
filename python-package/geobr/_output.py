"""Convert an in-memory GeoDataFrame to the requested output format.

``"duckdb"`` never reaches this module: ``read_geobr_v2`` returns the lazy
relation itself, and readers that post-process keep their SQL body for that
output. ``ALLOWED_OUTPUTS`` still lists it so callers can validate ``output``
in one place, before any download.
"""

from __future__ import annotations

from typing import Literal

import geopandas as gpd

OutputType = Literal["gpd", "duckdb", "arrow"]

ALLOWED_OUTPUTS = ("gpd", "duckdb", "arrow")


def convert_output(gdf: gpd.GeoDataFrame, output: OutputType = "gpd") -> object:
    """Return ``gdf`` as a GeoDataFrame (``"gpd"``) or an Arrow table (``"arrow"``).

    ``"arrow"`` encodes the geometry column as WKB binary, the same shape the
    DuckDB path produced.
    """
    if output not in ALLOWED_OUTPUTS:
        raise ValueError(
            f"`output` must be one of: {list(ALLOWED_OUTPUTS)}. Got: {output!r}"
        )
    if output == "duckdb":
        raise ValueError(
            'output="duckdb" is served by read_geobr_v2() directly; '
            "convert_output() only handles in-memory frames."
        )

    if output == "gpd":
        from geobr.utils import enforce_types

        return enforce_types(gdf)

    import pyarrow as pa

    return pa.table(gdf.to_arrow(geometry_encoding="WKB"))
