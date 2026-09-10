"""The single Processing algorithm that fronts every geobr reader.

One class serves every reader geobr exports. Its parameters are built from the
reader's own signature, so a reader added to geobr shows up in QGIS with no
change here.
"""

from __future__ import annotations

import os
import threading

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsSettings,
    QgsVectorFileWriter,
)

from .discovery import REQUIRED, validate_codes

PIP_COMMAND = 'python -m pip install --user "geobr>=2.0.0"'

# geobr keeps a module-global DuckDB connection and registers views by name
# ("{geo}_{year}"). Two algorithms running at once - batch mode, or a model -
# would share that connection and collide, so reader calls are serialised.
_GEOBR_LOCK = threading.Lock()

# Arguments the plugin owns rather than the user. QGIS already provides the
# equivalent: `feedback` replaces tqdm and the verbose flag, and the output
# format is fixed because we always want a GeoDataFrame to write to disk.
# `cache=True` is right under geobr 2.0.0: the cache is a per-session temp dir
# deleted when the process exits, so repeated reads inside one QGIS session are
# served from disk with no staleness risk.
# Each is passed only if the reader actually declares it - not every reader
# declares all four, and passing one that is absent would raise TypeError.
_FORCED = {"output": "gpd", "show_progress": False, "verbose": False, "cache": True}

# `macro` is deprecated in read_health_region and string-typed here, so any
# value the user types is truthy and silently overrides their geometry_level
# choice. (An untouched field is not the hazard: _collect drops empty strings
# before they reach the reader.)
_SKIP = {"macro"}

_YEAR_ARGS = {"year", "date", "start_year", "end_year"}

# Bounds for the numeric parameters. Without them the spin box opens on its
# own minimum - a large negative integer, which validates - and geobr is asked
# for an impossible year. 1872 is geobr's earliest data; `date` is YYYYMM.
_YEAR_RANGE = (1872, 9999)
_DATE_RANGE = (187201, 999912)

_ENUM_ARGS = {
    "zone": ["urban", "rural"],
    "geometry_level": ["municipality", "micro", "macro"],
}


def apply_qgis_proxy() -> None:
    """Expose QGIS's proxy settings to ``requests``.

    geobr downloads with ``requests``, which reads ``http_proxy``/``https_proxy``
    from the environment and knows nothing about QGIS's own network settings.
    Without this bridge every read fails by timeout on an institutional network.
    """
    settings = QgsSettings()
    if not settings.value("proxy/proxyEnabled", False, type=bool):
        return
    host = settings.value("proxy/proxyHost", "", type=str)
    if not host:
        return
    port = settings.value("proxy/proxyPort", "", type=str)
    user = settings.value("proxy/proxyUser", "", type=str)
    password = settings.value("proxy/proxyPassword", "", type=str)
    credentials = f"{user}:{password}@" if user else ""
    url = f"http://{credentials}{host}:{port}" if port else f"http://{credentials}{host}"
    # setdefault: never override a proxy the user set for the whole process.
    os.environ.setdefault("http_proxy", url)
    os.environ.setdefault("https_proxy", url)


