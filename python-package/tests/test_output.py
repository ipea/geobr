import geopandas as gpd
from geopandas.array import GeometryDtype
import pyarrow as pa
import pyarrow.types as pat
import pytest

from geobr._output import ALLOWED_OUTPUTS, convert_output


def test_allowed_outputs_still_lists_duckdb():
    # Validation happens in read_geobr_v2 before any download; "duckdb" must
    # stay a legal value even though this module never serves it.
    assert ALLOWED_OUTPUTS == ("gpd", "duckdb", "arrow")


def test_convert_output_gpd(sample_gdf):
    out = convert_output(sample_gdf, output="gpd")

    assert isinstance(out, gpd.GeoDataFrame)
    assert len(out) == 4
    assert isinstance(out["geometry"].dtype, GeometryDtype)
    assert out.crs.to_string() == "EPSG:4674"
    # enforce_types() applied
    assert str(out["code_muni"].dtype) == "float64"


def test_convert_output_arrow(sample_gdf):
    out = convert_output(sample_gdf, output="arrow")

    assert isinstance(out, pa.Table)
    assert out.num_rows == 4
    assert "geometry" in out.column_names
    assert pat.is_binary(out.column("geometry").type) or pat.is_large_binary(
        out.column("geometry").type
    )


def test_convert_output_duckdb_is_not_served_here(sample_gdf):
    with pytest.raises(ValueError, match="read_geobr_v2"):
        convert_output(sample_gdf, output="duckdb")


def test_convert_output_invalid_format(sample_gdf):
    with pytest.raises(ValueError, match="must be one of"):
        convert_output(sample_gdf, output="invalid")
