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
import sys

import pytest

import discovery

# 32 read_* names in geobr 2.1.0's __all__ (read_addresses joined in 2.1.0),
# minus the one deliberate exclusion.
EXPECTED_READER_COUNT = 31

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


def test_bundle_path_is_front_inserted_once(tmp_path, monkeypatch):
    """The bundled geobr must beat a pip-installed one, and never stack up."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    vendor = tmp_path / "_vendor"
    (vendor / "geobr").mkdir(parents=True)
    (vendor / "geobr" / "__init__.py").write_text("", encoding="utf-8")

    assert discovery.add_bundle_path(str(vendor)) == str(vendor)
    assert sys.path[0] == str(vendor)
    assert discovery.add_bundle_path(str(vendor)) == str(vendor)
    assert sys.path.count(str(vendor)) == 1


def test_no_bundle_leaves_sys_path_alone(tmp_path, monkeypatch):
    """A repo checkout has no _vendor/; that is a None, not an error."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = list(sys.path)
    assert discovery.add_bundle_path(str(tmp_path / "_vendor")) is None
    assert sys.path == before


def test_dependencies_start_with_geobr():
    """The probe list is the bundle first, then geobr's own requirements."""
    assert discovery.DEPENDENCIES[0] == "geobr"
    assert "duckdb" in discovery.DEPENDENCIES


# -- code filter validation -------------------------------------------------
#
# geobr 2.1.0 raises ValueError for an unmatched code, a mixed list, or a
# filter matching no row (`_duckdb_backend.py`) - but only after downloading
# the file, and without naming the offending value. The plugin catches these
# before the download and says which value is wrong.


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


# -- layer naming -----------------------------------------------------------
#
# One algorithm class serves every reader, so without a name derived from the
# call, every run lands in the QGIS legend under the same name and a second run
# cannot be told from the first. The geography comes from the literal each
# reader passes to `read_geobr_v2`, which is what `select_metadata_v2` matches
# against the metadata's `geo` column - the only one of the three copies geobr
# carries that cannot drift, because it is the one the reader calls with.

#: The readers with no single geography literal of their own, which fall back to
#: their own name. Small and individually justified, unlike a full geography
#: table - see the tests below for why each is here.
STEM_FALLBACKS = {"read_capitals", "read_pop_arrangements", "read_urban_concentrations"}


def _calls(spec):
    """Every distinct reader call the plugin can produce, as `_collect` builds it.

    A year is always present by the time `layer_name` sees the kwargs: it is
    either required (and `_missing_year` rejects a blank one before anything is
    downloaded) or defaulted, and `_collect` always reads it as an int.
    """
    base = {}
    for arg, _ in spec.params:
        if arg in ("year", "date"):
            base[arg] = 202504 if arg == "date" else 2020

    enums = [(arg, discovery.ENUM_ARGS[arg]) for arg, _ in spec.params
             if arg in discovery.ENUM_ARGS]
    assert len(enums) <= 1, f"{spec.name} takes two enum arguments; widen this"
    if not enums:
        return [base]
    arg, values = enums[0]
    return [dict(base, **{arg: value}) for value in values]


def test_every_reader_has_a_geography(specs):
    assert all(spec.geo for spec in specs)


def test_geography_shape(specs):
    """A geography read from geobr matches how the metadata records it.

    `download_metadata_v2` derives `geo` from the asset filename as `^([^_]+)`,
    so a geography containing an underscore could never match a metadata row -
    it would mean the extraction picked up the wrong literal. The readers that
    deliberately fall back to their own name are the exception.
    """
    for spec in specs:
        assert re.fullmatch(r"[a-z0-9_]+", spec.geo), spec.name
        if spec.name not in STEM_FALLBACKS:
            assert "_" not in spec.geo, spec.name


@pytest.mark.parametrize(
    "reader,geo",
    [
        ("read_favela", "favelas"),
        ("read_polling_places", "pollingplaces"),
        ("read_quilombola_land", "quilombolalands"),
    ],
)
def test_keyword_geography_is_extracted(by_name, reader, geo):
    """These three pass the geography by keyword; the other 26 pass it first.

    An extraction rewritten as positional-only still finds 26 of 29 and looks
    fine, so this is the test that has to catch it.
    """
    assert by_name[reader].geo == geo


@pytest.mark.parametrize(
    "reader,geo",
    [("read_indigenous_land", "indigenouslands"), ("read_metro_area", "metroarea")],
)
def test_positional_geography_is_extracted(by_name, reader, geo):
    """Anchored on the two that disagree with `_GEO_LOADERS`.

    `_duckdb_backend._GEO_LOADERS` is a second copy of this mapping and says
    `indigenousland` / `metropolitanarea`, which match no release asset. The
    readers are right. This test is what fails if someone ever "simplifies" the
    plugin by reading that table instead.
    """
    assert by_name[reader].geo == geo


def test_capitals_falls_back_to_reader_stem(by_name):
    """read_capitals composes read_municipal_seat rather than calling the pipeline.

    It has no geography literal to find, and naming it `municipalseats` would be
    a lie about which reader produced the layer.
    """
    assert by_name["read_capitals"].geo == "capitals"


