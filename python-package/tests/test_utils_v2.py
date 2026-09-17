from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess
import sys
import textwrap
import requests

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.types as pat
import pytest

import geobr
from geobr import utils
from geobr._cache import cache_dir, is_cached
from geobr.utils import download_metadata_v2, select_metadata_v2, _download_file, read_geobr_hybrid


class MockStreamResponse:
    def __init__(self, content_bytes, status_code=200):
        self.content_bytes = content_bytes
        self.status_code = status_code
        self.headers = {"content-length": str(len(content_bytes))}

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self.content_bytes), chunk_size):
            yield self.content_bytes[i : i + chunk_size]


@pytest.fixture
def metadata_file():
    return geobr.utils.download_metadata()

def test_cache_dir_exists():
    d = cache_dir()
    assert d.exists()


def test_select_metadata_v2():
    row = select_metadata_v2("states", 2010, simplified=True, verbose=True)
    assert row["file_name"] == "states_2010_simplified.parquet"


def test_select_metadata_v2_no_year():
    row = select_metadata_v2("states", year=None, simplified=True, verbose=True)
    assert row["file_name"] == "states_2025_simplified.parquet"


def test_select_metadata_v2_invalid_year():
    with pytest.raises(ValueError, match="year"):
        select_metadata_v2("states", 1999, simplified=True)


def test_select_metadata_v2_invalid_geo():
    with pytest.raises(ValueError, match="Geography"):
        select_metadata_v2("invalid", 2010, simplified=True)


def test_select_metadata_v2_invalid_simplified():
    with pytest.raises(ValueError, match="No simplified data"):
        select_metadata_v2("schools", year=2025, simplified=True)


def test_download_file(monkeypatch, tmp_path):
    dest = tmp_path / ".parquet"
    data = b"A" * 8192 + b"B" * 8192 + b"C" * 100

    def mock_get(url, stream=False, timeout=None, verify=True):
        return MockStreamResponse(data, status_code=200)

    monkeypatch.setattr(requests, "get", mock_get)

    resultado = _download_file(
        urls=["https://exemplo.com"],
        dest=dest,
        show_progress=True
    )

    assert resultado is True
    assert dest.exists()
    assert dest.read_bytes() == data 
    assert dest.stat().st_size == len(data)


def test_download_file_no_progress(monkeypatch, tmp_path):
    dest = tmp_path / ".parquet"
    data = b"A" * 8192 + b"B" * 8192 + b"C" * 100

    def mock_get(url, stream=False, timeout=None, verify=True):
        return MockStreamResponse(data, status_code=200)

    monkeypatch.setattr(requests, "get", mock_get)

    resultado = _download_file(
        urls=["https://exemplo.com"],
        dest=dest,
        show_progress=False
    )

    assert resultado is True
    assert dest.exists()
    assert dest.read_bytes() == data 
    assert dest.stat().st_size == len(data)


def test_download_file_status_error(monkeypatch, tmp_path):
    dest = tmp_path / ".parquet"
    data = b"A" * 8192 + b"B" * 8192 + b"C" * 100

    def mock_get(url, stream=False, timeout=None, verify=True):
        return MockStreamResponse(data, status_code=404)

    monkeypatch.setattr(requests, "get", mock_get)

    resultado = _download_file(urls=["https://exemplo.com"], dest=dest, show_progress=False)

    assert resultado is False


def test_download_file_exception(monkeypatch, tmp_path):
    dest = tmp_path / ".parquet"

    def mock_get(url, stream=False, timeout=None, verify=True):
        raise ConnectionError()

    monkeypatch.setattr(requests, "get", mock_get)

    resultado = _download_file(urls=["https://exemplo.com"], dest=dest, show_progress=False)

    assert resultado is False


def test_read_geobr_hybrid():
    gdf = read_geobr_hybrid(
        geography_v2="states",
        geography_gpkg="states",
        year=2025
    )
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty

def test_read_geobr_hybrid_legacy(monkeypatch, sample_gdf):
    monkeypatch.setattr(utils, "download_gpkg", lambda a: sample_gdf)
    gdf = read_geobr_hybrid(
        geography_v2="invalid",
        geography_gpkg="state",
        year=2010,
        code="AP"
    )
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty


@pytest.mark.network
def test_download_metadata_v2_live():
    meta = download_metadata_v2()
    assert "file_name" in meta.columns
    assert "geo" in meta.columns
    assert len(meta) > 0


@pytest.mark.network
def test_schools_v2_has_no_simplified_parquet():
    meta = download_metadata_v2()
    schools_2020 = meta[(meta["geo"] == "schools") & (meta["year"] == 2020)]
    assert len(schools_2020) == 1
    assert not schools_2020.iloc[0]["simplified"]
    assert "simplified" not in schools_2020.iloc[0]["file_name"]

    with pytest.raises(ValueError, match="No simplified data for schools"):
        select_metadata_v2("schools", 2020, simplified=True)


# --- read_geobr_v2: engine chosen by `output`, offline via the sample parquet ---


