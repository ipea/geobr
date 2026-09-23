"""Failure branches of `url_solver`.

Pins the behaviour introduced by the Bandit cleanup: the mirror probe has a
timeout (B113), it catches `requests.RequestException` instead of a bare
`except` (so it no longer swallows `KeyboardInterrupt`), and the failure is
logged at DEBUG instead of disappearing (B112). Requests are monkeypatched, so
these tests never touch the network.

The success path and the `_download_file` branches are already covered by
`test_utils.py` / `test_utils_v2.py`; only the error handling added here was
untested before.
"""

import logging

import pytest
import requests

from geobr import utils
from geobr.utils import url_solver


def test_url_solver_times_out_catches_and_raises(monkeypatch, caplog):
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(utils.requests, "get", fake_get)
    with caplog.at_level(logging.DEBUG, logger="geobr.utils"):
        with pytest.raises(ConnectionError, match="No mirrors are active"):
            url_solver("https://primary.invalid/x.parquet")

    assert seen.get("timeout") == 60
    assert any("failed" in record.getMessage() for record in caplog.records)


def test_url_solver_does_not_swallow_keyboard_interrupt(monkeypatch):
    def fake_get(url, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(utils.requests, "get", fake_get)
    with pytest.raises(KeyboardInterrupt):
        url_solver("https://primary.invalid/x.parquet")
