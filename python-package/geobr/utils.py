import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError
import tempfile

import geopandas as gpd
import pandas as pd
import requests
import unicodedata
from io import StringIO

from geobr.constants import DataTypes
from geobr._cache import cached_path, is_cached
from geobr._duckdb_backend import read_filter_parquet_relation, duckdb_connection
from geobr._output import convert_output

MIRRORS = ["https://github.com/ipea/geobr/releases/download/v1.7.0/"]
GEOBR_DATA_RELEASE = "v2.0.0"
GEOBR_PREP_DATA_BASE = (
    f"https://github.com/ipea/geobr_prep_data/releases/download/{GEOBR_DATA_RELEASE}"
)
IPEA_FALLBACK_BASE = "https://www.ipea.gov.br/geobr/data_v2.0.0"


def _get_unique_values(_df, column):

    return ", ".join([str(i) for i in _df[column].unique()])


def url_solver(url):

    file_id = url.split("/")[-1]
    urls = [url] + [mirror + file_id for mirror in MIRRORS]

    for url in urls:

        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
        except:
            continue

    raise ConnectionError(
        "No mirrors are active. Please report to https://github.com/ipea/geobr/issues"
    )


@lru_cache(maxsize=124)
def download_metadata(
    url="http://www.ipea.gov.br/geobr/metadata/metadata_1.7.0_gpkg.csv",
):
    """Support function to download metadata internally used in geobr.

    It caches the metadata file to avoid reloading it in the same session.

    Parameters
    ----------
    url : str, optional
        Metadata url, by default 'http://www.ipea.gov.br/geobr/metadata/metadata_1.7.0_gpkg.csv'

    Returns
    -------
    pd.DataFrame
        Table with all metadata of geopackages

    Raises
    ------
    Exception
        Leads user to Github issue page if metadata url is not found

    Examples
    --------
    >>> metadata = download_metadata()
    >>> metadata.head(1)
                  geo  year code                                      download_path      code_abbrev
    0  amazonia_legal  2012   am  http://www.ipea.gov.br/geobr/data_gpkg/amazoni...  amazonia_legal
    """

    try:
        return pd.read_csv(StringIO(url_solver(url).text))

    except HTTPError:
        raise Exception(
            "Perhaps this is an internet connection problem."
            "If this is not a connection problem in your network, "
            " please try geobr again in a few minutes. "
            "Please report to https://github.com/ipea/geobr/issues"
        )


def select_year(metadata, year):
    """Apply year to metadata and checks its existence.

    If it do not exist, raises an informative error.

    Parameters
    ----------
    metadata : pd.DataFrame
        Filtered metadata table
    year : int
        Year selected by user

    Returns
    -------
    pd.DataFrame
        Filtered dataframe by year.

    Raises
    ------
    Exception
        If year does not exists, raises exception with available years.
    """

    if year is None:
        year = max(metadata["year"])

    elif year not in list(metadata["year"]):

        raise Exception(
            "Error: Invalid Value to argument 'year/date'. "
            "It must be one of the following: "
            f'{_get_unique_values(metadata, "year")}'
        )

    return metadata.query(f"year == {year}")


def select_simplified(metadata, simplified):
    """Filter metadata by data type. It can be simplified or normal.
    If 'simplified' is True, it returns a simplified version of the shapefiles.
    'normal' returns the complete version. Usually, the complete version
    if heavier than the simplified, demanding more resources.

    Parameters
    ----------
    metadata : pd.DataFrame
        Filtered metadata table
    simplified : boolean
        Data type, either True for 'simplified' or False for 'normal'

    Returns
    -------
    pd.DataFrame
        Filtered metadata table by type

    """

    # regex=False: literal match, and it avoids the missing RE2 kernel under
    # pandas 3 with Arrow-backed strings (see download_metadata_v2).
    if simplified:
        return metadata[
            metadata["download_path"].str.contains("simplified", regex=False)
        ]

    else:
        return metadata[
            ~metadata["download_path"].str.contains("simplified", regex=False)
        ]


@lru_cache(maxsize=1240)
def load_gpkg(url):
    """Internal function to donwload and convert to geopandas one url.

    It caches url result for the active session.

    Parameters
    ----------
    url : str
        Address with gpkg

    Returns
    -------
    gpd.GeoDataFrame
         Table with metadata and shapefiles contained in url.
    """

    try:
        content = url_solver(url).content

    except Exception as e:

        raise Exception(
            "Some internal url is broken."
            "Please report to https://github.com/ipea/geobr/issues"
        ) from e

    # This below does not work in Windows -- see the Docs
    # Whether the name can be used to open the file a second time, while the named temporary file is still open,
    # varies across platforms (it can be so used on Unix; it cannot on Windows NT or later).
    # https://docs.python.org/2/library/tempfile.html

    # Create a temporary file with .gpkg extension that is automatically deleted when closed
    with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as fp:
        fp.write(content)
        # Need to close file before reading on Windows
        fp.close()
        gdf = gpd.read_file(fp.name)
        # Clean up temp file
        os.unlink(fp.name)

    return gdf