class GeobrAlgorithm(QgsProcessingAlgorithm):
    """Runs one geobr reader and writes the result as a vector layer."""

    def __init__(self, spec):
        super().__init__()
        self._spec = spec
        self._exposed = []

    # -- identity ---------------------------------------------------------

    def createInstance(self):
        # Processing runs the instance this returns, so it must carry the spec.
        return GeobrAlgorithm(self._spec)

    def name(self):
        return self._spec.name

    def displayName(self):
        return self._spec.name[len("read_") :].replace("_", " ").capitalize()

    def group(self):
        return "Brazilian spatial data"

    def groupId(self):
        return "geobr"

    def shortHelpString(self):
        return self._spec.doc

    # -- parameters -------------------------------------------------------

    def initAlgorithm(self, config=None):
        self._exposed = []
        for arg, default in self._spec.params:
            if arg in _FORCED or arg in _SKIP:
                continue
            key = arg.upper()
            label = arg.replace("_", " ").capitalize()
            required = default is REQUIRED

            if arg in _YEAR_ARGS:
                low, high = _DATE_RANGE if arg == "date" else _YEAR_RANGE
                self.addParameter(
                    QgsProcessingParameterNumber(
                        key,
                        label,
                        QgsProcessingParameterNumber.Integer,
                        defaultValue=None if required else default,
                        minValue=low,
                        maxValue=high,
                    )
                )
                kind = "int"
            elif arg in _ENUM_ARGS:
                options = _ENUM_ARGS[arg]
                self.addParameter(
                    QgsProcessingParameterEnum(
                        key,
                        label,
                        options=options,
                        defaultValue=options.index(default) if default in options else 0,
                    )
                )
                kind = ("enum", options)
            elif isinstance(default, bool):
                self.addParameter(
                    QgsProcessingParameterBoolean(key, label, defaultValue=default)
                )
                kind = "bool"
            else:
                self.addParameter(
                    QgsProcessingParameterString(
                        key,
                        label,
                        defaultValue=None if required else default,
                        optional=not required,
                    )
                )
                kind = "str"

            self._exposed.append((arg, key, kind))

        self.addParameter(
            QgsProcessingParameterVectorDestination("OUTPUT", "geobr layer")
        )

    # -- execution --------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        apply_qgis_proxy()

        feedback.pushInfo("Loading the geobr Python package...")
        try:
            import geobr
        except ImportError as exc:
            raise QgsProcessingException(
                "The 'geobr' Python package is not available to QGIS.\n"
                f"Install it, then restart QGIS:\n    {PIP_COMMAND}\n\n({exc})"
            ) from exc

        kwargs = self._collect(parameters, context)
        declared = {arg for arg, _ in self._spec.params}
        kwargs.update({k: v for k, v in _FORCED.items() if k in declared})

        if feedback.isCanceled():
            return {}

        shown = ", ".join(
            f"{k}={v!r}" for k, v in kwargs.items() if k not in _FORCED
        )
        feedback.pushInfo(f"Running geobr.{self._spec.name}({shown})")
        feedback.pushInfo("Downloading - this can take a while on first use.")

        with _GEOBR_LOCK:
            try:
                gdf = getattr(geobr, self._spec.name)(**kwargs)
            except Exception as exc:
                raise QgsProcessingException(self._explain(exc)) from exc

        if gdf is None or len(gdf) == 0:
            raise QgsProcessingException(
                f"geobr.{self._spec.name}() returned no features for these "
                "arguments. Check the year and the code filter."
            )

        feedback.pushInfo(f"{len(gdf)} features returned (CRS: {gdf.crs}).")
        return {"OUTPUT": self._write(gdf, parameters, context, feedback)}

    def _collect(self, parameters, context):
        """Read the QGIS parameters back into reader keyword arguments."""
        kwargs = {}
        for arg, key, kind in self._exposed:
            if kind == "int":
                kwargs[arg] = self.parameterAsInt(parameters, key, context)
            elif kind == "bool":
                kwargs[arg] = self.parameterAsBool(parameters, key, context)
            elif isinstance(kind, tuple):
                index = self.parameterAsEnum(parameters, key, context)
                kwargs[arg] = kind[1][index]
            else:
                value = (self.parameterAsString(parameters, key, context) or "").strip()
                if not value:
                    # Leave it out entirely so the reader's own default applies.
                    continue
                kwargs[arg] = self._validate_code(arg, value) if arg.startswith("code_") else value
        return kwargs

    @staticmethod
    def _validate_code(arg, value):
        """Reject a code filter geobr would ignore or only partly apply.

        The rules live in ``discovery.validate_codes`` so they can be tested
        without a QGIS runtime; this only translates the failure.
        """
        try:
            return validate_codes(arg, value)
        except ValueError as exc:
            raise QgsProcessingException(str(exc)) from exc

    def _explain(self, exc):
        """Turn geobr's failure into something a QGIS user can act on."""
        message = str(exc)
        text = f"geobr.{self._spec.name}() failed: {message}"
        lowered = message.lower()
        if "st_aswkb" in lowered or "st_crs" in lowered:
            # _setup_connection swallows a failed "INSTALL spatial", so the
            # real cause only surfaces here, as a missing SQL function.
            text += (
                "\n\nThis usually means DuckDB's 'spatial' extension is not "
                "installed. It downloads once and is cached in ~/.duckdb. "
                "With a working connection, run:\n"
                "    python -c \"import duckdb; duckdb.connect().execute('INSTALL spatial')\""
            )
        elif (
            isinstance(exc, ConnectionError)
            or "connection" in lowered
            or "timed out" in lowered
        ):
            # geobr raises ConnectionError for both metadata and file downloads,
            # and its own message does not always mention the network - the
            # download path reports a possibly-corrupted file instead.
            text += (
                "\n\nCheck your internet connection. If you are behind a proxy, "
                "set it in Settings > Options > Network so the plugin can pass "
                "it to geobr."
            )
        return text

    def _write(self, gdf, parameters, context, feedback):
        """Write the GeoDataFrame to whatever destination the user picked."""
        dest = self.parameterAsOutputLayer(parameters, "OUTPUT", context)
        extension = os.path.splitext(dest)[1].lstrip(".")
        driver = QgsVectorFileWriter.driverForExtension(extension) if extension else "GPKG"
        if not driver:
            raise QgsProcessingException(
                f"Cannot determine an output format for {dest!r}. Use a "
                "recognised extension such as .gpkg, .geojson or .shp."
            )
        if driver == "ESRI Shapefile":
            feedback.pushWarning(
                "Shapefile truncates field names to 10 characters and cannot "
                "store all geobr columns faithfully. GeoPackage is preferred."
            )

        options = {"layer": self.displayName()} if driver == "GPKG" else {}
        try:
            gdf.to_file(dest, driver=driver, **options)
        except Exception as exc:
            raise QgsProcessingException(f"Could not write {dest!r}: {exc}") from exc

        feedback.pushInfo(f"Wrote {dest} ({driver}).")
        return dest
