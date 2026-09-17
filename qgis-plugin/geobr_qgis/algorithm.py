"""The single Processing algorithm that fronts every geobr reader.

One class serves every reader geobr exports. Its parameters are built from the
reader's own signature, so a reader added to geobr shows up in QGIS with no
change here.
"""

from __future__ import annotations

import os
import threading

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProcessing,
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
from qgis.PyQt.QtCore import QTimer

from .discovery import (
    ENUM_ARGS,
    REQUIRED,
    available_years,
    layer_name,
    parameter_label,
    validate_codes,
)

PIP_COMMAND = 'python -m pip install --user "geobr>=2.0.1"'

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

# The year (or YYYYMM date) is a drop-down of the years geobr's metadata lists
# for the data set (see `years_on_offer`), newest first and preselected. Its
# values are the year strings themselves, not list positions: QGIS's
# `usesStaticStrings` makes `YEAR=2020` mean 2020 on the command line and in a
# saved model whatever the list looks like on the day it is run.
#
# When the years could not be listed - geobr missing, no network - the field
# falls back to the number widget below. 1872 is geobr's earliest data. A
# number widget cannot be blank unless the parameter is optional, so a year
# with no default of its own is declared optional to QGIS (the field then
# opens empty, showing "Not set") and the requirement is enforced in
# `checkParameterValues` / `_collect` instead. Without that, the spin box
# would open on its minimum and the reader would appear to default to 1872.
_YEAR_RANGE = (1872, 9999)
_DATE_RANGE = (187201, 999912)

# The algorithm window opens at least this many pixels wide. QGIS reopens the
# window at whatever size it last had, and the Processing default is barely
# 500 px; with the help panel taking half of that, the parameters are squeezed
# into a strip. A minimum on the widget beats that restore, since a window
# cannot be resized below what its content allows - but it is only a floor
# for the moment of opening: `_release_width` drops it as soon as the window
# is up, so the user resizes it freely and QGIS remembers the result as it
# does for any other algorithm. Clamped to the screen in `_fit_to_screen`.
_OPENING_WIDTH = 700


def _fit_to_screen(widget, width):
    """`width`, or 90% of the widget's screen if that is narrower."""
    screen = widget.screen() if hasattr(widget, "screen") else None
    if screen is None:
        return width
    return min(width, int(screen.availableGeometry().width() * 0.9))


def _release_width(widget):
    """Drop the opening floor so the window resizes freely.

    Runs from a zero-delay timer, i.e. on the first turn of the event loop
    after Processing has shown the window and QGIS has restored (and, thanks
    to the floor, widened) its geometry.
    """
    try:
        widget.setMinimumWidth(0)
    except RuntimeError:
        pass  # the window was closed before the event loop got here


# `{dataset: [years]}` from geobr's metadata, fetched once per QGIS session.
# `None` means not fetched yet; `{}` means the fetch failed, and is kept so a
# machine with no network pays geobr's connection timeout once, not on every
# dialog. The metadata itself is cached by geobr for the session, so the run
# that follows reuses this same listing rather than fetching it again.
_YEARS = None


