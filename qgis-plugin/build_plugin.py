"""Build the geobr QGIS plugin ZIP for plugins.qgis.org.

The plugin ships the geobr Python library inside itself, so users need no
``pip install``. That copy is made here, at build time, and never committed:
``python-package/geobr/`` is the one source tree in this repo, and this script
stages it into ``geobr_qgis/_vendor/geobr/`` before zipping.

    python qgis-plugin/build_plugin.py            # -> qgis-plugin/dist/geobr_qgis-<version>.zip
    python qgis-plugin/build_plugin.py --out DIR  # stage and zip somewhere else

The archive is written with ``zipfile`` and explicit POSIX member names. The
plugin repository rejects archives whose members carry backslashes, which is
what PowerShell's ``Compress-Archive`` can produce on Windows, so every member
is audited before the file is declared built.
"""

from __future__ import annotations

import argparse
import configparser
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
PLUGIN_DIR = HERE / "geobr_qgis"
GEOBR_SOURCE = REPO_ROOT / "python-package" / "geobr"
DEFAULT_OUT = HERE / "dist"

#: Never staged, from either tree.
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def _ignore_plugin(directory, names):
    """The plugin tree's own exclusions, plus an in-place ``_vendor`` if any.

    A developer may have staged into the working tree to test; the build must
    take geobr from ``python-package/``, never from a stale copy.
    """
    ignored = set(_IGNORE(directory, names))
    if Path(directory) == PLUGIN_DIR:
        ignored.add("_vendor")
    return ignored


def plugin_version() -> str:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    return parser["general"]["version"]


def stage(out_dir: Path) -> Path:
    """Copy the plugin and geobr into ``out_dir/geobr_qgis`` and return it.

    The target is removed first: ``copytree`` with ``dirs_exist_ok`` would keep
    a file a previous build staged and a later geobr release deleted.
    """
    if not (GEOBR_SOURCE / "__init__.py").is_file():
        raise SystemExit(f"geobr source not found at {GEOBR_SOURCE}")
    staged = Path(out_dir) / "geobr_qgis"
    shutil.rmtree(staged, ignore_errors=True)
    shutil.copytree(PLUGIN_DIR, staged, ignore=_ignore_plugin)
    shutil.copytree(GEOBR_SOURCE, staged / "_vendor" / "geobr", ignore=_IGNORE)
    return staged


def audit_member(name: str) -> None:
    """Raise if a ZIP member name would be rejected by the plugin repository."""
    if "\\" in name:
        raise ValueError(f"backslash in archive name: {name!r}")
    if not name.startswith("geobr_qgis/"):
        raise ValueError(f"member outside geobr_qgis/: {name!r}")
    parts = name.split("/")
    if "__pycache__" in parts or name.endswith(".pyc"):
        raise ValueError(f"generated file in archive: {name!r}")


def write_zip(staged: Path, zip_path: Path) -> list[str]:
    """Zip ``staged`` as ``geobr_qgis/...`` with POSIX names; return the names."""
    files = sorted(p for p in staged.rglob("*") if p.is_file())
    names = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            name = "geobr_qgis/" + path.relative_to(staged).as_posix()
            audit_member(name)
            zf.write(path, arcname=name)
            names.append(name)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            audit_member(info.filename)
    return names


def build(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    staged = stage(out_dir)
    zip_path = out_dir / f"geobr_qgis-{plugin_version()}.zip"
    names = write_zip(staged, zip_path)
    for name in names:
        print(name)
    print(f"\n{zip_path}  ({len(names)} members)")
    return zip_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"directory for the staged tree and the ZIP (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
