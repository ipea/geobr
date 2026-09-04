"""DuckDB backend for lazy parquet reads, SQL queries, and spatial analysis."""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any, Optional, Union
import duckdb

_CONN: Optional[Any] = None
_LAST_REGISTERED: dict[tuple[int, str], tuple[str, int]] = {}
_MAX_RESOLUTIONS = 10
_MISSING_TABLE_RE = re.compile(
    r'Table with name "?([^"\s]+)"? does not exist', re.IGNORECASE
)

# geo alias -> (v2 geography, optional gpkg fallback, read_* function name)
_GEO_LOADERS: dict[str, dict[str, Any]] = {
    "schools": {"v2": "schools", "gpkg": "schools", "read_fn": "read_schools"},
    "states": {"v2": "states", "gpkg": "state", "read_fn": "read_state"},
    "biomes": {"v2": "biomes", "gpkg": "biomes", "read_fn": "read_biomes"},
    "healthfacilities": {
        "v2": "healthfacilities",
        "gpkg": "health_facilities",
        "read_fn": "read_health_facilities",
        "year_param": "date",
    },
    "indigenousland": {
        "v2": "indigenousland",
        "gpkg": "indigenous_land",
        "read_fn": "read_indigenous_land",
        "year_param": "date",
    },
    "conservationunits": {
        "v2": "conservationunits",
        "gpkg": "conservation_units",
        "read_fn": "read_conservation_units",
        "year_param": "date",
    },
    "disasterriskareas": {
        "v2": "disasterriskareas",
        "gpkg": "disaster_risk_area",
        "read_fn": "read_disaster_risk_area",
    },
    "neighborhoods": {
        "v2": "neighborhoods",
        "gpkg": "neighborhood",
        "read_fn": "read_neighborhood",
    },
    "metropolitanarea": {
        "v2": "metropolitanarea",
        "gpkg": "metropolitan_area",
        "read_fn": "read_metro_area",
    },
    "urbanconcentrations": {
        "v2": "poparrangements",
        "gpkg": "urban_concentrations",
        "read_fn": "read_urban_concentrations",
    },
    "poparrangements": {
        "v2": "poparrangements",
        "gpkg": "pop_arrengements",
        "read_fn": "read_pop_arrangements",
    },
    "healthregions": {
        "v2": "healthregions",
        "gpkg": "health_region",
        "read_fn": "read_health_region",
    },
    "municipalities": {
        "v2": "municipalities",
        "gpkg": "municipality",
        "read_fn": "read_municipality",
    },
    "statsgrid": {
        "v2": "statsgrid",
        "gpkg": "statistical_grid",
        "read_fn": "read_statistical_grid",
    },
    "favelas": {"v2": "favelas", "gpkg": None, "read_fn": "read_favela", "v2_only": True},
    "pollingplaces": {
        "v2": "pollingplaces",
        "gpkg": None,
        "read_fn": "read_polling_places",
        "v2_only": True,
    },
    "quilombolalands": {
        "v2": "quilombolalands",
        "gpkg": None,
        "read_fn": "read_quilombola_land",
        "v2_only": True,
    },
    "country": {"v2": "country", "gpkg": "country", "read_fn": "read_country"},
    "regions": {"v2": "regions", "gpkg": "region", "read_fn": "read_region"},
    "mesoregions": {"v2": "mesoregions", "gpkg": "meso_region", "read_fn": "read_meso_region"},
    "microregions": {"v2": "microregions", "gpkg": "micro_region", "read_fn": "read_micro_region"},
    "intermediateregions": {
        "v2": "intermediateregions",
        "gpkg": "intermediate_region",
        "read_fn": "read_intermediate_region",
    },
    "immediateregions": {
        "v2": "immediateregions",
        "gpkg": "immediate_region",
        "read_fn": "read_immediate_region",
    },
    "municipalseats": {
        "v2": "municipalseats",
        "gpkg": "municipal_seat",
        "read_fn": "read_municipal_seat",
    },
    "weightingareas": {
        "v2": "weightingareas",
        "gpkg": "weighting_area",
        "read_fn": "read_weighting_area",
    },
    "censustracts": {
        "v2": "censustracts",
        "gpkg": "census_tract",
        "read_fn": "read_census_tract",
    },
    "urbanareas": {"v2": "urbanareas", "gpkg": "urban_area", "read_fn": "read_urban_area"},
    "amazonialegal": {"v2": "amazonialegal", "gpkg": "amazon", "read_fn": "read_amazon"},
    "semiarid": {"v2": "semiarid", "gpkg": "semiarid", "read_fn": "read_semiarid"},
    "amc": {
        "v2": "amc",
        "gpkg": "comparable_areas",
        "read_fn": "read_comparable_areas",
    },
}

