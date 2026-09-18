"""Tests for `read_addresses()` — the CNEFE address registry.

The network test is marked, unlike most `test_read_*` modules, because this
data set is a single 1.2 GB file with ~111 million rows. Downloading it on
every CI job (3 OSs x 5 Python versions) is not reasonable, so it runs only
under `pytest -m network`.
"""

import importlib
import inspect

import geopandas as gpd
import pytest

import geobr
from geobr import read_addresses


# --- offline -------------------------------------------------------------


def test_reads_the_cnefe_geography(monkeypatch):
    """The reader names `cnefe` and asks for the original (point) geometry."""
    captured = {}

    def spy(*args, **kwargs):
        captured["geography"] = args[0]
        captured["year"] = args[1]
        captured.update(kwargs)
        return "sentinel"

    mod = importlib.import_module("geobr.read_addresses")
    monkeypatch.setattr(mod, "read_geobr_v2", spy)

    assert read_addresses(2022, 3304557) == "sentinel"
    assert captured["geography"] == "cnefe"
    assert captured["year"] == 2022
    assert captured["code"] == 3304557
    assert captured["simplified"] is False


def test_code_muni_is_required():
    """Unlike most readers, `code_muni` has no default: 111M rows is not a
    sensible implicit request. The failure is a TypeError at call time, before
    anything is downloaded."""
    assert "code_muni" not in {
        name
        for name, p in inspect.signature(read_addresses).parameters.items()
        if p.default is not inspect.Parameter.empty
    }
    with pytest.raises(TypeError):
        read_addresses(year=2022)


def test_is_exported():
    assert geobr.read_addresses is read_addresses
    assert "read_addresses" in geobr.__all__


# --- network -------------------------------------------------------------


@pytest.mark.network
def test_read_addresses():
    gdf = read_addresses(year=2022, code_muni=3167202)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty
    assert set(gdf["code_muni"].unique()) == {3167202}
    assert gdf.crs.to_epsg() == 4674
    assert gdf.geometry.geom_type.unique().tolist() == ["Point"]

    with pytest.raises(Exception):
        read_addresses(year=9999999, code_muni=3167202)


@pytest.mark.network
def test_read_addresses_duckdb_output():
    rel = read_addresses(year=2022, code_muni="RJ", output="duckdb")
    assert rel.shape[0] > 0
