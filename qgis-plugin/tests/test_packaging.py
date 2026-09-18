"""Packaging invariants: what the plugin declares to QGIS and to qpip.

These read files, never import the plugin, so they run without a QGIS runtime
like the rest of this suite.
"""

import configparser
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "qgis-plugin" / "geobr_qgis"
PYPROJECT = REPO_ROOT / "python-package" / "pyproject.toml"


def _requirements():
    """Requirement lines of the plugin's requirements.txt, as qpip reads them."""
    lines = (PLUGIN_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith(("#", "-"))
    ]


def _geobr_duckdb_floor():
    """geobr's own duckdb requirement, e.g. 'duckdb>=1.5.3'."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = [d for d in data["project"]["dependencies"] if d.startswith("duckdb")]
    assert len(deps) == 1, deps
    return deps[0].replace(" ", "")


def _metadata():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    return parser["general"]


def test_requirements_is_duckdb_only():
    """qpip installs with --target, so only self-contained wheels are safe."""
    assert _requirements() == [_geobr_duckdb_floor()]


def test_pip_fallback_matches_requirements():
    """The hand-install command in algorithm.py names the same duckdb floor."""
    source = (PLUGIN_DIR / "algorithm.py").read_text(encoding="utf-8")
    match = re.search(r'PIP_COMMAND_DUCKDB = .*?"(duckdb[^"]*)"', source)
    assert match, "PIP_COMMAND_DUCKDB not found in algorithm.py"
    assert match.group(1) == _geobr_duckdb_floor()


def test_metadata_declares_qpip():
    deps = [d.strip() for d in _metadata()["plugin_dependencies"].split(",")]
    assert "qpip" in deps


def test_metadata_version_heads_changelog():
    meta = _metadata()
    first = meta["changelog"].strip().split()[0]
    assert first == meta["version"]