# Geographies that are point layers: there is nothing to simplify, so the data
# release ships no `*_simplified.parquet` asset for them and asking for one
# raises in `select_metadata_v2()`. The public readers encode this by passing
# `simplified=False`; this set is the same fact for the SQL/session path.
#
# `tests/test_point_geographies.py` checks this set against the live metadata,
# so upstream drift surfaces in CI rather than in a user's query.
POINT_GEOGRAPHIES = frozenset(
    {
        "healthfacilities",
        "municipalseats",
        "pollingplaces",
        "schools",
        "statsgrid",
    }
)


def _resolve_simplified(geo: str, simplified: Optional[bool]) -> bool:
    """Resolve the `simplified` flag for `geo`.

    `None` means the caller did not choose, so point layers resolve to False.
    An explicit True on a point layer is downgraded with a warning rather than
    left to fail deeper in `select_metadata_v2()`.
    """
    if geo not in POINT_GEOGRAPHIES:
        return True if simplified is None else bool(simplified)

    if simplified:
        warnings.warn(
            f"{geo!r} is a point layer and has no simplified variant; "
            "reading the original geometry instead.",
            UserWarning,
            stacklevel=3,
        )
    return False


def _setup_connection(conn) -> None:
    for stmt in (
        "INSTALL spatial",
        "LOAD spatial",
        "INSTALL httpfs",
        "LOAD httpfs",
    ):
        try:
            conn.execute(stmt)
        except Exception:
            pass


def _create_connection():
    conn = duckdb.connect()
    _setup_connection(conn)
    return conn


def duckdb_connection():
    """Return the shared DuckDB connection (loads spatial + httpfs once)."""
    global _CONN
    if _CONN is None:
        _CONN = _create_connection()
    return _CONN


def _reset_shared_connection() -> None:
    """Close and reset the module-level shared connection (for tests)."""
    global _CONN
    if _CONN is not None:
        try:
            _CONN.close()
        except Exception:
            pass
    _CONN = None
    _LAST_REGISTERED.clear()


def register_dataset(
    name: str,
    parquet_path: Union[str, Path],
    *,
    connection: Optional[Any] = None,
) -> Any:
    """Register a parquet file as a DuckDB view and return the relation."""
    conn = connection or duckdb_connection()
    path_str = str(Path(parquet_path).resolve()).replace("'", "''")
    safe_name = name.replace('"', '""')
    conn.execute(
        f'CREATE OR REPLACE VIEW "{safe_name}" AS '
        f"SELECT * FROM read_parquet('{path_str}')"
    )
    return conn.sql(f'SELECT * FROM "{safe_name}"')


def _parse_missing_table(exc: Exception) -> Optional[str]:
    match = _MISSING_TABLE_RE.search(str(exc))
    if match:
        return match.group(1)
    return None


def _known_geos() -> set[str]:
    try:
        from geobr.utils import download_metadata_v2

        meta = download_metadata_v2()
        return set(meta["geo"].dropna().unique())
    except Exception:
        return set(_GEO_LOADERS.keys())


