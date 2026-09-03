"""Discovery of geobr's readers, and the Processing provider that exposes them.

Discovery reads geobr's *source* rather than importing it. Importing the package
costs ~4 s warm and up to ~29 s cold, because it pulls in pandas, geopandas and
duckdb - a price QGIS would pay at every launch, for every user, whether or not
a geobr algorithm is ever run. ``find_spec`` locates the package without
executing it and ``ast`` reads the signatures straight from the files, which
costs ~0.5 s and still derives everything from geobr itself, so a new reader
appears in QGIS with no change here.
"""

from __future__ import annotations

import ast
import importlib.util
import os
from typing import NamedTuple

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithm import REQUIRED, GeobrAlgorithm


class ReaderSpec(NamedTuple):
    """What the algorithm needs to know about one geobr reader."""

    name: str
    params: tuple  # ((argument_name, default_or_REQUIRED), ...)
    doc: str


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


def discover_readers():
    """Return a ReaderSpec per exported geobr reader, or [] if geobr is absent."""
    package_dir = _package_dir()
    if package_dir is None:
        return []
    try:
        wanted = _exported_readers(package_dir)
    except (OSError, SyntaxError):
        return []
    if not wanted:
        return []

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
                    doc=ast.get_docstring(node) or "",
                )
    return [found[name] for name in sorted(found)]


class GeobrProvider(QgsProcessingProvider):
    """Exposes every geobr reader as a Processing algorithm."""

    def id(self):
        # Kept as "geobr" so algorithm ids read `geobr:read_state`, even though
        # the plugin folder must be named differently to avoid shadowing the
        # geobr library on sys.path.
        return "geobr"

    def name(self):
        return "geobr"

    def longName(self):
        return "geobr - official spatial data sets of Brazil"

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))

    def loadAlgorithms(self):
        for spec in discover_readers():
            self.addAlgorithm(GeobrAlgorithm(spec))
