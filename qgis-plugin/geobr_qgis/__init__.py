"""geobr for QGIS - official spatial data sets of Brazil as Processing algorithms.

The plugin folder is named ``geobr_qgis`` rather than ``geobr`` on purpose: QGIS
prepends the plugins directory to ``sys.path`` and imports the folder as a
top-level module, so a folder named ``geobr`` would shadow the geobr library
itself and neither would load.
"""

import importlib.util

from qgis.core import Qgis, QgsApplication, QgsMessageLog

from .algorithm import PIP_COMMAND

#: Modules geobr needs that QGIS does not ship. QGIS already provides
#: geopandas, shapely, pyarrow, pandas and requests.
DEPENDENCIES = ("geobr", "duckdb", "rapidfuzz")


def classFactory(iface):
    """Entry point called by QGIS."""
    return GeobrPlugin(iface)


def missing_dependencies():
    """Names of required modules QGIS cannot see.

    Uses ``find_spec`` so nothing is imported: this runs during QGIS startup,
    and importing geobr's stack there would cost seconds.
    """
    missing = []
    for module in DEPENDENCIES:
        try:
            if importlib.util.find_spec(module) is None:
                missing.append(module)
        except (ImportError, ValueError):
            missing.append(module)
    return missing


class GeobrPlugin:
    """Registers the geobr Processing provider."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        """Register the provider.

        QGIS calls this instead of ``initGui`` when running without a GUI, which
        is how ``qgis_process`` loads a plugin that declares
        ``hasProcessingProvider=yes``. Everything the algorithms need lives here;
        ``initGui`` only adds the parts that require a window.
        """
        from .provider import GeobrProvider

        if self.provider is None:
            self.provider = GeobrProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        missing = missing_dependencies()
        if missing:
            message = (
                f"geobr needs {', '.join(missing)}, which QGIS cannot find. "
                f"Install with:  {PIP_COMMAND}  - then restart QGIS."
            )
            # Logged as well as shown, so the instruction survives the banner.
            QgsMessageLog.logMessage(message, "geobr", Qgis.Warning)
            if self.iface is not None:
                self.iface.messageBar().pushMessage(
                    "geobr", message, level=Qgis.Warning, duration=15
                )

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
