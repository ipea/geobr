import geopandas as gpd
import pytest
from shapely.geometry import Point

from geobr._filter import code_length, filter_by_code, parquet_filters, resolve_filter


def test_filter_all(sample_gdf):
    out = filter_by_code(sample_gdf, "all")
    assert len(out) == 4


def test_filter_state_abbrev(sample_gdf):
    out = filter_by_code(sample_gdf, "RJ")
    assert len(out) == 1
    assert out.iloc[0]["abbrev_state"] == "RJ"


def test_filter_code_state(sample_gdf):
    out = filter_by_code(sample_gdf, 33)
    assert len(out) == 1
    assert out.iloc[0]["abbrev_state"] == "RJ"

def test_filter_code_macro(sample_gdf):
    out = filter_by_code(sample_gdf, 3304)
    assert len(out) == 1
    assert out.iloc[0]["abbrev_state"] == "RJ"


def test_filter_code_muni(sample_gdf):
    out = filter_by_code(sample_gdf, 3304557)
    out2 = filter_by_code(sample_gdf, "3304557")
    assert len(out) == 1
    assert len(out2) == 1


def test_filter_invalid():
    gdf = gpd.GeoDataFrame({"x": [1]}, geometry=[Point(0, 0)], crs="EPSG:4674")
    with pytest.raises(ValueError):
        filter_by_code(gdf, "INVALID")


# --- the release files store every code_* column as double -------------------


@pytest.fixture
def float_gdf(sample_gdf):
    """sample_gdf with code columns as float64, as in every release parquet."""
    gdf = sample_gdf.copy()
    for col in ("code_muni", "code_state", "code_pop_arrangement", "code_alt"):
        gdf[col] = gdf[col].astype("float64")
    return gdf


def test_filter_code_macro_on_float_columns(float_gdf):
    # str(3304.0) is six characters; the digit-length heuristic must measure
    # the integer value or this branch never matches on real data.
    out = filter_by_code(float_gdf, 3304)
    assert len(out) == 1
    assert out.iloc[0]["abbrev_state"] == "RJ"


def test_filter_code_muni_and_state_on_float_columns(float_gdf):
    assert len(filter_by_code(float_gdf, 3304557)) == 1
    assert len(filter_by_code(float_gdf, 33)) == 1


def test_filter_code_with_nulls(float_gdf):
    float_gdf.loc[0, "code_pop_arrangement"] = None
    out = filter_by_code(float_gdf, 3550308)
    assert out.iloc[0]["abbrev_state"] == "SP"


# --- resolve_filter -------------------------------------------------------------


def _lengths(gdf):
    return lambda col: code_length(gdf[col])


@pytest.mark.parametrize(
    "code,column,codes",
    [
        ("RJ", "abbrev_state", ["RJ"]),
        ("rj", "abbrev_state", ["RJ"]),
        (["RJ", "SP"], "abbrev_state", ["RJ", "SP"]),
        (33, "code_state", [33]),
        ("33", "code_state", [33]),
        (3304557, "code_muni", [3304557]),
        ("3304557", "code_muni", [3304557]),
        (3304, "code_alt", [3304]),
    ],
)
def test_resolve_filter(sample_gdf, code, column, codes):
    assert resolve_filter(sample_gdf.columns, code, _lengths(sample_gdf)) == (column, codes)


def test_resolve_filter_missing_column_raises(sample_gdf):
    with pytest.raises(ValueError, match="Invalid value"):
        resolve_filter(["name_muni"], "RJ", _lengths(sample_gdf))


def test_resolve_filter_no_length_match_raises(sample_gdf):
    with pytest.raises(ValueError, match="Invalid value"):
        resolve_filter(sample_gdf.columns, 33045, _lengths(sample_gdf))


def test_resolve_filter_rejects_all(sample_gdf):
    with pytest.raises(ValueError, match="'all'"):
        resolve_filter(sample_gdf.columns, "all", _lengths(sample_gdf))


# --- parquet_filters ------------------------------------------------------------


def test_parquet_filters_all(parquet_path):
    assert parquet_filters(parquet_path, "all") is None
    assert parquet_filters(parquet_path, None) is None


def test_parquet_filters_int_columns(parquet_path):
    assert parquet_filters(parquet_path, "RJ") == [("abbrev_state", "in", ["RJ"])]
    assert parquet_filters(parquet_path, 33) == [("code_state", "in", [33])]
    assert parquet_filters(parquet_path, 3304557) == [("code_muni", "in", [3304557])]
    assert parquet_filters(parquet_path, 3304) == [("code_alt", "in", [3304])]


def test_parquet_filters_types_values_from_schema(tmp_path, float_gdf):
    # double column -> float values; string column -> str values. pyarrow
    # refuses to compare a string list against a double column.
    float_gdf["code_muni"] = float_gdf["code_muni"].astype("int64").astype(str)
    path = tmp_path / "typed.parquet"
    float_gdf.to_parquet(path)

    assert parquet_filters(path, 33) == [("code_state", "in", [33.0])]
    assert parquet_filters(path, 3304) == [("code_alt", "in", [3304.0])]
    assert parquet_filters(path, 3304557) == [("code_muni", "in", ["3304557"])]


def test_parquet_filters_pushdown_reads_only_matching_rows(parquet_path):
    filters = parquet_filters(parquet_path, ["RJ", "SP"])
    out = gpd.read_parquet(parquet_path, filters=filters)
    assert sorted(out["abbrev_state"]) == ["RJ", "SP"]
