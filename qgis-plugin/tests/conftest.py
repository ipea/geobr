"""Test setup for the plugin's QGIS-free discovery layer.

``discovery`` is imported as a **top-level** module rather than as
``geobr_qgis.discovery``, because ``geobr_qgis/__init__.py`` imports
``qgis.core`` and would fail outside a QGIS runtime. Putting the plugin
directory itself on ``sys.path`` bypasses that package ``__init__``.

geobr does not need to be installed: the tests point discovery at this repo's
own ``python-package/geobr`` source tree.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "qgis-plugin" / "geobr_qgis"
GEOBR_SOURCE = REPO_ROOT / "python-package" / "geobr"

sys.path.insert(0, str(PLUGIN_DIR))


@pytest.fixture(scope="session")
def geobr_source():
    """Path to the geobr package source this repo ships."""
    if not (GEOBR_SOURCE / "__init__.py").is_file():
        pytest.fail(f"geobr source not found at {GEOBR_SOURCE}")
    return str(GEOBR_SOURCE)


@pytest.fixture(scope="session")
def specs(geobr_source):
    """Every ReaderSpec discovery derives from that source."""
    import discovery

    return discovery.discover_readers(package_dir=geobr_source)


@pytest.fixture(scope="session")
def by_name(specs):
    return {spec.name: spec for spec in specs}