@pytest.fixture
def v2_row(monkeypatch):
    """Point select_metadata_v2 at a fake row; mock_download_parquet serves the file."""
    row = pd.Series(
        {
            "file_name": "states_2010_simplified.parquet",
            "download_url": "https://example.invalid/states_2010_simplified.parquet",
            "geo": "states",
            "year": 2010,
            "simplified": True,
        }
    )
    monkeypatch.setattr(utils, "select_metadata_v2", lambda *a, **k: row)
    return row


def test_read_geobr_v2_gpd_all(v2_row, mock_download_parquet):
    gdf = utils.read_geobr_v2("states", 2010)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 4
    assert gdf.crs.to_string() == "EPSG:4674"
    assert str(gdf["code_muni"].dtype) == "float64"  # enforce_types


@pytest.mark.parametrize(
    "code,expected",
    [
        ("RJ", ["RJ"]),
        (33, ["RJ"]),
        (3304557, ["RJ"]),
        ("3304557", ["RJ"]),
        (3304, ["RJ"]),  # digit-length heuristic on code_alt
        (["RJ", "SP"], ["RJ", "SP"]),
        ([33, 35], ["RJ", "SP"]),
    ],
)
def test_read_geobr_v2_filters(v2_row, mock_download_parquet, code, expected):
    gdf = utils.read_geobr_v2("states", 2010, code=code)
    assert sorted(gdf["abbrev_state"]) == expected


def test_read_geobr_v2_unresolvable_code_raises(v2_row, mock_download_parquet):
    with pytest.raises(ValueError, match="Invalid value"):
        utils.read_geobr_v2("states", 2010, code="ZZ")


def test_read_geobr_v2_unmatched_code_raises(v2_row, mock_download_parquet):
    # Resolves to code_muni, matches nothing: an error, not a silent empty or
    # full result (R parity).
    with pytest.raises(ValueError, match="Invalid value"):
        utils.read_geobr_v2("states", 2010, code=1234567)
    with pytest.raises(ValueError, match="Invalid value"):
        utils.read_geobr_v2("states", 2010, code=1234567, output="arrow")


def test_read_geobr_v2_arrow(v2_row, mock_download_parquet):
    table = utils.read_geobr_v2("states", 2010, code="RJ", output="arrow")
    assert isinstance(table, pa.Table)
    assert table.num_rows == 1
    geom_type = table.column("geometry").type
    assert pat.is_binary(geom_type) or pat.is_large_binary(geom_type)


def test_read_geobr_v2_invalid_output_fails_before_download(v2_row, monkeypatch):
    calls = []
    monkeypatch.setattr(utils, "download_parquet", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match="must be one of"):
        utils.read_geobr_v2("states", 2010, output="geojson")
    assert calls == []


def test_read_geobr_v2_duckdb_relation(v2_row, mock_download_parquet, duckdb_conn):
    rel = utils.read_geobr_v2(
        "states", 2010, code="RJ", output="duckdb", connection=duckdb_conn
    )
    column_types = dict(zip(rel.columns, rel.types))
    assert column_types["geometry"] == "GEOMETRY('EPSG:4674')"
    assert len(rel) == 1
    # the {geo}_{year} view is registered as a side effect, as before
    assert duckdb_conn.sql("SELECT count(*) FROM states_2010").fetchone()[0] == 4


def test_read_geobr_v2_duckdb_unmatched_code_raises(v2_row, mock_download_parquet, duckdb_conn):
    # Same error on the DuckDB path as on the pyarrow one: never a silent
    # empty relation, never the unfiltered file.
    with pytest.raises(ValueError, match="Invalid value"):
        utils.read_geobr_v2("states", 2010, code=1234567, output="duckdb", connection=duckdb_conn)
    with pytest.raises(ValueError, match="Invalid value"):
        utils.read_geobr_v2("states", 2010, code=33045, output="duckdb", connection=duckdb_conn)


def test_readers_work_without_duckdb(parquet_path):
    """`import geobr` and a read must work with duckdb absent; DuckDB features must say why."""
    code = textwrap.dedent(
        f"""
        import sys
        sys.modules["duckdb"] = None          # makes `import duckdb` raise ImportError
        import pandas as pd
        import geobr
        from geobr import utils
        row = pd.Series({{"file_name": "x.parquet", "download_url": "https://example.invalid/x"}})
        utils.select_metadata_v2 = lambda *a, **k: row
        utils.download_parquet = lambda *a, **k: r"{parquet_path}"
        gdf = utils.read_geobr_v2("states", 2010, code="RJ")
        assert len(gdf) == 1, len(gdf)
        table = utils.read_geobr_v2("states", 2010, code=["RJ", "SP"], output="arrow")
        assert table.num_rows == 2, table.num_rows
        try:
            geobr.query("select 1")
        except ImportError as exc:
            assert "geobr[duckdb]" in str(exc), exc
        else:
            raise AssertionError("query() must need the duckdb extra")
        print("NO-DUCKDB-OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, result.stderr
    assert "NO-DUCKDB-OK" in result.stdout