def enforce_types(df):
    """Enforce correct datatypes according to DataTypes constant

    Parameters
    ----------
    df : gpd.GeoDataFrame
        Raw output data

    Returns
    -------
    gpd.GeoDataFrame
        Output data with correct types
    """

    for column in df.columns:

        if column in DataTypes.__members__.keys():

            df[column] = df[column].astype(DataTypes[column].value)

    return df


def download_gpkg(metadata):
    """Generalizes gpkg dowload and conversion to geopandas
    for one or many urls

    Parameters
    ----------
    metadata : pd.DataFrame
        Filtered metadata

    Returns
    -------
    gpd.GeoDataFrame
        Table with metadata and shapefiles contained in urls.
    """

    urls = metadata["download_path"].tolist()

    gpkgs = [load_gpkg(url) for url in urls]

    df = gpd.GeoDataFrame(pd.concat(gpkgs, ignore_index=True))

    df = enforce_types(df)

    return df


def select_metadata(geo, simplified=None, year=False):
    """Downloads and filters metadata given `geo`, `simplified` and `year`.

    Parameters
    ----------
    geo : str
        Shapefile category. I.e: state, biome, etc...
    simplified : boolean
        `simplified` or `normal` shapefiles
    year : int
        Year of the data

    Returns
    -------
    pd.DataFrame
        Filtered metadata

    Raises
    ------
    Exception
        if a parameter is not found in metadata table
    """

    # Get metadata with data addresses
    metadata = download_metadata()

    if len(metadata.query(f'geo == "{geo}"')) == 0:
        raise Exception(
            f"The `geo` argument {geo} does not exist."
            "Please, use one of the following:"
            f'{_get_unique_values(metadata, "geo")}'
        )

    # Select geo
    metadata = metadata.query(f'geo == "{geo}"')

    if simplified is not None:
        # Select data type
        metadata = select_simplified(metadata, simplified)

    if year != False:
        # Verify year input
        metadata = select_year(metadata, year)

    return metadata


