"""The Processing provider that exposes geobr's readers as algorithms.

Reader discovery itself lives in ``discovery.py``, which imports nothing from
``qgis`` so it can be tested without a QGIS runtime.
"""

from __future__ import annotations

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithm import GeobrAlgorithm
from .discovery import discover_readers


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
