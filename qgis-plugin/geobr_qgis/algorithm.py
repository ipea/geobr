"""The single Processing algorithm that fronts every geobr reader.

One class serves all 31 readers. Its parameters are built from the reader's own
signature, so a reader added to geobr shows up in QGIS with no change here.
"""

from __future__ import annotations

import os
import re
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


class _Required:
    """Sentinel for a reader argument that has no default."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "REQUIRED"


REQUIRED = _Required()

PIP_COMMAND = "python -m pip install --user geobr"

# geobr keeps a module-global DuckDB connection and registers views by name
# ("{geo}_{year}"). Two algorithms running at once - batch mode, or a model -
# would share that connection and collide, so reader calls are serialised.
_GEOBR_LOCK = threading.Lock()

# Arguments the plugin owns rather than the user. QGIS already provides the
# equivalent: `feedback` replaces tqdm and the verbose flag, and the output
# format is fixed because we always want a GeoDataFrame to write to disk.
# Each is passed only if the reader actually declares it - read_comparable_areas
# declares none of them and would otherwise raise TypeError.
_FORCED = {"output": "gpd", "show_progress": False, "verbose": False, "cache": True}

# `macro` is deprecated in read_health_region, and actively harmful here:
# parameterAsString returns "" for an unset optional, "" is not None, so the
# reader's `if macro is not None` branch fires and silently overwrites the
# user's geometry_level choice with "municipality".
_SKIP = {"macro"}

# Arguments suppressed for one specific reader. geobr's read_health_region
# accepts geometry_level but ignores it: the micro/macro aggregation groups by
# every column it does not explicitly exclude, and code_muni6 survives that
# GROUP BY, so all three levels return one feature per municipality. Offering a
# control that silently does nothing is worse than not offering it, so the
# reader ships at its (correct) municipality level until geobr is fixed.
_SKIP_PER_READER = {"read_health_region": {"geometry_level"}}

_YEAR_ARGS = {"year", "date", "start_year", "end_year"}

_ENUM_ARGS = {
    "zone": ["urban", "rural"],
    "geometry_level": ["municipality", "micro", "macro"],
}

# geobr infers the filter column from the value's shape. Anything it cannot
# match falls through to an *unfiltered* result rather than an error, so the
# accepted forms are checked here before the call.
_CODE_RE = re.compile(r"^(all|[A-Za-z]{2}|\d+)$")


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
        skipped = _SKIP | _SKIP_PER_READER.get(self._spec.name, set())
        for arg, default in self._spec.params:
            if arg in _FORCED or arg in skipped:
                continue
            key = arg.upper()
            label = arg.replace("_", " ").capitalize()
            required = default is REQUIRED

            if arg in _YEAR_ARGS:
                self.addParameter(
                    QgsProcessingParameterNumber(
                        key,
                        label,
                        QgsProcessingParameterNumber.Integer,
                        defaultValue=None if required else default,
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
        """Check a code filter before geobr silently ignores it.

        ``read_filter_parquet_relation`` returns the *unfiltered* relation when a
        value matches none of its patterns, so a typo would otherwise produce a
        whole-country layer where one state was asked for.
        """
        parts = [p.strip() for p in value.split(",") if p.strip()]
        for part in parts:
            if not _CODE_RE.match(part):
                raise QgsProcessingException(
                    f"Invalid value {part!r} for '{arg}'. Use 'all', a two-letter "
                    "state abbreviation (RJ), or a numeric IBGE code (33, "
                    "3304557). Separate several codes with commas."
                )
        return parts[0] if len(parts) == 1 else parts

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
        elif "connection" in lowered or "timed out" in lowered:
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
