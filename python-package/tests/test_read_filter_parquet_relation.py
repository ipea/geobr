"""Unit tests for `read_filter_parquet_relation` (DuckDB parquet filtering).

The function is the shared entry point used by `read_geobr_v2()` to build a
DuckDB relation over a parquet file and apply the same code filter that
`geobr._filter.filter_by_code` applies in memory. These tests exercise it
directly (rather than through a `read_*()` reader) so that each dispatch branch
and the `view_name` contract are pinned independently.
"""

import pytest

pytest.importorskip("duckdb")

import geopandas as gpd
from shapely.geometry import Point

from geobr._duckdb_backend import (
    _reset_shared_connection,
    read_filter_parquet_relation,
)
from tests.conftest import write_geom_parquet


@pytest.fixture(autouse=True)
def reset_duckdb():
    _reset_shared_connection()
    yield
    _reset_shared_connection()


@pytest.fixture
def codes_parquet(tmp_path, sample_gdf):
    """A parquet carrying every code column the dispatch branches look for."""
    return write_geom_parquet(
        tmp_path / "codes.parquet",
        sample_gdf.drop(columns="geometry").to_dict("list"),
        geometry=list(sample_gdf.geometry),
    )


def _rows(rel):
    """Fetch a relation as (ordered) list of dicts for easy assertions."""
    return rel.df().to_dict("records")


# ---------------------------------------------------------------------------
# Pass-through branches
# ---------------------------------------------------------------------------


def test_all_returns_every_row(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, "all", connection=duckdb_conn)
    assert len(_rows(rel)) == 4


def test_none_filter_returns_every_row(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, None, connection=duckdb_conn)
    assert len(_rows(rel)) == 4


def test_default_filter_is_all(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, connection=duckdb_conn)
    assert len(_rows(rel)) == 4


def test_no_view_registered_without_view_name(duckdb_conn, codes_parquet):
    read_filter_parquet_relation(codes_parquet, "RJ", connection=duckdb_conn)
    tables = {row[0] for row in duckdb_conn.execute("SHOW TABLES").fetchall()}
    assert tables == set()


# ---------------------------------------------------------------------------
# abrev_state branch
# ---------------------------------------------------------------------------


def test_filters_by_state_abbrev(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, "RJ", connection=duckdb_conn)
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["abbrev_state"] == "RJ"


def test_state_abbrev_is_normalized_to_uppercase(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, "rj", connection=duckdb_conn)
    assert [r["abbrev_state"] for r in _rows(rel)] == ["RJ"]