def years_on_offer():
    """Which years geobr can serve, per data set, or ``{}`` if unknown.

    This is the plugin's one use of geobr outside a run, and it is deliberate:
    the years a data set offers exist nowhere but in the release listing that
    ``download_metadata_v2()`` builds, and that listing changes whenever data
    is added upstream. Reading geobr's source, as the rest of the plugin does,
    cannot see it.

    Importing geobr costs seconds and the listing needs the network, so this
    is never called at QGIS startup - only from an instance Processing has
    created to run or to show (see ``createInstance``).
    """
    global _YEARS
    if _YEARS is None:
        _YEARS = {}
        try:
            apply_qgis_proxy()
            from geobr.utils import download_metadata_v2

            meta = download_metadata_v2()
            _YEARS = available_years(zip(meta["geo"], meta["year"]))
        except Exception as exc:  # noqa: BLE001 - never fail a dialog for this
            QgsMessageLog.logMessage(
                "Could not list the years geobr offers, so year fields open "
                f"empty this session: {exc}",
                "geobr",
                Qgis.MessageLevel.Warning,
            )
    return _YEARS


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

    def __init__(self, spec, prefill=False):
        super().__init__()
        self._spec = spec
        self._exposed = []
        self._prefill = prefill

    # -- identity ---------------------------------------------------------

    def createInstance(self):
        # Processing calls create() - and so this - for every dialog, batch
        # row, model child and qgis_process run. The prototype the provider
        # registers at startup is initialised too, but never shown or run, so
        # only the instances made here look up the years on offer: that keeps
        # the geobr import and the network off the QGIS startup path.
        return GeobrAlgorithm(self._spec, prefill=True)

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

    def createCustomParametersWidget(self, parent=None):
        """QGIS's own algorithm window, guaranteed a usable width.

        Processing shows whatever this returns in place of the window it
        would build itself - from the toolbox, the locator, the Processing
        menu, "Run as Single Process" in batch mode and
        ``processing.createAlgorithmDialog`` alike - and that is the only
        moment an algorithm can reach its own window. What is returned *is*
        the window Processing would have built, so batch mode, the log,
        docking and everything else behave as for any other algorithm; it
        merely opens at least ``_OPENING_WIDTH`` wide.

        Returning ``None`` hands back to Processing, so a QGIS whose
        Processing internals have moved again loses the width guarantee, not
        the algorithm.
        """
        try:
            from qgis.utils import iface
        except ImportError:  # pragma: no cover - always present inside QGIS
            iface = None
        window = iface.mainWindow() if iface is not None else parent
        try:
            try:
                # QGIS 4: a dockable widget whose exec() shows it docked or
                # as a dialog, whichever the user last had.
                from processing.gui.algorithm_widget import AlgorithmWidget

                widget = AlgorithmWidget(self, False, window)
            except ImportError:
                # QGIS 3: a plain dialog.
                from processing.gui.AlgorithmDialog import AlgorithmDialog

                widget = AlgorithmDialog(self, False, window)
        except Exception as exc:  # noqa: BLE001 - never lose the algorithm for this
            QgsMessageLog.logMessage(
                "Could not build the geobr algorithm window; using the "
                f"Processing default: {exc}",
                "geobr",
                Qgis.MessageLevel.Warning,
            )
            return None
        widget.setMinimumWidth(_fit_to_screen(widget, _OPENING_WIDTH))
        QTimer.singleShot(0, lambda: _release_width(widget))
        return widget

    # -- parameters -------------------------------------------------------

    def initAlgorithm(self, config=None):
        self._exposed = []
        self._required_years = []
        years = years_on_offer().get(self._spec.dataset, []) if self._prefill else []
        for arg, default in self._spec.params:
            if arg in _FORCED or arg in _SKIP:
                continue
            key = arg.upper()
            label = parameter_label(arg)
            required = default is REQUIRED

            if arg in ("year", "date") and years:
                # Newest first, newest selected - ahead of any default the
                # reader declares. `start_year`/`end_year` never get here:
                # they belong to the excluded read_comparable_areas.
                options = [str(y) for y in reversed(years)]
                self.addParameter(
                    QgsProcessingParameterEnum(
                        key,
                        label,
                        options=options,
                        defaultValue=options[0],
                        usesStaticStrings=True,
                    )
                )
                kind = "year"
            elif arg in _YEAR_ARGS:
                low, high = _DATE_RANGE if arg == "date" else _YEAR_RANGE
                self.addParameter(
                    QgsProcessingParameterNumber(
                        key,
                        label,
                        QgsProcessingParameterNumber.Type.Integer,
                        defaultValue=None if required else default,
                        optional=required,
                        minValue=low,
                        maxValue=high,
                    )
                )
                if required:
                    self._required_years.append((key, label))
                kind = "int"
            elif arg in ENUM_ARGS:
                options = ENUM_ARGS[arg]
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

    def checkParameterValues(self, parameters, context):
        missing = self._missing_year(parameters, context)
        if missing:
            return False, missing
        return super().checkParameterValues(parameters, context)

    def _missing_year(self, parameters, context):
        """Message naming the first blank year the reader cannot do without.

        A year parameter is optional to QGIS only when nothing could be
        prefilled, so that the field can open empty; the reader still needs a
        value, and asking here is cheaper than letting geobr raise a TypeError
        after loading.
        """
        for key, label in self._required_years:
            if not self.parameterAsString(parameters, key, context).strip():
                what = "a date as YYYYMM" if key == "DATE" else "a year"
                years = years_on_offer().get(self._spec.dataset)
                offered = (
                    f": {', '.join(str(y) for y in years)}" if years else "."
                )
                return (
                    f"{label} is required. Enter {what} that geobr offers for "
                    f"this data set{offered}"
                )
        return None

    def processAlgorithm(self, parameters, context, feedback):
        apply_qgis_proxy()

        missing = self._missing_year(parameters, context)
        if missing:
            raise QgsProcessingException(missing)

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
        name = layer_name(self._spec.geo, kwargs)
        return {"OUTPUT": self._write(gdf, name, parameters, context, feedback)}

    def _collect(self, parameters, context):
        """Read the QGIS parameters back into reader keyword arguments."""
        kwargs = {}
        for arg, key, kind in self._exposed:
            if kind == "year":
                # A static-string enum: the value is the year as text. Read it
                # as a string rather than with parameterAsEnumString so an
                # integer passed from Python is accepted too.
                kwargs[arg] = int(self.parameterAsString(parameters, key, context))
            elif kind == "int":
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

    def _write(self, gdf, name, parameters, context, feedback):
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

        self._name_layer(name, dest, parameters, context)
        feedback.pushInfo(f"Wrote {dest} ({driver}).")
        return dest

    def _name_layer(self, name, dest, parameters, context):
        """Name the layer QGIS is about to load after the data it holds.

        One algorithm class serves every reader and the destination is a
        generated temporary file, so without this every run arrives in the
        legend under the same name and a second run cannot be told from the
        first. That is the whole point of the change.

        QGIS reads `LayerDetails.name` only when `forceName` is set; otherwise
        PREFER_FILENAME_AS_LAYER_NAME wins and the name comes from the file on
        disk. Forcing is therefore the only lever, and it is pulled narrowly:

        * only for a temporary destination, so a filename the user typed still
          names their layer - which is exactly what that setting promises;
        * only when nothing upstream has already named it, because Model
          Builder puts the *user's* model output name in `name`, and clobbering
          that would be a worse regression than the bug being fixed.

        `parameterAsOutputLayer` must already have run: it is what registers the
        destination, so `willLoadLayerOnCompletion` is False until it has. That
        check is also False for `qgis_process` and for model intermediates,
        which are left alone.
        """
        if not context.willLoadLayerOnCompletion(dest):
            return

        # How QGIS's own Postprocessing reads the destination: an exact sentinel
        # comparison rather than a temp-path prefix test, which would fail
        # silently on a path-separator mismatch.
        raw = parameters.get("OUTPUT")
        sink = raw.sink.staticValue() if hasattr(raw, "sink") else raw
        if sink not in (None, "", QgsProcessing.TEMPORARY_OUTPUT):
            return

        details = context.layerToLoadOnCompletionDetails(dest)
        unnamed = (
            "",
            self.parameterDefinition("OUTPUT").description(),
            QgsProcessing.TEMPORARY_OUTPUT,
        )
        if details.name in unnamed:
            details.name = name
            details.forceName = True
