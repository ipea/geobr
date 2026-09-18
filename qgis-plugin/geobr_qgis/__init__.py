"""geobr for QGIS - official spatial data sets of Brazil as Processing algorithms.

The plugin folder is named ``geobr_qgis`` rather than ``geobr`` on purpose: QGIS
prepends the plugins directory to ``sys.path`` and imports the folder as a
top-level module, so a folder named ``geobr`` would shadow the geobr library
itself and neither would load.
"""

import importlib.util
import os
import sys

from qgis.core import Qgis, QgsApplication, QgsMessageLog

from .algorithm import PIP_COMMAND, PIP_COMMAND_DUCKDB

#: Modules geobr needs that QGIS does not ship. QGIS already provides
#: geopandas, shapely, pyarrow, pandas and requests. The two come from
#: different places: ``geobr`` is a pip install into QGIS's Python, ``duckdb``
#: is listed in ``requirements.txt`` for the qpip plugin to install.
DEPENDENCIES = ("geobr", "duckdb")


def qpip_site_packages():
    """Where qpip installs the packages listed in ``requirements.txt``.

    Mirrors qpip's own layout - ``<profile>/python/dependencies/<major.minor>``,
    one directory per Python version so a profile shared between QGIS builds
    does not mix ABIs.
    """
    return os.path.join(
        QgsApplication.qgisSettingsDirPath(),
        "python",
        "dependencies",
        f"{sys.version_info.major}.{sys.version_info.minor}",
    )


def add_qpip_path():
    """Put qpip's dependency directory on ``sys.path`` unless qpip already has.

    qpip does this itself when it loads, ahead of every other plugin - but only
    in the desktop app: it needs the GUI, so ``qgis_process`` never loads it,
    and a duckdb that qpip installed would be invisible to a headless run.
    Inserted at the front, as qpip does, so both paths agree on which duckdb
    they import. Returns the directory, or ``None`` if it does not exist yet.
    """
    path = qpip_site_packages()
    if not os.path.isdir(path):
        return None
    if path not in sys.path:
        sys.path.insert(0, path)
    return path


def missing_message(missing):
    """One instruction per missing piece, since each comes from a different place."""
    parts = []
    if "geobr" in missing:
        parts.append(f"the geobr Python package (install with:  {PIP_COMMAND} )")
    if "duckdb" in missing:
        parts.append(
            "duckdb, which the qpip plugin installs from geobr's requirements.txt "
            "(install and enable qpip from the Plugin Manager, or run:  "
            f"{PIP_COMMAND_DUCKDB} )"
        )
    return "geobr needs " + " and ".join(parts) + " - then restart QGIS."


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
        add_qpip_path()

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
            message = missing_message(missing)
            # Logged as well as shown, so the instruction survives the banner.
            QgsMessageLog.logMessage(message, "geobr", Qgis.MessageLevel.Warning)
            if self.iface is not None:
                self.iface.messageBar().pushMessage(
                    "geobr", message, level=Qgis.MessageLevel.Warning, duration=15
                )

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
