import geopandas as gpd
import pytest
from geobr import read_municipality


def test_read_municipality():

    gdf = read_municipality(year=2025, code_muni="AP")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty

    with pytest.raises(Exception):
        read_municipality(year=9999999)
        read_municipality(year=2025, code_muni="RJ_ABC")


# --- offline: the operational-area filter on both non-DuckDB outputs ------------


def _sample_with_operational_row(sample_gdf):
    gdf = sample_gdf.copy()
    gdf.loc[gdf.index[0], "code_muni"] = 4300001  # Lagoa dos Patos placeholder
    gdf["code_muni"] = gdf["code_muni"].astype("float64")
    return gdf


def _patch_reader(monkeypatch, gdf):
    import importlib

    import pyarrow as pa

    # `geobr.read_municipality` is the re-exported function; import the module.
    mod = importlib.import_module("geobr.read_municipality")

    table = pa.table(gdf.to_arrow(geometry_encoding="WKB"))
    monkeypatch.setattr(
        mod, "read_geobr_v2",
        lambda *a, **k: table if k.get("output") == "arrow" else gdf.copy(),
    )
    return mod


def test_read_municipality_drops_operational_areas_gpd(monkeypatch, sample_gdf):
    mod = _patch_reader(monkeypatch, _sample_with_operational_row(sample_gdf))
    out = mod.read_municipality(2020)
    assert len(out) == 3 and 4300001.0 not in out["code_muni"].tolist()
    assert len(mod.read_municipality(2020, keep_areas_operacionais=True)) == 4


def test_read_municipality_drops_operational_areas_arrow(monkeypatch, sample_gdf):
    import pyarrow as pa

    mod = _patch_reader(monkeypatch, _sample_with_operational_row(sample_gdf))
    out = mod.read_municipality(2020, output="arrow")
    assert isinstance(out, pa.Table)
    assert out.num_rows == 3 and 4300001.0 not in out["code_muni"].to_pylist()
    assert mod.read_municipality(2020, output="arrow", keep_areas_operacionais=True).num_rows == 4
