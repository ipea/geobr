"""Discovery of geobr's readers, by reading its source rather than importing it.

Importing geobr costs ~4 s warm and up to ~29 s cold, because it pulls in pandas,
geopandas and duckdb - a price QGIS would pay at every launch, for every user,
whether or not a geobr algorithm is ever run. ``find_spec`` locates the package
without executing it and ``ast`` reads the signatures straight from the files,
which costs ~0.5 s and still derives everything from geobr itself, so a new
reader appears in QGIS with no change here.

Nothing in this module imports ``qgis``. That is deliberate: it is the only part
of the plugin that is coupled to geobr's *source shape*, so it is the part most
likely to break when geobr changes, and it must be testable without a QGIS
runtime. See ``qgis-plugin/tests/test_discovery.py``.
"""

from __future__ import annotations

import ast
import html
import importlib.util
import os
import re
import textwrap
from typing import NamedTuple


class _Required:
    """Sentinel for a reader argument that has no default."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "REQUIRED"


REQUIRED = _Required()


class ReaderSpec(NamedTuple):
    """What the algorithm needs to know about one geobr reader."""

    name: str
    params: tuple  # ((argument_name, default_or_REQUIRED), ...)
    doc: str


#: Readers deliberately not exposed, despite being in geobr's ``__all__``.
#: ``read_comparable_areas`` is the only reader still on geobr's legacy gpkg
#: path, whose ``url_solver()`` calls ``requests.get()`` with no timeout - inside
#: a Processing worker thread that cannot be cancelled mid-request, a hang there
#: lasts until QGIS is restarted. geobr's own docstring describes that download
#: path as suspended.
_EXCLUDED_READERS = {"read_comparable_areas"}


# geobr infers the filter column from the value's shape. Anything it cannot
# match falls through to an *unfiltered* result rather than an error, so the
# accepted forms are checked before the call.
#
# Exactly three digits is excluded because geobr can never match it:
# read_filter_parquet_relation tests for 2 digits, then 7, then `> 3`, so a
# 3-digit value reaches the bare `return rel` and yields the whole country.
# Four or more digits stays legal - those are how code_meso, code_micro,
# code_immediate and code_weighting are filtered.
CODE_RE = re.compile(r"^(all|[A-Za-z]{2}|\d{1,2}|\d{4,})$")


def code_shape(part):
    """Which column geobr will dispatch this value to."""
    if part.isdigit():
        if len(part) <= 2:
            return "a two-digit state code"
        if len(part) == 7:
            return "a seven-digit municipality code"
        return f"a {len(part)}-digit code"
    return "a state abbreviation"


def validate_codes(arg, value):
    """Check a code filter before geobr silently mis-applies it.

    ``read_filter_parquet_relation`` returns the *unfiltered* relation when a
    value matches none of its patterns, so a typo would otherwise produce a
    whole-country layer where one state was asked for.

    It also picks the column from ``codes[0]`` alone and interpolates the rest
    into that column's ``WHERE``, so a mixed list like ``RJ,33`` silently
    returns only RJ. Such a list is rejected here rather than under-filtered
    there.

    Returns the value to hand to geobr - a bare string for one code, a list for
    several. Raises ``ValueError`` with a message meant for the user; the
    caller turns that into a ``QgsProcessingException``.

    This lives here, rather than beside its caller, so it can be tested without
    a QGIS runtime.
    """
    parts = [p.strip() for p in value.split(",") if p.strip()]
    for part in parts:
        if not CODE_RE.match(part):
            raise ValueError(
                f"Invalid value {part!r} for '{arg}'. Use 'all', a two-letter "
                "state abbreviation (RJ), or a numeric IBGE code (33, "
                "3304557). Separate several codes with commas."
            )

    shapes = {code_shape(p) for p in parts if p != "all"}
    if len(shapes) > 1:
        raise ValueError(
            f"Mixed code types in '{arg}': {value!r}. geobr filters on a "
            "single column, chosen from the first value, so a mixed list "
            "would silently return only part of what you asked for. Use "
            f"one type at a time - here it saw {', '.join(sorted(shapes))}."
        )
    return parts[0] if len(parts) == 1 else parts


def _package_dir():
    """Locate the installed geobr package without importing it."""
    try:
        spec = importlib.util.find_spec("geobr")
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    return os.path.dirname(spec.origin)


def _parse(path):
    with open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def _exported_readers(package_dir):
    """The read_* names listed in geobr's own ``__all__``."""
    tree = _parse(os.path.join(package_dir, "__init__.py"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == "__all__" for t in node.targets):
            continue
        names = []
        for element in node.value.elts:
            try:
                names.append(ast.literal_eval(element))
            except ValueError:
                continue
        return {n for n in names if n.startswith("read_")}
    return set()


def _signature(node):
    """Argument names and literal defaults, straight from the AST.

    Annotations are deliberately ignored: at least one reader is annotated
    ``year: InterruptedError``, so only the name and the default are trustworthy.
    """
    def literal(node_):
        try:
            return ast.literal_eval(node_)
        except ValueError:
            # A non-literal default cannot be represented; treat it as required.
            return REQUIRED

    names = [a.arg for a in node.args.args]
    defaults = node.args.defaults
    offset = len(names) - len(defaults)
    params = [
        (name, REQUIRED if index < offset else literal(defaults[index - offset]))
        for index, name in enumerate(names)
    ]
    # No geobr reader uses keyword-only arguments today, but discovery is meant
    # to keep working as geobr grows, and these would otherwise vanish silently.
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        params.append((arg.arg, REQUIRED if default is None else literal(default)))
    return tuple(params)


def _shared_params(package_dir):
    """geobr's shared parameter documentation blocks, read from source.

    Since geobr 2.0.0 the readers carry ``{year}``-style tokens in their
    docstrings, which a ``@docparams`` decorator replaces with the blocks in
    ``geobr/_docstrings.py`` **at import time** (``PARAMS`` there is a flat
    ``dict[str, str]`` of literals, so ``literal_eval`` is safe). Reading the
    source, as this module does, therefore sees the tokens rather than the text,
    and the substitution has to be reproduced here - see :func:`_render_doc`.

    Returns ``{}`` if the file cannot be read or is not the shape expected, so a
    future geobr that moves or restructures it degrades to plainer help text
    rather than breaking discovery.
    """
    try:
        tree = _parse(os.path.join(package_dir, "_docstrings.py"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(getattr(t, "id", None) == "PARAMS" for t in node.targets):
                continue
            params = ast.literal_eval(node.value)
            return {k: v for k, v in params.items() if isinstance(v, str)}
    except (OSError, SyntaxError, ValueError, AttributeError, TypeError):
        return {}
    return {}


def _render_doc(doc, params):
    """Substitute geobr's shared doc blocks, then format for QGIS.

    The substitution mirrors ``geobr._docstrings.docparams``: plain string
    replacement of each ``{name}`` token, with the block re-indented to wherever
    the token sits. An unrecognised token is left alone rather than raising,
    exactly as upstream does.

    The docstring arrives already cleaned by ``ast.get_docstring``, so tokens sit
    at column 0 and the block is seated at column 0 with its body indented by
    four - the same result upstream reaches by substituting into the raw
    docstring and letting the consumer clean it. Do not clean again.

    ``shortHelpString()`` is rendered as rich text, so the numpydoc layout
    (hanging indents, hard line breaks) would otherwise collapse into a single
    run-on paragraph. Escaping and wrapping in ``<pre>`` preserves it.
    """
    for name, block in params.items():
        token = "{" + name + "}"
        if token not in doc:
            continue
        indent = "    "
        for line in doc.splitlines():
            if line.strip() == token:
                indent = line[: len(line) - len(line.lstrip())]
                break
        doc = doc.replace(token, textwrap.indent(block, indent).lstrip())

    return f"<pre>{html.escape(doc)}</pre>" if doc else ""


def discover_readers(package_dir=None):
    """Return a ReaderSpec per exported geobr reader, or [] if geobr is absent.

    ``package_dir`` defaults to the installed geobr, which is what QGIS wants.
    The tests pass an explicit path instead, so they never depend on geobr being
    installed in the runner.
    """
    if package_dir is None:
        package_dir = _package_dir()
    if package_dir is None:
        return []
    try:
        wanted = _exported_readers(package_dir) - _EXCLUDED_READERS
    except (OSError, SyntaxError, AttributeError, TypeError):
        # AttributeError/TypeError guard the unchecked `node.value.elts` above:
        # `__all__` is a list literal today, but a future `sorted(...)` there
        # would otherwise escape and take loadAlgorithms() down with it.
        return []
    if not wanted:
        return []

    params = _shared_params(package_dir)

    found = {}
    for filename in os.listdir(package_dir):
        if not filename.startswith("read_") or not filename.endswith(".py"):
            continue
        try:
            tree = _parse(os.path.join(package_dir, filename))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                found[node.name] = ReaderSpec(
                    name=node.name,
                    params=_signature(node),
                    doc=_render_doc(ast.get_docstring(node) or "", params),
                )
    return [found[name] for name in sorted(found)]
