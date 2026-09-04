import pytest
import warnings

from geobr._duckdb_backend import _reset_shared_connection, query
from tests.conftest import patch_module_attr, register_geom_view, write_geom_parquet


@pytest.fixture(autouse=True)
def reset_duckdb():
    _reset_shared_connection()
    yield
    _reset_shared_connection()


def test_auto_resolve_suffixed_view(monkeypatch, duckdb_conn, tmp_path):
    from shapely.geometry import box

    path = write_geom_parquet(
        tmp_path / "states.parquet",
        {"name_state": ["RJ"], "code_state": [33]},
        geometry=[box(0, 0, 1, 1)],
    )

    def fake_read_geobr_hybrid(v2, gpkg, year, **kwargs):
        register_geom_view(kwargs["connection"], kwargs["view_name"], path)
        return kwargs["connection"].sql(f'SELECT * FROM "{kwargs["view_name"]}"')

    patch_module_attr(monkeypatch, "geobr.utils", "read_geobr_hybrid", fake_read_geobr_hybrid)
    monkeypatch.setattr("geobr._duckdb_backend._known_geos", lambda: {"states"})
    monkeypatch.setattr("geobr._duckdb_backend._available_years", lambda geo: [2010, 2020])

    count = query(
        "SELECT count(*) FROM states_2020",
        connection=duckdb_conn,
    ).fetchone()[0]
    assert count == 1
    tables = {row[0] for row in duckdb_conn.execute("SHOW TABLES").fetchall()}
    assert "states_2020" in tables


def test_auto_resolve_bare_registered_no_warning(monkeypatch, duckdb_conn, tmp_path):
    from shapely.geometry import box

    path = write_geom_parquet(
        tmp_path / "schools.parquet",
        {"code_school": [1]},
        geometry=[box(0, 0, 1, 1)],
    )
    register_geom_view(duckdb_conn, "schools_2020", path)

    monkeypatch.setattr("geobr._duckdb_backend._known_geos", lambda: {"schools"})
    monkeypatch.setattr("geobr._duckdb_backend._available_years", lambda geo: [2020])

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        count = query("SELECT count(*) FROM schools", connection=duckdb_conn).fetchone()[0]
    assert count == 1
    assert not record


def test_auto_resolve_bare_cached_warns(monkeypatch, duckdb_conn, tmp_path):
    from shapely.geometry import box

    cache_file = tmp_path / "schools_2019_simplified.parquet"
    write_geom_parquet(
        cache_file,
        {"code_school": [1]},
        geometry=[box(0, 0, 1, 1)],
    )

    calls = []

    def fake_read_geobr_hybrid(v2, gpkg, year, **kwargs):
        calls.append(year)
        register_geom_view(kwargs["connection"], kwargs["view_name"], cache_file)
        return kwargs["connection"].sql(f'SELECT * FROM "{kwargs["view_name"]}"')

    patch_module_attr(monkeypatch, "geobr.utils", "read_geobr_hybrid", fake_read_geobr_hybrid)
    monkeypatch.setattr("geobr._duckdb_backend._known_geos", lambda: {"schools"})
    monkeypatch.setattr("geobr._duckdb_backend._available_years", lambda geo: [2019, 2020])
    monkeypatch.setattr("geobr._duckdb_backend._cached_years", lambda geo: [2019])

    with pytest.warns(UserWarning, match="FROM schools: no year specified, using cached year 2019"):
        count = query("SELECT count(*) FROM schools", connection=duckdb_conn).fetchone()[0]
    assert count == 1
    assert calls == [2019]