def _available_years(geo: str) -> list[int]:
    try:
        from geobr.utils import download_metadata_v2

        meta = download_metadata_v2()
        subset = meta.loc[meta["geo"] == geo, "year"].dropna()
        return sorted(int(y) for y in subset.unique())
    except Exception:
        return []


def _cached_years(geo: str) -> list[int]:
    from geobr._cache import cache_dir

    years: list[int] = []
    for path in cache_dir().glob(f"{geo}_*.parquet"):
        match = re.match(rf"^{re.escape(geo)}_(\d+)", path.name)
        if match:
            years.append(int(match.group(1)))
    return sorted(set(years))


def _registered_years(geo: str, connection) -> list[tuple[str, int]]:
    prefix = f"{geo}_"
    rows = connection.execute("SHOW TABLES").fetchall()
    found: list[tuple[str, int]] = []
    for (table_name,) in rows:
        if table_name == geo:
            key = (id(connection), geo)
            if key in _LAST_REGISTERED:
                view_name, year = _LAST_REGISTERED[key]
                found.append((view_name, year))
            continue
        if table_name.startswith(prefix):
            suffix = table_name[len(prefix) :]
            if suffix.isdigit():
                found.append((table_name, int(suffix)))
    return found


def _resolve_table_name(name: str) -> tuple[str, Optional[int], bool]:
    """Return (geo, year_or_date, is_bare)."""
    known = _known_geos()
    if name in known:
        return name, None, True

    if "_" in name:
        geo, suffix = name.rsplit("_", 1)
        if suffix.isdigit() and geo in known:
            return geo, int(suffix), False
        if geo in known:
            raise ValueError(
                f"Invalid year/date suffix in table {name!r}. "
                f"Available years for {geo}: "
                f"{', '.join(str(y) for y in _available_years(geo))}."
            )

    available = ", ".join(sorted(_known_geos()))
    raise ValueError(
        f"Unknown geobr table {name!r}. Available geographies: {available}."
    )


def _format_bare_year_warning(geo: str, year: int, *, from_cache: bool) -> str:
    years = _available_years(geo)
    years_str = ", ".join(str(y) for y in years) if years else "unknown"
    loader = _GEO_LOADERS.get(geo, {})
    read_fn = loader.get("read_fn", f"read_{geo}")
    year_param = loader.get("year_param", "year")
    if from_cache:
        intro = f"FROM {geo}: no year specified, using cached year {year}."
    else:
        intro = (
            f"FROM {geo}: no year specified, using year {year} "
            f"(most recent available)."
        )
    return (
        f"{intro} To choose a year, use FROM {geo}_{year} in SQL or call "
        f"{read_fn}({year_param}={year}, output='duckdb') first. "
        f"Available years: {years_str}."
    )


def _pick_bare_year(
    geo: str,
    connection,
) -> tuple[int, bool, bool]:
    """Return (year, from_cache, should_warn)."""
    registered = _registered_years(geo, connection)
    if len(registered) == 1:
        return registered[0][1], True, False
    if len(registered) > 1:
        key = (id(connection), geo)
        if key in _LAST_REGISTERED:
            _, year = _LAST_REGISTERED[key]
            return year, True, False
        return registered[-1][1], True, True

    cached = _cached_years(geo)
    if cached:
        return cached[-1], True, True

    available = _available_years(geo)
    if not available:
        raise ValueError(f"No years available for geography {geo!r}.")
    return available[-1], False, True


def _register_alias(geo: str, year: int, connection) -> None:
    suffixed = f"{geo}_{year}"
    safe_geo = geo.replace('"', '""')
    safe_suffixed = suffixed.replace('"', '""')
    connection.execute(
        f'CREATE OR REPLACE VIEW "{safe_geo}" AS SELECT * FROM "{safe_suffixed}"'
    )


def _track_registration(connection, geo: str, view_name: str, year: int) -> None:
    _LAST_REGISTERED[(id(connection), geo)] = (view_name, year)


