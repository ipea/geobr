"""Disk-backed cache helpers for geobr parquet downloads.

Like the R package, the cache is temporary: files are stored in a
session-specific directory under the system temp folder and are deleted when
the Python process exits.
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
import threading
import time
from pathlib import Path

_cache_lock = threading.Lock()
_session_dir: Path | None = None

# Leftover session caches older than this are removed on a best-effort basis
# when a new session cache is created (processes killed before atexit could
# run leave their cache behind).
_MAX_CACHE_AGE_DAYS = 30


def cache_dir() -> Path:
    """Return the geobr cache directory for this session.

    A fresh temporary directory is created for this session and deleted when
    the Python process exits, so cached downloads never outlive the session
    (same behavior as the R package).
    """
    global _session_dir

    with _cache_lock:
        if _session_dir is None:
            _session_dir = Path(tempfile.mkdtemp(prefix="geobr_"))
            _sweep_stale_caches()
            atexit.register(_remove_session_dir, _session_dir)
        return _session_dir


def _sweep_stale_caches() -> None:
    """Delete session caches abandoned by processes that did not exit cleanly."""
    now = time.time()
    max_age_seconds = _MAX_CACHE_AGE_DAYS * 24 * 60 * 60
    try:
        for entry in Path(tempfile.gettempdir()).glob("geobr_*"):
            if entry.is_dir() and now - entry.stat().st_mtime > max_age_seconds:
                shutil.rmtree(entry, ignore_errors=True)
    except OSError:
        pass


def _remove_session_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def cached_path(filename: str) -> Path:
    """Full path for a cached parquet file."""
    return cache_dir() / filename


def is_cached(filename: str) -> bool:
    path = cached_path(filename)
    return path.exists() and path.stat().st_size > 0
