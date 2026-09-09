"""Point-geometry readers expose no `simplified` argument.

There is nothing to simplify in a point layer, so these readers match the R
package: no `simplified` in the signature, and `simplified=False` hardcoded on
the way into the shared pipeline.

Offline — `read_geobr_v2` is monkeypatched, nothing is downloaded.
"""

import importlib
import inspect

import pytest

import geobr

# (reader name, kwargs that satisfy its required arguments)
POINT_READERS = [
    ("read_municipal_seat", {"year": 2010}),
    ("read_schools", {"year": 2020}),
    ("read_health_facilities", {"date": 202004}),
    ("read_polling_places", {"year": 2022}),
    ("read_statistical_grid", {"year": 2010, "code_muni": "AP"}),
]

IDS = [name for name, _ in POINT_READERS]


@pytest.mark.parametrize("name,kwargs", POINT_READERS, ids=IDS)
def test_no_simplified_argument(name, kwargs):
    params = inspect.signature(getattr(geobr, name)).parameters
    assert "simplified" not in params


@pytest.mark.parametrize("name,kwargs", POINT_READERS, ids=IDS)
def test_rejects_simplified(name, kwargs):
    with pytest.raises(TypeError):
        getattr(geobr, name)(**kwargs, simplified=True)


@pytest.mark.parametrize("name,kwargs", POINT_READERS, ids=IDS)
def test_passes_simplified_false_downstream(name, kwargs, monkeypatch):
    captured = {}

    def spy(*args, **kw):
        captured.update(kw)
        return "sentinel"

    # `geobr.read_schools` is the function, not the module — resolve the
    # module explicitly, as tests/test_lookup_muni.py does.
    mod = importlib.import_module(f"geobr.{name}")
    monkeypatch.setattr(mod, "read_geobr_v2", spy)

    assert getattr(geobr, name)(**kwargs) == "sentinel"
    assert captured["simplified"] is False
