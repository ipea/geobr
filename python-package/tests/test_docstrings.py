"""Guard the shared parameter docs in geobr._docstrings.

These run offline: they only inspect ``__doc__`` after import-time
substitution, so they need no network marker.
"""

import inspect
import re

import pytest

import geobr
from geobr._docstrings import PARAMS

TOKEN = re.compile(r"\{[a-z_]+\}")

READERS = sorted(
    (name, obj)
    for name, obj in vars(geobr).items()
    if name.startswith("read_") and inspect.isfunction(obj)
)


def test_readers_were_collected():
    assert len(READERS) >= 30


@pytest.mark.parametrize("name,func", READERS, ids=[n for n, _ in READERS])
def test_no_unsubstituted_tokens(name, func):
    """Every {token} in a reader docstring resolves to a PARAMS entry."""
    assert func.__doc__, f"{name} has no docstring"
    leftover = TOKEN.findall(func.__doc__)
    assert not leftover, f"{name} has unsubstituted tokens: {leftover}"


@pytest.mark.parametrize("name,func", READERS, ids=[n for n, _ in READERS])
def test_every_argument_is_documented(name, func):
    """The numpydoc Parameters section covers every argument, by name."""
    doc = func.__doc__
    assert "Parameters" in doc, f"{name} has no Parameters section"
    for arg in inspect.signature(func).parameters:
        assert re.search(rf"^\s*{re.escape(arg)} : ", doc, re.MULTILINE), (
            f"{name} does not document argument {arg!r}"
        )


def test_shared_blocks_are_wellformed():
    """Each PARAMS entry is a numpydoc block: unindented name, indented body."""
    for key, block in PARAMS.items():
        head, *body = block.splitlines()
        assert head.startswith(f"{key} : "), f"{key}: bad header {head!r}"
        assert body, f"{key}: no description"
        assert all(
            line.startswith("    ") for line in body
        ), f"{key}: description lines must be indented 4 spaces"


def test_docparams_tolerates_literal_braces():
    """Literal braces outside a known token are left alone, not formatted."""
    from geobr._docstrings import docparams

    @docparams
    def f():
        r"""Summary with \doi{10.1590/0101-416147182phe}{Philipp Ehrl}.

        Parameters
        ----------
        {year}
        """

    assert "10.1590/0101-416147182phe" in f.__doc__
    assert "year : int" in f.__doc__


def test_docparams_handles_missing_docstring():
    """No AttributeError under `python -OO`, where __doc__ is None."""
    from geobr._docstrings import docparams

    def g():
        pass

    g.__doc__ = None
    assert docparams(g) is g
