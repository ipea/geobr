"""Spatial filtering helpers (port of R filter_arrw).

Three consumers share one column resolver, :func:`resolve_filter`:

* :func:`filter_by_code` filters an in-memory GeoDataFrame (legacy gpkg path);
* :func:`parquet_filters` builds the pyarrow ``filters`` that
  ``read_geobr_v2`` pushes down into ``gpd.read_parquet`` / ``pq.read_table``;
* ``_duckdb_backend.read_filter_parquet_relation`` keeps its own SQL twin of
  the same rules for ``output="duckdb"``.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Optional, Union

import geopandas as gpd
import pandas as pd

# Brazilian state codes and abbreviations (IBGE)
ALL_CODE_STATE = [str(i).zfill(2) for i in range(11, 54) if i not in (20, 30, 40)]
ALL_ABBREV_STATE = [
    "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE",
    "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO",
    "DF",
]

INVALID_CODE_MESSAGE = "Invalid value to argument `code_` / `code_muni` / `code_state`."


def _normalize_code(code: Any) -> Union[str, list]:
    if code == "all" or code is None:
        return "all"
    if isinstance(code, (list, tuple)):
        return [_normalize_code_single(c) for c in code]
    return _normalize_code_single(code)


def _normalize_code_single(code: Any) -> str:
    if isinstance(code, int):
        return str(code)
    return str(code).strip().upper() if isinstance(code, str) and code.isalpha() else str(code)


def _numbers_only(x: str) -> bool:
    return bool(re.fullmatch(r"\d+", str(x)))


def code_length(values: pd.Series) -> Optional[int]:
    """Digit count of the longest non-null code in ``values``.

    The release parquet files store every ``code_*`` column as ``double``, so
    ``str(3304.0)`` is six characters, not four. Measuring on the integer value
    is what lets the digit-length heuristic in :func:`resolve_filter` match on
    real data (the R side does the same through ``CAST(... AS BIGINT)``).
    """
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if len(numeric):
        return int(numeric.astype("int64").astype(str).str.len().max())
    text = values.dropna().astype(str)
    return int(text.str.len().max()) if len(text) else None


def resolve_filter(
    columns: Iterable[str],
    code: Any,
    max_code_len: Callable[[str], Optional[int]],
) -> tuple[str, list]:
    """Which column a ``code`` filter applies to, and the values to match.

    Mirrors R ``filter_arrw()``: a two-letter abbreviation filters
    ``abbrev_state``; a one/two-digit state code filters ``code_state``; a
    seven-digit code filters ``code_muni``; any other code of more than three
    digits filters the first other ``code_*`` column whose longest value has the
    same number of digits (``max_code_len`` measures that, per column, so the
    caller decides how to read the data).

    Returns ``(column, codes)``; numeric branches return ``int`` values.
    Raises ``ValueError`` when nothing resolves. ``"all"`` is the caller's job.
    """
    codes = _normalize_code(code)
    if codes == "all":
        raise ValueError("resolve_filter() does not handle 'all'; the caller must.")
    if not isinstance(codes, list):
        codes = [codes]
    columns = list(columns)

    if all(c in ALL_ABBREV_STATE for c in codes):
        if "abbrev_state" in columns:
            return "abbrev_state", codes
    elif all(
        _numbers_only(c) and len(c) <= 2
        and (c.zfill(2) in ALL_CODE_STATE or c in ALL_CODE_STATE)
        for c in codes
    ):
        if "code_state" in columns:
            return "code_state", [int(c) for c in codes]
    elif all(_numbers_only(c) and len(c) == 7 for c in codes):
        if "code_muni" in columns:
            return "code_muni", [int(c) for c in codes]
    elif all(_numbers_only(c) and len(c) > 3 for c in codes):
        candidates = [
            c for c in columns
            if c.startswith("code_") and c not in ("code_state", "code_muni")
        ]
        for column in candidates:
            if max_code_len(column) == len(codes[0]):
                return column, [int(c) for c in codes]

    raise ValueError(INVALID_CODE_MESSAGE)


def filter_by_code(
    gdf: gpd.GeoDataFrame,
    code: Any = "all",
) -> gpd.GeoDataFrame:
    """Filter a GeoDataFrame by state abbrev, state code, municipality code, or other code_* column.

    Mirrors R ``filter_arrw()`` behavior for in-memory GeoDataFrames.
    """
    if gdf is None or len(gdf) == 0:
        return gdf

    if code == "all" or code is None:
        return gdf

    column, codes = resolve_filter(gdf.columns, code, lambda col: code_length(gdf[col]))

    if column == "abbrev_state":
        result = gdf[gdf[column].isin(codes)]
    elif column == "code_state":
        gdf = gdf.copy()
        gdf[column] = pd.to_numeric(gdf[column], errors="coerce")
        result = gdf[gdf[column].isin(codes)]
    elif column == "code_muni":
        gdf = gdf.copy()
        gdf[column] = pd.to_numeric(gdf[column], errors="coerce").astype("Int64")
        result = gdf[gdf[column].isin(codes)]
        if len(result) == 0:
            result = gdf[gdf[column].astype(str).isin([str(c) for c in codes])]
    else:
        numeric = pd.to_numeric(gdf[column], errors="coerce")
        result = gdf[numeric.isin(codes)]
        if len(result) == 0:
            result = gdf[gdf[column].astype(str).isin([str(c) for c in codes])]

    if len(result) == 0:
        raise ValueError(INVALID_CODE_MESSAGE)

    return result


def parquet_filters(path, code: Any) -> Optional[list]:
    """pyarrow ``filters`` for ``code`` against the parquet at ``path``.

    ``None`` for ``"all"``. The column is resolved from the file's schema; on the
    digit-length branch only the candidate ``code_*`` columns are read to measure
    lengths (columnar, cheap). Values are typed from the schema field: pyarrow
    will not compare a ``string`` list against a ``double`` column, and older
    files (health facilities) carry string code columns.
    """
    if code == "all" or code is None:
        return None

    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = pq.read_schema(path)
    candidates = [
        n for n in schema.names
        if n.startswith("code_") and n not in ("code_state", "code_muni")
    ]
    lengths: dict[str, Optional[int]] = {}

    def max_code_len(column: str) -> Optional[int]:
        if not lengths:
            table = pq.read_table(path, columns=candidates)
            for name in candidates:
                lengths[name] = code_length(table.column(name).to_pandas())
        return lengths.get(column)

    column, codes = resolve_filter(schema.names, code, max_code_len)

    field_type = schema.field(column).type
    if pa.types.is_string(field_type) or pa.types.is_large_string(field_type):
        codes = [str(c) for c in codes]
    elif pa.types.is_floating(field_type):
        codes = [float(c) for c in codes]
    elif pa.types.is_integer(field_type):
        codes = [int(c) for c in codes]

    return [(column, "in", codes)]