def test_aliased_geographies_are_separated(by_name):
    """Two readers, one asset, two different layers.

    Both pass `poparrangements`, and the release ships a single year of it, so
    they would always collide - the exact complaint this naming answers. They
    are not the same layer: read_pop_arrangements keeps only rows with a
    non-null `code_pop_arrangement`.
    """
    assert by_name["read_pop_arrangements"].geo == "pop_arrangements"
    assert by_name["read_urban_concentrations"].geo == "urban_concentrations"


def test_layer_names_are_unique(specs):
    """No two reader calls can produce the same layer name. The whole point.

    Expanded over every `zone` / `geometry_level` choice, because those select a
    different geometry under one geography: drop either from the name and two
    unrelated layers collide again.
    """
    names = [discovery.layer_name(s.geo, call) for s in specs for call in _calls(s)]
    assert len(names) == len(set(names))
    assert len(names) > len(specs)  # the enum readers really did expand


def test_layer_names_are_valid_identifiers(specs):
    """Safe as a QGIS layer name and as a GeoPackage table name.

    Never starts with a digit, no quoting or escaping needed, and never the
    `gpkg_` prefix the GeoPackage spec reserves.
    """
    for spec in specs:
        for call in _calls(spec):
            name = discovery.layer_name(spec.geo, call)
            assert re.fullmatch(r"[a-z][a-z0-9_]*", name), name
            assert not name.startswith("gpkg_"), name


@pytest.mark.parametrize(
    "geo,kwargs,expected",
    [
        ("municipalities", {"year": 2020}, "municipalities_2020"),
        # `date` readers carry YYYYMM, matching the asset name.
        ("healthfacilities", {"date": 202504}, "healthfacilities_202504"),
        ("censustracts", {"year": 2000, "zone": "urban"}, "censustracts_2000_urban"),
        ("censustracts", {"year": 2000, "zone": "rural"}, "censustracts_2000_rural"),
        (
            "healthregions",
            {"year": 2013, "geometry_level": "municipality"},
            "healthregions_2013_municipality",
        ),
        (
            "healthregions",
            {"year": 2013, "geometry_level": "macro"},
            "healthregions_2013_macro",
        ),
        # Unreachable through the algorithm, but the name must stay usable.
        ("states", {}, "states"),
    ],
)
def test_layer_name(geo, kwargs, expected):
    assert discovery.layer_name(geo, kwargs) == expected


def test_reader_spec_fields():
    """`geo` and `dataset` are appended and defaulted, so positional construction still works."""
    assert discovery.ReaderSpec._fields == ("name", "params", "doc", "geo", "dataset")
    assert discovery.ReaderSpec("read_x", (), "").geo == ""
    assert discovery.ReaderSpec("read_x", (), "").dataset == ""


# --- available years --------------------------------------------------------


def test_dataset_is_the_metadata_geography(specs, by_name):
    """`dataset` is what geobr's metadata is keyed by: unrenamed, even for aliases."""
    for spec in specs:
        assert spec.dataset, spec.name
    # The alias pair keeps geobr's name here while `geo` was split apart.
    assert by_name["read_pop_arrangements"].dataset == "poparrangements"
    assert by_name["read_urban_concentrations"].dataset == "poparrangements"
    assert by_name["read_pop_arrangements"].geo != by_name["read_urban_concentrations"].geo
    # Everywhere else the two agree.
    assert all(
        spec.dataset == spec.geo
        for spec in specs
        if spec.name not in ("read_pop_arrangements", "read_urban_concentrations")
    )


def test_available_years_from_metadata_rows():
    """The shape `download_metadata_v2()` yields: floats, NaN for undated assets."""
    nan = float("nan")
    rows = [
        ("states", 2020.0),
        ("states", 2025.0),
        ("states", 2020.0),  # the simplified twin of the same year
        ("healthfacilities", 202604.0),
        ("healthfacilities", 202504.0),
        ("br", nan),
        ("metadata", None),
    ]
    assert discovery.available_years(rows) == {
        "states": [2020, 2025],
        "healthfacilities": [202504, 202604],
    }


def test_available_years_of_nothing():
    assert discovery.available_years([]) == {}


@pytest.mark.parametrize(
    "arg,expected",
    [
        # The one override: the argument name alone reads as a download mode
        # rather than as a choice of geometry.
        ("simplified", "Simplified geometry"),
        # Everything else stays mechanical, so a new geobr argument needs no
        # change here.
        ("year", "Year"),
        ("date", "Date"),
        ("code_state", "Code state"),
        ("geometry_level", "Geometry level"),
        ("zone", "Zone"),
    ],
)
def test_parameter_label(arg, expected):
    assert discovery.parameter_label(arg) == expected


def test_every_exposed_argument_has_a_label(specs):
    """No reader argument renders blank or keeps an underscore in the UI."""
    for spec in specs:
        for arg, _ in spec.params:
            label = discovery.parameter_label(arg)
            assert label and "_" not in label, (spec.name, arg, label)


def test_labels_only_override_real_arguments(specs):
    """A typo in LABELS would silently never apply; catch it here instead."""
    declared = {arg for spec in specs for arg, _ in spec.params}
    assert set(discovery.LABELS) <= declared, set(discovery.LABELS) - declared