def _load_geo_dataset(
    geo: str,
    year: int,
    *,
    connection,
    simplified: Optional[bool] = None,
    code: str = "all",
) -> Any:
    view_name = f"{geo}_{year}"
    loader = _GEO_LOADERS.get(geo)
    if loader is None:
        available = ", ".join(sorted(_known_geos()))
        raise ValueError(
            f"Geography {geo!r} cannot be auto-loaded. Available: {available}."
        )

    simplified = _resolve_simplified(geo, simplified)

    from geobr.utils import read_geobr_hybrid, read_geobr_v2

    common = dict(
        year=year,
        code=code,
        simplified=simplified,
        output="duckdb",
        show_progress=False,
        cache=True,
        connection=connection,
        view_name=view_name,
    )
    if loader.get("v2_only") or loader.get("gpkg") is None:
        result = read_geobr_v2(geography=loader["v2"], **common)
    else:
        result = read_geobr_hybrid(loader["v2"], loader["gpkg"], **common)

    _track_registration(connection, geo, view_name, year)
    return result


def _resolve_missing_table(table_name: str, connection) -> None:
    geo, year, is_bare = _resolve_table_name(table_name)

    if is_bare:
        year, from_cache, should_warn = _pick_bare_year(geo, connection)
        if should_warn:
            warnings.warn(
                _format_bare_year_warning(geo, year, from_cache=from_cache),
                UserWarning,
                stacklevel=4,
            )
        suffixed = f"{geo}_{year}"
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        if suffixed not in tables:
            _load_geo_dataset(geo, int(year), connection=connection)
        _register_alias(geo, int(year), connection)
        return

    available = _available_years(geo)
    if available and int(year) not in available:
        raise ValueError(
            f"Year {year} not available for {geo}. "
            f"Available years: {', '.join(str(y) for y in available)}."
        )

    _load_geo_dataset(geo, int(year), connection=connection)


def query(
    sql: str,
    *,
    connection: Optional[Any] = None,
    params: Optional[Union[list, dict]] = None,
) -> Any:
    """Run SQL on DuckDB, auto-resolving missing geobr snapshot views."""
    conn = connection or duckdb_connection()
    resolutions = 0
    while True:
        try:
            if params is None:
                return conn.sql(sql)
            return conn.execute(sql, params)
        except Exception as exc:
            exc_name = exc.__class__.__name__
            if "Catalog" not in exc_name and "catalog" not in str(exc).lower():
                raise
            missing = _parse_missing_table(exc)
            if missing is None:
                raise
            if resolutions >= _MAX_RESOLUTIONS:
                raise RuntimeError(
                    f"Exceeded {_MAX_RESOLUTIONS} auto-resolutions while running query."
                ) from exc
            _resolve_missing_table(missing, conn)
            resolutions += 1


def _relation_sql(rel_or_name: Union[str, Any]) -> str:
    if isinstance(rel_or_name, str):
        safe = rel_or_name.replace('"', '""')
        return f'"{safe}"'
    if hasattr(rel_or_name, "sql"):
        return f"({rel_or_name.sql()})"
    raise TypeError("`rel_or_name` must be a view name or DuckDB relation.")


def _detect_geometry_column(conn, source: str) -> Optional[str]:
    rows = conn.sql(f"DESCRIBE SELECT * FROM {source}").fetchall()
    for name, col_type, *_ in rows:
        type_upper = str(col_type).upper()
        if "GEOMETRY" in type_upper or name.lower() in ("geometry", "geom"):
            return name
    return None


