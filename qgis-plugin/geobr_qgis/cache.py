"""A Processing algorithm that clears geobr's download cache.

geobr's Python cache is deliberately persistent - unlike the R package, which
uses a per-session temp directory, it writes to ~/.cache/geobr and never expires
or caps it. A few years of census tracts add up to gigabytes, so this gives the
user a visible, deliberate way to reclaim the space. Nothing is ever cleared
automatically: the directory is shared with every other geobr consumer on the
machine (scripts, notebooks), and a QGIS plugin silently wiping it would force
re-downloads for tools it knows nothing about.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingOutputNumber,
    QgsProcessingParameterBoolean,
)


def cache_dirs():
    """Every directory geobr might have cached into, most likely first.

    This mirrors ``geobr._cache.cache_dir()`` rather than importing it. That
    module is private, and importing it would execute ``geobr/__init__.py``,
    pulling in pandas, geopandas and duckdb for what is otherwise a path
    lookup. The contract - ``$XDG_CACHE_HOME/geobr``, else ``~/.cache/geobr``,
    falling back to the system temp directory when that cannot be created - is
    documented in both geobr packages.

    Duplicating it is safe in the one direction that matters: if geobr ever
    moves the cache, this reports an empty directory rather than deleting
    something else. Every candidate ends in a directory literally named
    ``geobr``.
    """
    candidates = []
    base = os.environ.get("XDG_CACHE_HOME")
    candidates.append(Path(base) / "geobr" if base else Path.home() / ".cache" / "geobr")
    candidates.append(Path(tempfile.gettempdir()) / "geobr")

    seen, unique = set(), []
    for path in candidates:
        resolved = str(path)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


class ClearCacheAlgorithm(QgsProcessingAlgorithm):
    """Removes the parquet files geobr has downloaded."""

    def createInstance(self):
        return ClearCacheAlgorithm()

    def name(self):
        return "clear_cache"

    def displayName(self):
        return "Clear geobr download cache"

    def group(self):
        return "Brazilian spatial data"

    def groupId(self):
        return "geobr"

    def shortHelpString(self):
        return (
            "Deletes the data files geobr has downloaded.\n\n"
            "geobr caches every dataset it downloads and never expires or caps "
            "that cache, so it grows without bound - a single year of census "
            "tracts can exceed 350 MB. This algorithm reclaims that space.\n\n"
            "Nothing is lost permanently: anything deleted is downloaded again "
            "the next time you request it.\n\n"
            "Note the cache is shared with any other geobr use on this machine, "
            "such as Python scripts or notebooks, which will also re-download "
            "afterwards. Tick 'List files only' to see what is there first."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterBoolean(
                "LIST_ONLY",
                "List files only (do not delete)",
                defaultValue=False,
            )
        )
        self.addOutput(QgsProcessingOutputNumber("FILES", "Files removed"))
        self.addOutput(QgsProcessingOutputNumber("BYTES", "Bytes freed"))

    def processAlgorithm(self, parameters, context, feedback):
        list_only = self.parameterAsBool(parameters, "LIST_ONLY", context)

        files = 0
        freed = 0
        found_any = False

        for directory in cache_dirs():
            if not directory.is_dir():
                continue
            found_any = True
            feedback.pushInfo(f"Cache directory: {directory}")

            # Only regular *.parquet files, never subdirectories: that is all
            # geobr writes here, and it keeps an unexpected directory safe.
            for entry in sorted(directory.glob("*.parquet")):
                if feedback.isCanceled():
                    break
                if not entry.is_file():
                    continue
                try:
                    size = entry.stat().st_size
                except OSError as exc:
                    feedback.pushWarning(f"Could not inspect {entry.name}: {exc}")
                    continue

                if list_only:
                    feedback.pushInfo(f"  {entry.name} ({size / 1048576:.1f} MB)")
                    files += 1
                    freed += size
                    continue

                try:
                    entry.unlink()
                except OSError as exc:
                    # A file held open by another process is not fatal; report
                    # it and keep going rather than aborting half-way.
                    feedback.pushWarning(f"Could not delete {entry.name}: {exc}")
                    continue
                feedback.pushInfo(f"  removed {entry.name} ({size / 1048576:.1f} MB)")
                files += 1
                freed += size

        if not found_any:
            feedback.pushInfo("No geobr cache directory found - nothing to do.")
            return {"FILES": 0, "BYTES": 0}

        verb = "would free" if list_only else "freed"
        feedback.pushInfo(f"{files} file(s), {verb} {freed / 1048576:.1f} MB.")
        return {"FILES": files, "BYTES": freed}