def _download_file(urls, dest: Path, show_progress: bool = False) -> bool:
    """Try URLs in order; write to dest. Return True on success."""
    for url in urls:
        try:
            response = requests.get(url, stream=True, timeout=500, verify=False)
            if response.status_code != 200:
                continue
            total = int(response.headers.get("content-length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            if show_progress and total > 0:
                try:
                    from tqdm import tqdm

                    with open(dest, "wb") as f, tqdm(
                        total=total, unit="B", unit_scale=True, desc=dest.name
                    ) as bar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
                except ImportError:
                    with open(dest, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            else:
                with open(dest, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            if dest.exists() and dest.stat().st_size > 0:
                return True
        except Exception:
            continue
    return False


@lru_cache(maxsize=1)
def download_metadata_v2() -> pd.DataFrame:
    """Download and parse latest release file list from GitHub (mirrors R download_metadata2)."""
    cache_meta = cached_path("metadata_geobr_v2.parquet")
    if cache_meta.exists() and cache_meta.stat().st_size > 0:
        return pd.read_parquet(cache_meta)
    # Try to read latest release
    api_url = (
        "https://api.github.com/repos/ipea/geobr_prep_data/releases/latest"
    )
    try:
        resp = requests.get(api_url, timeout=60)
        resp.raise_for_status()
        assets = resp.json().get("assets", [])
        rows = []
        for asset in assets:
            fname = asset.get("name", "")
            url = asset.get("browser_download_url", "")
            if not fname.endswith(".parquet"):
                continue
            rows.append({"file_name": fname, "download_url": url})
        if not rows:
            # if latest download fails, fallback to `GEOBR_DATA_RELEASE`
            release_url = (
                "https://api.github.com/repos/ipea/geobr_prep_data/releases"
            )
            resp2 = requests.get(release_url, timeout=60)
            resp2.raise_for_status()
            for release in resp2.json():
                if release.get("tag_name") == GEOBR_DATA_RELEASE:
                    for asset in release.get("assets", []):
                        fname = asset.get("name", "")
                        if fname.endswith(".parquet"):
                            rows.append({"file_name": fname})
                    break
        if not rows:
            raise ConnectionError("Could not list geobr_prep_data v2.0.0 assets.")
        temp_meta = pd.DataFrame(rows)
    except Exception as e:
        raise ConnectionError(
            "Failed to download v2 metadata. Check your internet connection."
        ) from e

    temp_meta["geo"] = temp_meta["file_name"].str.extract(r"^([^_]+)", expand=False)
    temp_meta["year"] = pd.to_numeric(
        temp_meta["file_name"].str.extract(r"(\d+)", expand=False), errors="coerce"
    )
    # Matched without a regex on purpose. Under pandas 3 strings are
    # Arrow-backed, so a regex match dispatches to
    # `pyarrow.compute.match_substring_regex`, which is missing from pyarrow
    # builds compiled without RE2 - QGIS ships one, so `case=False` there
    # raised AttributeError and no reader could resolve its metadata.
    temp_meta["simplified"] = (
        temp_meta["file_name"].str.lower().str.contains(
            "simplified", na=False, regex=False
        )
    )
    temp_meta.to_parquet(cache_meta, index=False)
    return temp_meta


def select_metadata_v2(geography, year, simplified=True, verbose=False, zone=None) -> pd.Series:
    """Filter v2 metadata by geography, year, and simplified flag."""
    metadata = download_metadata_v2()
    temp_meta = metadata[metadata["geo"] == geography].copy()
    if len(temp_meta) == 0:
        available = ", ".join(sorted(metadata["geo"].unique()))
        raise ValueError(
            f"Geography {geography!r} not found in v2 metadata. Available: {available}"
        )
    years_available = sorted(temp_meta["year"].dropna().unique())
    if year is None:
        year = int(max(years_available))
    elif int(year) not in [int(y) for y in years_available]:
        raise ValueError(
            f"Data currently available only for the following year/date: "
            f"{', '.join(str(int(y)) for y in years_available)}."
        )
    if verbose:
        print(f"Using year/date {year}")
    temp_meta = temp_meta[temp_meta["year"] == int(year)]
    temp_meta = temp_meta[temp_meta["simplified"] == bool(simplified)]
    if len(temp_meta) == 0:
        raise ValueError(
            f"No {'simplified' if simplified else 'original'} data for "
            f"{geography} in year {year}."
        )

    # used for read_census_tract
    if zone:
        # regex=False for the same reason as download_metadata_v2: `zone` is a
        # literal ("urban"/"rural"), and the regex path needs an RE2-enabled
        # pyarrow that QGIS does not ship.
        temp_meta = temp_meta[
            temp_meta["file_name"].str.contains(zone, regex=False)
        ]

    return temp_meta.iloc[0]


def download_parquet(
    filename_to_download: str,
    download_url: str,
    show_progress: bool = True,
    cache: bool = True,
) -> Path:
    """Download a parquet file from lates geobr_prep_data release. Returns a local path."""
    dest = cached_path(filename_to_download)
    if cache and is_cached(filename_to_download):
        return dest
    urls = [
        download_url,
        f"{IPEA_FALLBACK_BASE}/{filename_to_download}",
    ]
    if not _download_file(urls, dest, show_progress=show_progress):
        raise ConnectionError(
            "A file may have been corrupted during download. "
            "Please try again or report at https://github.com/ipea/geobr/issues"
        )
    return dest


def read_geobr_v2(
    geography: str,
    year: int,
    code: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
    connection=None,
    view_name: Optional[str] = None,
    zone=None,
):
    """Shared v2 read pipeline: metadata -> parquet -> filter -> convert output."""
    row = select_metadata_v2(geography, year, simplified=simplified, verbose=verbose, zone=zone)
    path = download_parquet(
        row["file_name"],
        row["download_url"],
        show_progress=show_progress,
        cache=cache,
    )
    if view_name is None:
        view_name = f"{geography}_{year}"

    conn = connection or duckdb_connection()

    relation = read_filter_parquet_relation(
        path,
        filter_code=code,
        connection=conn,
        view_name=view_name,
    )

    return convert_output(
        relation,
        output=output,
        connection=conn,
    )


def _simplified_attempts(preferred: bool) -> list[bool]:
    """Try preferred flag first; when True was requested, also try original geometry."""
    return [True, False] if preferred else [False]


def read_geobr_hybrid(
    geography_v2: str,
    geography_gpkg: str,
    year: int,
    code: str = "all",
    simplified: bool = True,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
    connection=None,
    view_name: Optional[str] = None,
):
    """Try v2 parquet pipeline; fall back to legacy gpkg on failure."""
    last_exc = None
    for simp in _simplified_attempts(simplified):
        try:
            return read_geobr_v2(
                geography_v2,
                year,
                code=code,
                simplified=simp,
                output=output,
                show_progress=show_progress,
                cache=cache,
                verbose=verbose,
                connection=connection,
                view_name=view_name,
            )
        except (ValueError, ConnectionError, KeyError) as exc:
            last_exc = exc

    for simp in _simplified_attempts(simplified):
        try:
            metadata = select_metadata(
                geography_gpkg, year=year, simplified=simp
            )
            gdf = download_gpkg(metadata)
            if code != "all":
                from geobr._filter import filter_by_code

                gdf = filter_by_code(gdf, code)
            return gdf
        except Exception as exc:
            last_exc = exc

    if last_exc is not None:
        raise last_exc
    raise ValueError(
        f"Could not load {geography_v2!r} for year {year}."
    )


def strip_accents(text):
    """
    Strip accents from input String.

    Parameters
    ----------
    text: str, The input string

    Returns
    ----------
    str, The processed string
    """
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore")
    text = text.decode("utf-8")
    return str(text)
