"""Every ``read_*`` exposes its arguments in the same order as the R package.

geobr is one package implemented twice, so a positional call should mean the
same thing in both languages. The R signatures are the contract; this module
pins them so Python cannot drift away again.

The canonical shape is::

    read_<geography>(<year|date>, <code_*>, [extras], simplified,
                     output, show_progress, cache, verbose)

Two argument *names* differ by design and are normalised here rather than in
the source: R spells ``showProgress`` where Python spells ``show_progress``.
Defaults also differ by design (``output="sf"`` / ``"gpd"``,
``verbose=TRUE`` / ``False``), so this module checks names and order only.

Offline — signatures only, nothing is downloaded.
"""

import inspect

import pytest

import geobr

# Argument order of each exported reader in r-package/R/read_*.R, with
# `showProgress` renamed to `show_progress`. Regenerate with:
#     Rscript -e 'library(geobr); args(read_state)'
R_ARGUMENT_ORDER = {
    "read_amazon": ("year", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_biomes": ("year", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_capitals": ("year", "output", "show_progress", "cache", "verbose"),
    "read_census_tract": ("year", "code_tract", "zone", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_comparable_areas": ("start_year", "end_year", "simplified", "show_progress", "cache", "verbose"),
    "read_conservation_units": ("date", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_country": ("year", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_disaster_risk_area": ("year", "code_muni", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_favela": ("year", "code_muni", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_health_facilities": ("date", "code_muni", "output", "show_progress", "cache", "verbose"),
    "read_health_region": ("year", "code_state", "geometry_level", "macro", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_immediate_region": ("year", "code_immediate", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_indigenous_land": ("year", "code_state", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_intermediate_region": ("year", "code_intermediate", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_meso_region": ("year", "code_meso", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_metro_area": ("year", "code_state", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_micro_region": ("year", "code_micro", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_municipal_seat": ("year", "code_muni", "output", "show_progress", "cache", "verbose"),
    "read_municipality": ("year", "code_muni", "simplified", "output", "show_progress", "cache", "verbose", "keep_areas_operacionais"),
    "read_neighborhood": ("year", "code_muni", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_polling_places": ("year", "code_muni", "output", "show_progress", "cache", "verbose"),
    "read_pop_arrangements": ("year", "code_state", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_quilombola_land": ("date", "code_state", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_region": ("year", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_schools": ("year", "code_muni", "output", "show_progress", "cache", "verbose"),
    "read_semiarid": ("year", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_state": ("year", "code_state", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_statistical_grid": ("year", "code_muni", "output", "show_progress", "cache", "verbose"),
    "read_urban_area": ("year", "code_muni", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_urban_concentrations": ("year", "code_state", "simplified", "output", "show_progress", "cache", "verbose"),
    "read_weighting_area": ("year", "code_weighting", "simplified", "output", "show_progress", "cache", "verbose"),
}

CASES = sorted(R_ARGUMENT_ORDER.items())
IDS = [name for name, _ in CASES]


def test_every_exported_reader_is_pinned():
    """No reader escapes the table above."""
    exported = {
        name
        for name, obj in vars(geobr).items()
        if name.startswith("read_") and inspect.isfunction(obj)
    }
    assert exported == set(R_ARGUMENT_ORDER)


@pytest.mark.parametrize("name,expected", CASES, ids=IDS)
def test_argument_order_matches_r(name, expected):
    actual = tuple(inspect.signature(getattr(geobr, name)).parameters)
    assert actual == expected


@pytest.mark.parametrize("name,expected", CASES, ids=IDS)
def test_no_keyword_only_or_var_arguments(name, expected):
    """Positional calls must stay portable between the two packages."""
    for param in inspect.signature(getattr(geobr, name)).parameters.values():
        assert param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD, (
            f"{name}.{param.name} is {param.kind}, which R cannot mirror"
        )
