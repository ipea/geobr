import importlib

import geopandas as gpd
import pandas as pd
import pytest
from pathlib import Path
from shapely.geometry import Point


@pytest.fixture
def sample_gdf():
    """Minimal GeoDataFrame for filter and reading tests."""
    return gpd.GeoDataFrame(
        {
            "code_muni": [3304557, 3550308, 2927408, 1600303],
            "abbrev_state": ["RJ", "SP", "BA", "AP"],
            "code_state": [33, 35, 29, 16],
            "name_muni": ["Rio de Janeiro", "São Paulo", "Salvador", "Macapá"],
            "code_pop_arrangement": [3304557, 3550308, 2927408, 1600303],
            "code_alt": [3304, 3550, 2927, 1600],
        },
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3)],
        crs="EPSG:4674",
    )


@pytest.fixture
def sample_metadata_v2():
    return pd.DataFrame(
        {
            "file_name": ["states_2010_simplified.parquet", "states_2018_simplified.parquet"],
            "geo": ["states", "states"],
            "year": [2010, 2018],
            "simplified": [True, True],
        }
    )


@pytest.fixture
def parquet_path(tmp_path, sample_gdf):
    path = tmp_path / "test.parquet"
    sample_gdf.to_parquet(path)
    return path


@pytest.fixture(autouse=True)
def mock_download_metadata_v2(monkeypatch):
    mod = importlib.import_module("geobr.utils")
    dir = Path(__file__).parent
    metadata_path = dir/"samples"/"metadata_geobr_v2.parquet"

    def _mock_func():
        return pd.read_parquet(metadata_path)

    monkeypatch.setattr(mod, "download_metadata_v2", _mock_func)


@pytest.fixture
def mock_download_parquet(monkeypatch, parquet_path):
    mod = importlib.import_module("geobr.utils")

    monkeypatch.setattr(mod, "download_parquet", lambda *a, **kw: Path(parquet_path))


def patch_module_attr(monkeypatch, module_path: str, attr: str, value):
    """Patch attribute on a submodule (avoids geobr namespace shadowing)."""
    mod = importlib.import_module(module_path)
    monkeypatch.setattr(mod, attr, value)
    return mod


@pytest.fixture
def duckdb_conn():
    # duckdb is an optional extra; every test that asks for this fixture is a
    # DuckDB test and skips cleanly when the extra is not installed.
    pytest.importorskip("duckdb")
    from geobr._duckdb_backend import duckdb_connection, _reset_shared_connection

    _reset_shared_connection()
    conn = duckdb_connection()
    conn.execute("SET threads TO 1;")
    yield conn
    conn.close()
    _reset_shared_connection()


def write_geom_parquet(path, data, geometry):
    """Write a minimal GeoParquet file for DuckDB spatial tests."""
    import geopandas as gpd

    gdf = gpd.GeoDataFrame(data, geometry=geometry, crs="EPSG:4674")
    gdf.to_parquet(path)
    return path


def register_geom_view(conn, view_name, parquet_path):
    from geobr._duckdb_backend import register_dataset

    register_dataset(view_name, parquet_path, connection=conn)