def test_auto_resolve_bare_download_warns(monkeypatch, duckdb_conn, tmp_path):
    from shapely.geometry import box

    path = write_geom_parquet(
        tmp_path / "schools_2020.parquet",
        {"code_school": [1]},
        geometry=[box(0, 0, 1, 1)],
    )
    calls = []

    def fake_read_geobr_hybrid(v2, gpkg, year, **kwargs):
        calls.append(year)
        register_geom_view(kwargs["connection"], kwargs["view_name"], path)
        return kwargs["connection"].sql(f'SELECT * FROM "{kwargs["view_name"]}"')

    patch_module_attr(monkeypatch, "geobr.utils", "read_geobr_hybrid", fake_read_geobr_hybrid)
    monkeypatch.setattr("geobr._duckdb_backend._known_geos", lambda: {"schools"})
    monkeypatch.setattr("geobr._duckdb_backend._available_years", lambda geo: [2019, 2020])
    monkeypatch.setattr("geobr._duckdb_backend._cached_years", lambda geo: [])

    with pytest.warns(
        UserWarning,
        match=(
            "FROM schools: no year specified, using year 2020 \\(most recent available\\). "
            "To choose a year, use FROM schools_2020 in SQL or call "
            "read_schools\\(year=2020, output='duckdb'\\) first. "
            "Available years: 2019, 2020."
        ),
    ):
        count = query("SELECT count(*) FROM schools", connection=duckdb_conn).fetchone()[0]
    assert count == 1
    assert calls == [2020]


def test_auto_resolve_retries_non_simplified(monkeypatch, duckdb_conn, tmp_path):
    """A polygon geography still falls back when its simplified asset is absent.

    Uses `states` rather than `schools`: point layers now resolve to
    `simplified=False` up front (see tests/test_point_geographies.py), so they
    no longer exercise the retry.
    """
    from shapely.geometry import box

    path = write_geom_parquet(
        tmp_path / "states_2020.parquet",
        {"code_state": [33, 35]},
        geometry=[box(0, 0, 1, 1), box(1, 1, 2, 2)],
    )
    simplified_calls = []

    def fake_read_geobr_v2(geography, year, *, simplified, output, connection, view_name, **kwargs):
        simplified_calls.append(simplified)
        if simplified:
            raise ValueError("No simplified data for states in year 2020.")
        register_geom_view(connection, view_name, path)
        return connection.sql(f'SELECT * FROM "{view_name}"')

    patch_module_attr(monkeypatch, "geobr.utils", "read_geobr_v2", fake_read_geobr_v2)
    monkeypatch.setattr("geobr._duckdb_backend._known_geos", lambda: {"states"})
    monkeypatch.setattr("geobr._duckdb_backend._available_years", lambda geo: [2020])

    count = query("SELECT count(*) FROM states_2020", connection=duckdb_conn).fetchone()[0]
    assert count == 2
    assert simplified_calls == [True, False]


def test_auto_resolve_point_layer_skips_the_simplified_attempt(
    monkeypatch, duckdb_conn, tmp_path
):
    """`pollingplaces` is v2_only, so a wrong `simplified=True` had no retry.

    Before the fix this query raised
    `ValueError: No simplified data for pollingplaces in year 2022.`
    """
    from shapely.geometry import Point

    path = write_geom_parquet(
        tmp_path / "pollingplaces_2022.parquet",
        {"code_muni": [3304557, 3550308]},
        geometry=[Point(0, 0), Point(1, 1)],
    )
    simplified_calls = []

    def fake_read_geobr_v2(geography, year, *, simplified, output, connection, view_name, **kwargs):
        simplified_calls.append(simplified)
        if simplified:
            raise ValueError(f"No simplified data for {geography} in year {year}.")
        register_geom_view(connection, view_name, path)
        return connection.sql(f'SELECT * FROM "{view_name}"')

    patch_module_attr(monkeypatch, "geobr.utils", "read_geobr_v2", fake_read_geobr_v2)
    monkeypatch.setattr("geobr._duckdb_backend._known_geos", lambda: {"pollingplaces"})
    monkeypatch.setattr("geobr._duckdb_backend._available_years", lambda geo: [2022])

    count = query(
        "SELECT count(*) FROM pollingplaces_2022", connection=duckdb_conn
    ).fetchone()[0]
    assert count == 2
    assert simplified_calls == [False]
