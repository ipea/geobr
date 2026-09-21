"""Packaging invariants: what the plugin declares to QGIS and to qpip, and
what ``build_plugin.py`` puts in the ZIP.

These read files and run the build into a temp dir; they never import the
plugin, so they run without a QGIS runtime like the rest of this suite.
"""

import configparser
import re
import tomllib
import zipfile
from pathlib import Path

import build_plugin
import discovery

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "qgis-plugin" / "geobr_qgis"
GEOBR_SOURCE = REPO_ROOT / "python-package" / "geobr"
PYPROJECT = REPO_ROOT / "python-package" / "pyproject.toml"


def _requirements():
    """Requirement lines of the plugin's requirements.txt, as qpip reads them."""
    lines = (PLUGIN_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith(("#", "-"))
    ]


def _geobr_dependencies():
    """geobr's declared requirements, whitespace-stripped, e.g. 'duckdb>=1.5.3'."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return [d.replace(" ", "") for d in data["project"]["dependencies"]]


def _geobr_duckdb_floor():
    """geobr's own duckdb requirement, e.g. 'duckdb>=1.5.3'."""
    deps = [d for d in _geobr_dependencies() if d.startswith("duckdb")]
    assert len(deps) == 1, deps
    return deps[0]


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


def test_metadata_external_deps_is_duckdb():
    """The one dependency left outside the ZIP is duckdb, via qpip."""
    assert _metadata()["external_deps"] == _geobr_duckdb_floor()


def test_startup_probe_matches_pyproject():
    """The modules probed at startup are geobr itself plus its declared deps.

    ``DEPENDENCIES`` is written by hand in discovery.py; this keeps it from
    drifting when python-package/pyproject.toml gains or loses a requirement.
    """
    declared = {re.split(r"[<>=!~\[ ]", d, maxsplit=1)[0] for d in _geobr_dependencies()}
    assert set(discovery.DEPENDENCIES) == {"geobr"} | declared


def _relative_files(root):
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


def test_staged_bundle_is_the_python_package(tmp_path):
    """_vendor/geobr is a byte-for-byte copy of python-package/geobr."""
    staged = build_plugin.stage(tmp_path)
    bundle = staged / "_vendor" / "geobr"
    assert _relative_files(bundle) == _relative_files(GEOBR_SOURCE)
    for rel in _relative_files(bundle):
        assert (bundle / rel).read_bytes() == (GEOBR_SOURCE / rel).read_bytes(), rel
    # The staged plugin itself carries no generated files and no nested copy
    # of a previous in-place staging.
    assert not any("__pycache__" in p.parts for p in staged.rglob("*"))
    assert not (staged / "_vendor" / "_vendor").exists()


def test_zip_layout(tmp_path):
    """What CLAUDE.md asks a human to check by hand: one top dir, POSIX names,
    nothing generated, and the bundle with its data files inside."""
    assert build_plugin.main(["--out", str(tmp_path)]) == 0
    zips = list(tmp_path.glob("geobr_qgis-*.zip"))
    assert zips == [tmp_path / f"geobr_qgis-{_metadata()['version']}.zip"]
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    assert names, "empty archive"
    for name in names:
        assert "\\" not in name, name
        assert name.startswith("geobr_qgis/"), name
        assert "__pycache__" not in name and not name.endswith(".pyc"), name
    assert {n.split("/")[0] for n in names} == {"geobr_qgis"}
    for required in (
        "geobr_qgis/metadata.txt",
        "geobr_qgis/requirements.txt",
        "geobr_qgis/_vendor/geobr/__init__.py",
        "geobr_qgis/_vendor/geobr/data/br_offcoast.parquet",
        "geobr_qgis/_vendor/geobr/data/grid_state_correspondence_table.csv",
    ):
        assert required in names, required
    assert not any(n.startswith("geobr_qgis/tests/") for n in names)
