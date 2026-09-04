"""Shared parameter documentation for the ``read_*`` functions.

This is the Python counterpart to the roxygen templates in
``r-package/man/roxygen/templates/``. Each entry below is written once and
interpolated into every reader's docstring by the :func:`docparams` decorator,
so a wording change propagates to all readers at once.

Substitution happens at **import time**, which means the completed text is
visible to ``help()``, IDE hover, Jupyter ``?``, and any documentation
generator that reads ``__doc__``.

The text here cannot be shared verbatim with the R templates. The two packages
deliberately differ on ``verbose`` (``TRUE`` in R, ``False`` in Python) and on
``output`` (``"sf"`` vs ``"gpd"``), and Python names the progress argument
``show_progress`` rather than ``showProgress``. Keep the R templates and this
file in sync by hand, adapting rather than copying.

Usage
-----
Reference a parameter by wrapping its name in braces on a line of its own, at
the indentation level of the numpydoc ``Parameters`` section::

    @docparams
    def read_biomes(year, simplified=True, ...):
        '''Download official Brazilian biomes data (IBGE).

        Parameters
        ----------
        {year}
        {simplified}
        '''
"""

from __future__ import annotations

import textwrap

__all__ = ["docparams", "PARAMS"]


PARAMS = {
    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------
    "year": """\
year : int
    Year of the data in ``YYYY`` format.""",
    "date": """\
date : int
    Date of the data in ``YYYYMM`` format.""",
    "start_year": """\
start_year : int, default 1970
    Start year of the period, in ``YYYY`` format.""",
    "end_year": """\
end_year : int, default 2010
    End year of the period, in ``YYYY`` format.""",
    # ------------------------------------------------------------------
    # Geography codes
    # ------------------------------------------------------------------
    "code_muni": """\
code_muni : int, str or list, default "all"
    The 7-digit code of a municipality. If ``code_muni="all"`` (the default),
    the function downloads all the data available in the country.
    Alternatively, if a two-digit state code or a two-letter uppercase
    abbreviation of a state is passed (e.g. ``33`` or ``"RJ"``), all data of
    that state are downloaded. Municipality codes can be consulted with
    ``geobr.lookup_muni()``.""",
    "code_state": """\
code_state : int, str or list, default "all"
    The two-digit code of a state or a two-letter uppercase abbreviation
    (e.g. ``33`` or ``"RJ"``). If ``code_state="all"`` (the default), the
    function downloads all states.""",
    "code_immediate": """\
code_immediate : int, str or list, default "all"
    The 6-digit code of an immediate region. If the two-digit code or a
    two-letter uppercase abbreviation of a state is passed (e.g. ``33`` or
    ``"RJ"``), the function will load all immediate regions of that state. If
    ``code_immediate="all"`` (the default), the function downloads all
    immediate regions of the country.""",
    # NOTE: the Python signature spells this `code_intermadiate`; the R package
    # uses `code_intermediate`. The key matches the Python signature.
    "code_intermadiate": """\
code_intermadiate : int, str or list, default "all"
    The 4-digit code of an intermediate region. If the two-digit code or a
    two-letter uppercase abbreviation of a state is passed (e.g. ``33`` or
    ``"RJ"``), the function will load all intermediate regions of that state.
    If ``code_intermadiate="all"`` (the default), the function downloads all
    intermediate regions of the country.""",
    "code_meso": """\
code_meso : int, str or list, default "all"
    The 4-digit code of a meso region. If the two-digit code or a two-letter
    uppercase abbreviation of a state is passed (e.g. ``33`` or ``"RJ"``), the
    function will load all meso regions of that state. If ``code_meso="all"``
    (the default), the function downloads all meso regions of the country.""",
    "code_micro": """\
code_micro : int, str or list, default "all"
    The 5-digit code of a micro region. If the two-digit code or a two-letter
    uppercase abbreviation of a state is passed (e.g. ``33`` or ``"RJ"``), the
    function will load all micro regions of that state. If
    ``code_micro="all"`` (the default), the function downloads all micro
    regions of the country.""",
    "code_tract": """\
code_tract : int, str or list, default "all"
    The 7-digit code of a municipality. If the two-digit code or a two-letter
    uppercase abbreviation of a state is passed (e.g. ``33`` or ``"RJ"``), the
    function will load all census tracts of that state. If
    ``code_tract="all"`` (the default), the function downloads all census
    tracts of the country.""",
    "code_weighting": """\
code_weighting : int, str or list, default "all"
    The 7-digit code of a municipality. If the two-digit code or a two-letter
    uppercase abbreviation of a state is passed (e.g. ``33`` or ``"RJ"``), the
    function will load all weighting areas of that state. If
    ``code_weighting="all"`` (the default), all weighting areas of the country
    are loaded.""",
    # ------------------------------------------------------------------
    # Standard options
    # ------------------------------------------------------------------
    "simplified": """\
simplified : bool, default True
    Whether the function should return the data set with 'original' spatial
    resolution or a data set with 'simplified' geometry. Defaults to ``True``.
    For spatial analysis and statistics, users should set
    ``simplified=False``. Borders have been simplified by removing vertices of
    borders while preserving topology, with a ``dTolerance`` of 100.""",
    "output": """\
output : str, default "gpd"
    Type of object returned by the function. Defaults to ``"gpd"``, which
    loads the data into memory as a geopandas ``GeoDataFrame``.
    Alternatively, ``"duckdb"`` returns a lazy spatial relation backed by
    DuckDB, and ``"arrow"`` returns an Arrow table. Both ``"duckdb"`` and
    ``"arrow"`` support out-of-memory processing of large data sets.""",
    "show_progress": """\
show_progress : bool, default True
    Whether to display a download progress bar.""",
    "cache": """\
cache : bool, default True
    Whether the function should read the data cached locally, which is faster.
    Defaults to ``True``. By default, ``geobr`` stores data files in a
    temporary directory that exists only within each Python session. If
    ``cache=False``, the function will download the data again and overwrite
    the local file.""",
    "verbose": """\
verbose : bool, default False
    If ``True``, the function prints informative messages. If ``False`` (the
    default), the function is silent.""",
    # ------------------------------------------------------------------
    # Reader-specific
    # ------------------------------------------------------------------
    "zone": """\
zone : str, default "urban"
    For census tracts before 2010, 'urban' and 'rural' census tracts are
    separate data sets. Must be either ``"urban"`` or ``"rural"``.""",
    "geometry_level": """\
geometry_level : str, default "municipality"
    Spatial level of the output geometries. Use ``"municipality"`` to return
    municipal geometries (the default), ``"micro"`` to aggregate geometries by
    health region, or ``"macro"`` to aggregate geometries by health
    macroregion.""",
    "macro": """\
macro : bool, optional
    Deprecated. Use ``geometry_level`` instead.""",
    "keep_areas_operacionais": """\
keep_areas_operacionais : bool, default False
    Whether the function should keep the polygons of Lagoa dos Patos and Lagoa
    Mirim in the state of Rio Grande do Sul (considered as *areas estaduais
    operacionais*). Defaults to ``False``.""",
}


def docparams(func):
    """Interpolate shared parameter blocks into ``func``'s docstring.

    Replaces every ``{name}`` token that matches a key of :data:`PARAMS` with
    the corresponding numpydoc block, re-indented to the token's own
    indentation. Substitution is plain string replacement rather than
    ``str.format``, so literal braces elsewhere in a docstring are safe and an
    unrecognised token is left untouched instead of raising.

    Returns the function unchanged when ``__doc__`` is absent, which is the
    case under ``python -OO``.
    """
    doc = func.__doc__
    if not doc:
        return func

    for name, block in PARAMS.items():
        token = "{" + name + "}"
        if token not in doc:
            continue
        # Re-indent the block to wherever the token sits in the docstring.
        indent = "    "
        for line in doc.splitlines():
            if line.strip() == token:
                indent = line[: len(line) - len(line.lstrip())]
                break
        doc = doc.replace(token, textwrap.indent(block, indent).lstrip())

    func.__doc__ = doc
    return func
