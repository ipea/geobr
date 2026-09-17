import importlib

import geopandas as gpd
import pytest

from geobr import read_health_region


def test_read_health_region():
    gdf = read_health_region(year=2025, code_state="AP")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty

    with pytest.raises(Exception):
        read_health_region(year=9999999)


def test_read_health_region_macro():
    with pytest.warns(DeprecationWarning):
        gdf = read_health_region(year=2025, macro=True)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty


def test_read_health_region_micro():
    gdf = read_health_region(year=2025, code_state="AP", geometry_level="micro")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty


def test_read_health_region_invalid_geometry():
    with pytest.raises(ValueError, match="must be one of"):
        read_health_region(year=2025, code_state="AP", geometry_level="invalid")


# --- the shapely dissolve, offline on a synthetic sample --------------------


def test_dissolve_remove_holes_unions_and_fills_holes():
    from shapely.geometry import Polygon, box

    from geobr.read_health_region import _dissolve_remove_holes, _group_columns

    donut = Polygon(
        [(0, 0), (4, 0), (4, 4), (0, 4)],
        holes=[[(1, 1), (3, 1), (3, 3), (1, 3)]],
    )
    gdf = gpd.GeoDataFrame(
        {
            "code_muni": [1, 2, 3, 4],
            "name_muni": ["a", "b", "c", "d"],
            "code_health_region": [10, 10, 20, 20],
            "name_health_region": ["north", "north", "south", "south"],
            "code_state": [33, 33, 33, 33],
        },
        geometry=[donut, box(4, 0, 6, 4), box(10, 0, 11, 1), box(20, 0, 21, 1)],
        crs="EPSG:4674",
    )
    group_cols = _group_columns(gdf.columns, "micro")
    assert group_cols == ["code_health_region", "name_health_region", "code_state"]

    out = _dissolve_remove_holes(gdf, group_cols)

    assert list(out.columns) == group_cols + ["geometry"]
    assert out.crs.to_string() == "EPSG:4674"
    assert sorted(out["code_health_region"]) == [10, 20]

    north = out[out["code_health_region"] == 10].geometry.iloc[0]
    # donut (16 - 4 = 12) + box (8) unioned, then the hole filled: 24
    assert north.area == pytest.approx(24.0)
    assert north.geom_type == "Polygon" and len(north.interiors) == 0

    south = out[out["code_health_region"] == 20].geometry.iloc[0]
    # two disjoint boxes stay a MultiPolygon with no interiors
    assert south.geom_type == "MultiPolygon"
    assert south.area == pytest.approx(2.0)
    assert all(len(p.interiors) == 0 for p in south.geoms)


def test_group_columns_drop_muni6_variants():
    from geobr.read_health_region import _group_columns

    cols = ["code_muni", "code_muni6", "name_muni", "code_health_region",
            "name_health_region", "code_health_macroregion",
            "name_health_macroregion", "code_state", "geometry"]
    assert _group_columns(cols, "macro") == ["code_health_macroregion",
                                             "name_health_macroregion", "code_state"]
