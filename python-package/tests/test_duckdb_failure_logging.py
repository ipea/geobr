"""Failure branches and swallowed-exception logging in `_duckdb_backend`.

Pins the behaviour changed by the Bandit cleanup: exceptions that used to be
discarded with a bare `pass` are now logged at DEBUG (B110), `to_geopandas`
accepts a DuckDB relation (it used to look for a non-existent `.sql()` method
and always raised `TypeError`), and a geometry-less relation yields a plain
`GeoDataFrame` instead of failing.
"""

import logging

import pytest

pytest.importorskip("duckdb")

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from geobr import _duckdb_backend as backend
from geobr._duckdb_backend import (
    GeoBrDuckDB,
    _reset_shared_connection,
    _setup_connection,
    register_dataset,
    to_geopandas,
)
from tests.conftest import write_geom_parquet


class _BoomConnection:
    """Connection stub whose every interaction raises."""

    def execute(self, *args, **kwargs):
        raise RuntimeError("extension unavailable")

    def close(self):
        raise RuntimeError("close failed")


# ---------------------------------------------------------------------------
# Debug logging of previously swallowed exceptions
# ---------------------------------------------------------------------------


def test_setup_connection_logs_extension_failure(caplog):
    with caplog.at_level(logging.DEBUG, logger="geobr._duckdb_backend"):
        _setup_connection(_BoomConnection())  # must not raise
    assert any("failed" in record.getMessage() for record in caplog.records)


def test_reset_shared_connection_logs_close_failure(caplog):
    try:
        backend._CONN = _BoomConnection()
        with caplog.at_level(logging.DEBUG, logger="geobr._duckdb_backend"):
            _reset_shared_connection()
        assert backend._CONN is None
        assert any("failed" in record.getMessage() for record in caplog.records)
    finally:
        backend._CONN = None
        backend._LAST_REGISTERED.clear()


def test_geobr_duckdb_close_logs_failure(caplog):
    session = object.__new__(GeoBrDuckDB)
    session._conn = _BoomConnection()
    with caplog.at_level(logging.DEBUG, logger="geobr._duckdb_backend"):
        session.close()  # must not raise
    assert session._conn is None
    assert any("failed" in record.getMessage() for record in caplog.records)


# ---------------------------------------------------------------------------
# to_geopandas
# ---------------------------------------------------------------------------


def test_to_geopandas_rejects_invalid_type(duckdb_conn):
    with pytest.raises(TypeError, match="must be a view name or DuckDB relation"):
        to_geopandas(123, connection=duckdb_conn)


def test_to_geopandas_accepts_relation_object(duckdb_conn, tmp_path):
    path = write_geom_parquet(
        tmp_path / "rel.parquet",
        {"name_state": ["RJ"], "code_state": [33]},
        geometry=[box(0, 0, 1, 1)],
    )
    relation = register_dataset("rel_2020", path, connection=duckdb_conn)

    # The regression: relations expose `.sql_query()`, never `.sql()`.
    assert hasattr(relation, "sql_query")
    assert not hasattr(relation, "sql")

    gdf = to_geopandas(relation, connection=duckdb_conn)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert gdf.crs.to_epsg() == 4674
    assert gdf.iloc[0]["name_state"] == "RJ"


def test_to_geopandas_without_geometry(duckdb_conn, tmp_path):
    path = tmp_path / "nogeo.parquet"
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_parquet(path)
    relation = duckdb_conn.read_parquet(str(path))

    result = to_geopandas(relation, connection=duckdb_conn)
    assert isinstance(result, gpd.GeoDataFrame)
    assert {"a", "b"} <= set(result.columns)
    assert "geometry" not in result.columns