def test_filters_by_multiple_abbrevs(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(
        codes_parquet, ["RJ", "BA"], connection=duckdb_conn
    )
    assert {r["abbrev_state"] for r in _rows(rel)} == {"RJ", "BA"}


# ---------------------------------------------------------------------------
# code_state branch
# ---------------------------------------------------------------------------


def test_filters_by_state_code_int(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, 33, connection=duckdb_conn)
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["abbrev_state"] == "RJ"


def test_filters_by_state_code_string(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, "35", connection=duckdb_conn)
    assert [r["abbrev_state"] for r in _rows(rel)] == ["SP"]


def test_filters_by_multiple_state_codes(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(
        codes_parquet, [33, 29], connection=duckdb_conn
    )
    assert {r["abbrev_state"] for r in _rows(rel)} == {"RJ", "BA"}


# ---------------------------------------------------------------------------
# code_muni branch
# ---------------------------------------------------------------------------


def test_filters_by_municipality_code(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, 3304557, connection=duckdb_conn)
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["name_muni"] == "Rio de Janeiro"


def test_filters_by_municipality_code_string(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(codes_parquet, "3550308", connection=duckdb_conn)
    assert [r["name_muni"] for r in _rows(rel)] == ["São Paulo"]


# ---------------------------------------------------------------------------
# Generic code_* suffix branch (no code_muni column)
# ---------------------------------------------------------------------------


def test_seven_digit_code_falls_back_to_suffix_column(duckdb_conn, tmp_path):
    """Without `code_muni`, a 7-digit code matches a matching-length code_* col."""
    path = write_geom_parquet(
        tmp_path / "poparr.parquet",
        {
            "abbrev_state": ["RJ", "SP"],
            "code_state": [33, 35],
            "code_pop_arrangement": [3304557, 3550308],
            "code_alt": [3304, 3550],
        },
        geometry=[Point(0, 0), Point(1, 1)],
    )
    rel = read_filter_parquet_relation(path, 3304557, connection=duckdb_conn)
    assert [r["abbrev_state"] for r in _rows(rel)] == ["RJ"]


def test_four_digit_code_matches_shortest_matching_suffix(duckdb_conn, codes_parquet):
    # `code_alt` (4 digits) matches; `code_pop_arrangement` (7 digits) does not.
    rel = read_filter_parquet_relation(codes_parquet, 3304, connection=duckdb_conn)
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["name_muni"] == "Rio de Janeiro"


def test_first_matching_suffix_column_wins(duckdb_conn, tmp_path):
    """Within the generic branch, the first width-matching code_* column wins."""
    path = write_geom_parquet(
        tmp_path / "ambiguous.parquet",
        {
            "code_state": [33, 35],
            "code_a": [1111, 2222],
            "code_b": [3333, 4444],
        },
        geometry=[Point(0, 0), Point(1, 1)],
    )
    rel = read_filter_parquet_relation(path, 1111, connection=duckdb_conn)
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["code_a"] == 1111


def test_municipality_code_wins_over_other_seven_digit_column(duckdb_conn, tmp_path):
    """A 7-digit code resolves to `code_muni`, matching `filter_arrw()`.

    R checks `code_muni` last, so it overrides the generic `code_*` branch even
    when another 7-digit `code_*` column is present.
    """
    path = write_geom_parquet(
        tmp_path / "mixed7.parquet",
        {
            "code_muni": [3304557, 3550308],
            "abbrev_state": ["RJ", "SP"],
            "code_state": [33, 35],
            "code_pop_arrangement": [9999999, 8888888],
        },
        geometry=[Point(0, 0), Point(1, 1)],
    )
    rel = read_filter_parquet_relation(path, 3304557, connection=duckdb_conn)
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["abbrev_state"] == "RJ"


# ---------------------------------------------------------------------------
# view_name contract
# ---------------------------------------------------------------------------


def test_view_name_registers_a_queryable_view(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(
        codes_parquet, "all", connection=duckdb_conn, view_name="codes_2020"
    )
    tables = {row[0] for row in duckdb_conn.execute("SHOW TABLES").fetchall()}
    assert "codes_2020" in tables
    assert len(_rows(rel)) == 4
    count = duckdb_conn.sql("SELECT count(*) FROM codes_2020").fetchone()[0]
    assert count == 4


def test_view_name_still_applies_the_filter(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(
        codes_parquet, "RJ", connection=duckdb_conn, view_name="codes_2020"
    )
    rows = _rows(rel)
    assert len(rows) == 1
    assert rows[0]["abbrev_state"] == "RJ"


def test_view_name_is_idempotent(duckdb_conn, codes_parquet):
    first = read_filter_parquet_relation(
        codes_parquet, "RJ", connection=duckdb_conn, view_name="codes_2020"
    )
    second = read_filter_parquet_relation(
        codes_parquet, 35, connection=duckdb_conn, view_name="codes_2020"
    )
    assert len(_rows(first)) == 1
    assert [r["abbrev_state"] for r in _rows(second)] == ["SP"]


def test_view_name_with_double_quote_is_escaped(duckdb_conn, codes_parquet):
    rel = read_filter_parquet_relation(
        codes_parquet, "RJ", connection=duckdb_conn, view_name='we"ird'
    )
    assert len(_rows(rel)) == 1


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------


def test_path_with_apostrophe_is_escaped(duckdb_conn, tmp_path, sample_gdf):
    path = write_geom_parquet(
        tmp_path / "o'brien.parquet",
        sample_gdf.drop(columns="geometry").to_dict("list"),
        geometry=list(sample_gdf.geometry),
    )
    rel = read_filter_parquet_relation(path, "RJ", connection=duckdb_conn)
    assert len(_rows(rel)) == 1


# ---------------------------------------------------------------------------
# Invalid input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_code",
    [
        "XX",  # not a state abbreviation
        9999999,  # 7 digits, but no such municipality
        9999,  # 4 digits, matches no code_* column
    ],
)
def test_invalid_code_raises_value_error(duckdb_conn, codes_parquet, bad_code):
    with pytest.raises(ValueError):
        read_filter_parquet_relation(codes_parquet, bad_code, connection=duckdb_conn)


def test_abbrev_without_abbrev_column_raises(duckdb_conn, tmp_path):
    path = write_geom_parquet(
        tmp_path / "noabbrev.parquet",
        {"code_state": [33, 35]},
        geometry=[Point(0, 0), Point(1, 1)],
    )
    with pytest.raises(ValueError):
        read_filter_parquet_relation(path, "RJ", connection=duckdb_conn)


def test_all_inside_a_list_raises(duckdb_conn, codes_parquet):
    """Scalar `"all"` short-circuits, but `["all"]` is not a valid code list."""
    with pytest.raises(ValueError):
        read_filter_parquet_relation(codes_parquet, ["all"], connection=duckdb_conn)