def to_geopandas(
    rel_or_name: Union[str, Any],
    *,
    connection: Optional[Any] = None,
):
    """Convert a DuckDB relation or view to a GeoDataFrame."""
    import geopandas as gpd
    from shapely import from_wkb

    conn = connection or duckdb_connection()
    source = _relation_sql(rel_or_name)
    geom_col = _detect_geometry_column(conn, source)
    if geom_col is None:
        df = conn.sql(f"SELECT * FROM {source}").df()
        return gpd.GeoDataFrame(df)

    safe_geom = geom_col.replace('"', '""')
    df = conn.sql(
        f"SELECT * EXCLUDE ({safe_geom}), "
        f"ST_AsWKB({safe_geom}) AS __geom_wkb "
        f"FROM {source}"
    ).df()

    def _to_geom(value):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray, memoryview)):
            return from_wkb(bytes(value))
        if hasattr(value, "tobytes"):
            return from_wkb(value.tobytes())
        return from_wkb(value)

    geometries = df.pop("__geom_wkb").apply(_to_geom)
    return gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4674")


def read_filter_parquet_relation(
    path: Union[str, Path],
    filter_code: Any = "all",
    *,
    connection: Optional[Any] = None,
    view_name: Optional[str] = None,
):
    """Return a DuckDB relation over a parquet file."""
    if view_name:
        register_dataset(view_name, path, connection=connection)
        source = f'"{view_name.replace(chr(34), chr(34) * 2)}"'
    else:
        path_str = str(Path(path).resolve()).replace("'", "''")
        source = f"read_parquet('{path_str}')"

    if filter_code == "all" or filter_code is None:
        return connection.sql(f"SELECT * FROM {source}")

    codes = filter_code if isinstance(filter_code, (list, tuple)) else [filter_code]
    code = codes[0]

    if isinstance(code, str) and len(code) == 2 and code.isalpha():
        codes_sql = ", ".join([f"'{c}'" for c in codes])
        return connection.sql(f"SELECT * FROM {source} WHERE abbrev_state IN ({codes_sql})")
    if str(code).isdigit() and len(str(code)) == 7:
        codes_sql = ", ".join(map(str, codes))
        return connection.sql(
            f"SELECT * FROM {source} WHERE CAST(code_muni AS BIGINT) IN ({codes_sql})"
        )
    if str(code).isdigit() and len(str(code)) <= 2:
        codes_sql = ", ".join(map(str, codes))
        return connection.sql(
            f"SELECT * FROM {source} WHERE CAST(code_state AS INTEGER) IN ({codes_sql})"
        )

    rel = connection.sql(f"SELECT * FROM {source}")

    if str(code).isdigit() and len(str(code)) > 3:
        code_cols = [c for c in rel.columns if c.startswith("code_") and c not in ["code_state", "code_muni"]]
        for code_col in code_cols:
            len_alvo = rel.aggregate(f"max(length(CAST(CAST({code_col} as BIGINT) as VARCHAR)))").fetchone()[0]
            if len_alvo == len(str(code)):
                filter_col = code_col
                codes_sql = ", ".join(map(str, codes))
                return connection.sql(f"SELECT * FROM {source} WHERE CAST({filter_col} AS INTEGER) IN ({codes_sql})")

    return rel


class GeoBrDuckDB:
    """Isolated DuckDB session for geobr queries."""

    def __init__(self):
        self._conn = _create_connection()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    @property
    def connection(self):
        return self._conn

    def query(self, sql: str, *, params: Optional[Union[list, dict]] = None):
        return query(sql, connection=self._conn, params=params)

    def read(
        self,
        geo: str,
        *,
        year: Optional[int] = None,
        simplified: Optional[bool] = None,
        code: str = "all",
    ):
        if year is None:
            year, _, should_warn = _pick_bare_year(geo, self._conn)
            if should_warn:
                warnings.warn(
                    _format_bare_year_warning(geo, year, from_cache=True),
                    UserWarning,
                    stacklevel=2,
                )
        return _load_geo_dataset(
            geo, int(year), connection=self._conn, simplified=simplified, code=code
        )

    def register(self, name: str, parquet_path: Union[str, Path]):
        return register_dataset(name, parquet_path, connection=self._conn)

    def to_geopandas(self, rel_or_name: Union[str, Any]):
        return to_geopandas(rel_or_name, connection=self._conn)


def session() -> GeoBrDuckDB:
    """Open an isolated DuckDB session."""
    return GeoBrDuckDB()
