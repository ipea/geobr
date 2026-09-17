import geopandas as gpd
import pytest
from geobr import read_pop_arrangements


def test_read_pop_arrangements():

    gdf = read_pop_arrangements(year=2010, code_state="AP")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty

    with pytest.raises(Exception):
        read_pop_arrangements(year=9999999)


# --- offline: rows without an arrangement code are dropped on both outputs ------


def test_read_pop_arrangements_drops_null_codes(monkeypatch, sample_gdf):
    import importlib

    import pyarrow as pa

    # `geobr.read_pop_arrangements` is the re-exported function; import the module.
    mod = importlib.import_module("geobr.read_pop_arrangements")

    gdf = sample_gdf.copy()
    gdf["code_pop_arrangement"] = gdf["code_pop_arrangement"].astype("float64")
    gdf.loc[gdf.index[0], "code_pop_arrangement"] = None
    table = pa.table(gdf.to_arrow(geometry_encoding="WKB"))
    monkeypatch.setattr(
        mod, "read_geobr_v2",
        lambda *a, **k: table if k.get("output") == "arrow" else gdf.copy(),
    )
    assert len(mod.read_pop_arrangements(2015)) == 3
    out = mod.read_pop_arrangements(2015, output="arrow")
    assert isinstance(out, pa.Table) and out.num_rows == 3
    assert out["code_pop_arrangement"].null_count == 0
