"""Point layers have no simplified variant, on the SQL/session path too.

`_load_geo_dataset` used to default `simplified=True` for every geography.
For the five point layers that is unsatisfiable: the data release ships no
`*_simplified.parquet` asset, so `select_metadata_v2()` raises. Four of them
were rescued by accident, because `read_geobr_hybrid()` retries with the flag
toggled; `pollingplaces` is `v2_only`, takes the `read_geobr_v2()` branch, and
so failed outright:

    >>> geobr.query("SELECT * FROM pollingplaces_2022")
    ValueError: No simplified data for pollingplaces in year 2022.

The offline tests below pin the resolution logic. The network test checks the
hardcoded set against the live metadata, so upstream drift shows up in CI.
"""

import pytest

from geobr._duckdb_backend import (
    POINT_GEOGRAPHIES,
    _GEO_LOADERS,
    _load_geo_dataset,
    _resolve_simplified,
)


@pytest.fixture
def spy(monkeypatch):
    """Capture the kwargs `_load_geo_dataset` forwards, without downloading."""
    captured = {}

    def fake(*args, **kwargs):
        captured.update(kwargs)
        return "sentinel"

    monkeypatch.setattr("geobr.utils.read_geobr_v2", fake)
    monkeypatch.setattr("geobr.utils.read_geobr_hybrid", fake)
    monkeypatch.setattr(
        "geobr._duckdb_backend._track_registration", lambda *a, **k: None
    )
    return captured


def test_point_geographies_are_known_loaders():
    assert POINT_GEOGRAPHIES <= set(_GEO_LOADERS)


# --- _resolve_simplified -------------------------------------------------


@pytest.mark.parametrize("geo", sorted(POINT_GEOGRAPHIES))
def test_point_layer_defaults_to_original_geometry(geo):
    assert _resolve_simplified(geo, None) is False


@pytest.mark.parametrize("geo", sorted(POINT_GEOGRAPHIES))
def test_explicit_true_on_point_layer_warns_and_downgrades(geo):
    with pytest.warns(UserWarning, match="no simplified variant"):
        assert _resolve_simplified(geo, True) is False


@pytest.mark.parametrize("geo", sorted(POINT_GEOGRAPHIES))
def test_explicit_false_on_point_layer_is_silent(geo, recwarn):
    assert _resolve_simplified(geo, False) is False
    assert len(recwarn) == 0


def test_polygon_layer_keeps_the_simplified_default():
    assert _resolve_simplified("municipalities", None) is True
    assert _resolve_simplified("municipalities", True) is True
    assert _resolve_simplified("municipalities", False) is False


# --- _load_geo_dataset ---------------------------------------------------


def test_load_geo_dataset_passes_false_for_point_layer(spy):
    # pollingplaces is v2_only, so this is the call that used to raise.
    assert _load_geo_dataset("pollingplaces", 2022, connection=None) == "sentinel"
    assert spy["simplified"] is False


def test_load_geo_dataset_keeps_true_for_polygon_layer(spy):
    assert _load_geo_dataset("municipalities", 2020, connection=None) == "sentinel"
    assert spy["simplified"] is True


def test_load_geo_dataset_downgrades_explicit_true(spy):
    with pytest.warns(UserWarning, match="no simplified variant"):
        _load_geo_dataset("schools", 2020, connection=None, simplified=True)
    assert spy["simplified"] is False


# --- the set itself ------------------------------------------------------


@pytest.mark.network
def test_point_geographies_matches_the_data_release():
    """Geographies with no simplified asset upstream == POINT_GEOGRAPHIES."""
    from geobr.utils import download_metadata_v2

    meta = download_metadata_v2()
    without = {
        geo
        for geo, group in meta.groupby("geo")
        if not group["simplified"].any()
    }
    assert without & set(_GEO_LOADERS) == POINT_GEOGRAPHIES
