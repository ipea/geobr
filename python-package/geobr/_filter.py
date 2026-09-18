"""Spatial filtering helpers (port of R filter_arrw)."""

from __future__ import annotations

import re
from typing import Any, Union

import geopandas as gpd
import pandas as pd

# Brazilian state codes and abbreviations (IBGE)
ALL_CODE_STATE = [
    11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 31, 32, 33, 35, 41, 42, 43, 50,
    51, 52, 53
]
ALL_ABBREV_STATE = [
    "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE",
    "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO",
    "DF",
]


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

    codes = _normalize_code(code) # retorna str
    if not isinstance(codes, list):
        codes = [codes]

    filter_col = None

    if all(c in ALL_ABBREV_STATE for c in codes):
        if "abbrev_state" in gdf.columns:
            filter_col = "abbrev_state"
    elif all(
        _numbers_only(c) and len(c) == 2
        and (int(c) in ALL_CODE_STATE) for c in codes
    ):
        if "code_state" in gdf.columns:
            filter_col = "code_state"
            codes = [int(c) for c in codes]
    elif all(_numbers_only(c) and len(c) == 7 for c in codes):
        if "code_muni" in gdf.columns:
            filter_col = "code_muni"
            codes = [int(c) for c in codes]
    elif all(_numbers_only(c) and len(c) > 3 for c in codes):
        code_cols = [c for c in gdf.columns if c.startswith("code_") and c not in ["code_state", "code_muni"]]
        if code_cols:
            for code_col in code_cols:
                if gdf[code_col].astype(str).str.len().max() == len(str(codes[0])):
                    filter_col = code_col

    if filter_col is None:
        raise ValueError("Invalid value to argument `code_` / `code_muni` / `code_state`.")

    if filter_col == "code_state":
        gdf = gdf.copy()
        gdf[filter_col] = pd.to_numeric(gdf[filter_col], errors="coerce")
        codes_num = [int(c) for c in codes]
        result = gdf[gdf[filter_col].isin(codes_num)]
    elif filter_col == "code_muni":
        gdf = gdf.copy()
        gdf[filter_col] = pd.to_numeric(gdf[filter_col], errors="coerce").astype("Int64")
        codes_num = [int(c) for c in codes]
        result = gdf[gdf[filter_col].isin(codes_num)]
        if len(result) == 0:
            result = gdf[gdf[filter_col].astype(str).isin([str(c) for c in codes_num])]
    else:
        result = gdf[gdf[filter_col].isin(codes)]
        if len(result) == 0:
            codes_num = [int(c) for c in codes]
            result = gdf[gdf[filter_col].astype(str).isin([str(c) for c in codes_num])]

    if len(result) == 0:
        raise ValueError("Invalid value to argument `code_` / `code_muni` / `code_state`.")

    return result
