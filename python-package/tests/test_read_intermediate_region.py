import geopandas as gpd
import pytest
from geobr import read_intermediate_region


def test_read_intermediate_region():

    gdf = read_intermediate_region(year=2025, code_intermediate="AP")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert not gdf.empty

    with pytest.raises(Exception):
        read_intermediate_region(year=9999999)

