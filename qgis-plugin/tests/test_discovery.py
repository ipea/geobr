"""The plugin derives its Processing parameters from geobr's source by ``ast``.

That coupling is invisible at runtime - a geobr release can change the source
shape and the plugin will keep loading while quietly producing wrong parameters
or unreadable help. geobr 2.0.0 did exactly that: it moved shared parameter docs
into an import-time decorator, and every algorithm's help panel started showing
literal ``{year}`` tokens.

These tests are the standing check on that coupling. They import nothing from
``qgis`` and need no geobr install - they read ``python-package/geobr`` directly,
so a geobr change fails this job.
"""

import re

import pytest

import discovery

# 31 read_* names in geobr's __all__, minus the one deliberate exclusion.
EXPECTED_READER_COUNT = 30

TOKEN = re.compile(r"\{[a-z_]+\}")


def test_discovery_is_not_empty(specs):
    """Discovery finds every exported reader.

    This assertion is load-bearing and must come first. `discover_readers`
    returns [] when it cannot locate the package, so without a count check
    every parametrised test below would collect zero cases and pass green - a
    suite that cannot fail.
    """
    assert len(specs) == EXPECTED_READER_COUNT


def test_no_unsubstituted_tokens(specs):
    """No `{year}`-style token survives into the QGIS help panel.

    geobr's `@docparams` substitutes these at import time; discovery reads the
    source and so must reproduce the substitution itself.
    """
    offenders = {spec.name: TOKEN.findall(spec.doc) for spec in specs}
    offenders = {name: found for name, found in offenders.items() if found}
    assert not offenders


def test_every_reader_has_help(specs):
    assert all(spec.doc.strip() for spec in specs)


def test_help_is_html(by_name):
    """`shortHelpString()` is rendered as rich text, so numpydoc needs wrapping."""
    doc = by_name["read_state"].doc
    assert doc.startswith("<pre>") and doc.endswith("</pre>")
    # The substituted parameter block survived, and its layout with it.
    assert "year : int" in doc


@pytest.mark.parametrize(
    "reader,argument",
    [("read_census_tract", "code_tract"), ("read_statistical_grid", "code_muni")],
)
def test_required_arguments_have_no_default(by_name, reader, argument):
    params = dict(by_name[reader].params)
    assert params[argument] is discovery.REQUIRED


def test_anchor_signatures(by_name):
    """A few hand-picked shapes covering everything `_signature` must handle.

    Deliberately not a copy of geobr's full argument-order table: that contract
    already lives in `python-package/tests/test_reader_argument_order.py`, and a
    second copy here would drift.
    """
    capitals = by_name["read_capitals"].params
    assert capitals[0] == ("year", 2010)

    # A trailing argument after the shared block - easy to lose in a rewrite.
    assert by_name["read_municipality"].params[-1][0] == "keep_areas_operacionais"

    # Point geographies have nothing to simplify.
    assert "simplified" not in dict(by_name["read_schools"].params)

    # `date` (YYYYMM) readers, not `year`.
    assert by_name["read_health_facilities"].params[0][0] == "date"

    # The health-region suppression is gone: geobr 2.0.0 fixed geometry_level.
    assert "geometry_level" in dict(by_name["read_health_region"].params)


def test_exclusions(by_name):
    """read_comparable_areas stays out: its download path has no timeout."""
    assert "read_comparable_areas" not in by_name


def test_missing_package_is_survivable():
    """A bad path yields no readers rather than an exception at QGIS startup."""
    assert discovery.discover_readers(package_dir="/nonexistent/geobr") == []


# -- code filter validation -------------------------------------------------
#
# geobr fails quietly here: an unmatched code returns the relation UNFILTERED
# (`_duckdb_backend.py`, the bare `return rel`), and a comma list is dispatched
# on `codes[0]` alone. Both would hand the user a wrong layer with no error, so
# these are the cases the plugin has to catch itself.


@pytest.mark.parametrize(
    "value,expected",
    [
        ("all", "all"),
        ("RJ", "RJ"),
        ("33", "33"),
        ("3304557", "3304557"),
        ("RJ,SP", ["RJ", "SP"]),
        ("33,35", ["33", "35"]),
        ("3304557,3550308", ["3304557", "3550308"]),
        ("3301", "3301"),  # 4-digit micro/meso codes are legitimate
        (" RJ , SP ", ["RJ", "SP"]),
    ],
)
def test_accepted_codes(value, expected):
    assert discovery.validate_codes("code_state", value) == expected


@pytest.mark.parametrize(
    "value,reason",
    [
        ("331", "3 digits can never match a geobr column - it returns everything"),
        ("R", "one letter is not an abbreviation"),
        ("RJ1", "not a shape geobr recognises"),
        ("RJ,33", "mixed: dispatches on 'RJ', silently returns only RJ"),
        ("33,3304557", "mixed: dispatches on '33', silently returns the state"),
    ],
)
def test_rejected_codes(value, reason):
    with pytest.raises(ValueError):
        discovery.validate_codes("code_state", value)
