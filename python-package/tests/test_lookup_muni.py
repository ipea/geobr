import importlib

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from geobr.lookup_muni import lookup_muni


@pytest.fixture
def mock_seat():
    return gpd.GeoDataFrame(
        {
            "code_muni": [3304557, 3550308],
            "name_muni": ["Rio de Janeiro", "São Paulo"],
            "abbrev_state": ["RJ", "SP"],
            "code_state": [33, 35],
        },
        geometry=[Point(0, 0)] * 2,
        crs="EPSG:4674",
    )


def _patch_seat(monkeypatch, mock_seat):
    mod = importlib.import_module("geobr.read_municipal_seat")
    monkeypatch.setattr(mod, "read_municipal_seat", lambda **k: mock_seat)


def test_lookup_by_code(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    out = lookup_muni(code_muni=3304557, year=2010, verbose=True)
    assert len(out) == 1
    assert isinstance(out, pd.DataFrame)
    assert out.iloc[0]["name_muni"].lower() == "rio de janeiro"


def test_lookup_by_name(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    out = lookup_muni(name_muni="Rio de Janero", year=2010, verbose=True)
    assert len(out) == 1
    assert isinstance(out, pd.DataFrame)
    assert out.iloc[0]["name_muni"].lower() == "rio de janeiro"


def test_lookup_muni_all(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    out = lookup_muni(code_muni="all", year=2010, verbose=True)
    assert len(out) == len(mock_seat)


def test_lookup_requires_input(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    with pytest.raises(ValueError):
        lookup_muni(year=2010, name_muni=None, code_muni=None)


def test_mutual_exclusion(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    with pytest.raises(ValueError, match="cannot be used"):
        lookup_muni(name_muni="Rio", code_muni=3304557)


def test_lookup_no_code_found(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    with pytest.raises(ValueError, match="valid municipality code"):
        lookup_muni(year=2010, code_muni=9999999)


def test_lookup_no_name_found(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    with pytest.raises(ValueError, match="valid municipality name"):
        lookup_muni(year=2010, name_muni='Brasília')


def test_lookup_fuzzy_name_with_apostrophe(monkeypatch):
    # The user string is bound as a SQL parameter; an apostrophe must not break
    # the DuckDB query (it does break the glue-interpolated R version).
    seat = gpd.GeoDataFrame(
        {
            "code_muni": [3548500, 3550308],
            "name_muni": ["Santa Bárbara d'Oeste", "São Paulo"],
            "abbrev_state": ["SP", "SP"],
            "code_state": [35, 35],
        },
        geometry=[Point(0, 0)] * 2,
        crs="EPSG:4674",
    )
    _patch_seat(monkeypatch, seat)
    out = lookup_muni(name_muni="Santa Barbara dOeste", year=2010)
    assert len(out) == 1
    assert out.iloc[0]["code_muni"] == 3548500
    assert "_fmt" not in out.columns


def test_lookup_fuzzy_name_returns_all_tied_homonyms(monkeypatch):
    # Several municipalities share a name (e.g. Bom Jesus in PI, RN, RS, ...).
    # A fuzzy hit must return every row tied at the best score, as the exact
    # match path already does, instead of silently picking one.
    seat = gpd.GeoDataFrame(
        {
            "code_muni": [2201919, 2401909, 4302204],
            "name_muni": ["Bom Jesus", "Bom Jesus", "Bom Jesus do Sul"],
            "abbrev_state": ["PI", "RN", "RS"],
            "code_state": [22, 24, 43],
        },
        geometry=[Point(0, 0)] * 3,
        crs="EPSG:4674",
    )
    _patch_seat(monkeypatch, seat)
    out = lookup_muni(name_muni="Bom Jesuss", year=2010)
    assert sorted(out["code_muni"]) == [2201919, 2401909]


@pytest.mark.parametrize("code", [330455, "330455", " 330455 "])
def test_lookup_by_6_digit_code(mock_seat, monkeypatch, code):
    # DATASUS systems (SIM, SIH, SINASC) store municipality codes without the
    # IBGE check digit. The 6-digit prefix is unique, so it maps to one row.
    _patch_seat(monkeypatch, mock_seat)
    out = lookup_muni(code_muni=code, year=2010)
    assert len(out) == 1
    assert out.iloc[0]["code_muni"] == 3304557


def test_lookup_6_digit_code_with_float_codes(mock_seat, monkeypatch):
    # The published municipal seat data stores code_muni as float.
    seat = mock_seat.assign(code_muni=mock_seat["code_muni"].astype(float))
    _patch_seat(monkeypatch, seat)
    out = lookup_muni(code_muni=355030, year=2010)
    assert out.iloc[0]["name_muni"] == "São Paulo"


def test_lookup_no_6_digit_code_found(mock_seat, monkeypatch):
    _patch_seat(monkeypatch, mock_seat)
    with pytest.raises(ValueError, match="valid municipality code"):
        lookup_muni(year=2010, code_muni=999999)


@pytest.mark.parametrize("code", [33045, 33045570, "33a455"])
def test_lookup_rejects_malformed_code(mock_seat, monkeypatch, code):
    _patch_seat(monkeypatch, mock_seat)
    with pytest.raises(ValueError, match="valid municipality code"):
        lookup_muni(year=2010, code_muni=code)


@pytest.mark.parametrize("code", [3304557.0, 330455.0])
def test_lookup_accepts_integral_float_code(mock_seat, monkeypatch, code):
    # int(3304557.0) worked before 6-digit support; keep accepting it.
    _patch_seat(monkeypatch, mock_seat)
    out = lookup_muni(code_muni=code, year=2010)
    assert out.iloc[0]["code_muni"] == 3304557


def test_lookup_ambiguous_6_digit_code(monkeypatch):
    # Historical years (e.g. 1872) use synthetic codes such as 1599902 and
    # 1599903 that share a 6-digit prefix; a 6-digit lookup must not guess.
    seat = gpd.GeoDataFrame(
        {
            "code_muni": [1599902.0, 1599903.0],
            "name_muni": ["Macapá", "Masagão"],
            "abbrev_state": ["PA", "PA"],
            "code_state": [15, 15],
        },
        geometry=[Point(0, 0)] * 2,
        crs="EPSG:4674",
    )
    _patch_seat(monkeypatch, seat)
    with pytest.raises(ValueError, match="matches 2 municipalities in 1872"):
        lookup_muni(year=1872, code_muni=159990)
    out = lookup_muni(year=1872, code_muni=1599903)
    assert out.iloc[0]["name_muni"] == "Masagão"
