from __future__ import annotations

import duckdb
import pandas as pd

from geobr import utils


def _format_name(name: str) -> str:
    name = str(name).lower().strip()
    return utils.strip_accents(name)


def _fuzzy_match_name(df: pd.DataFrame, target: str, threshold: float = 0.9) -> pd.DataFrame:
    """Rows tied at the best Jaro similarity to ``target`` on the ``_fmt`` column.

    Uses DuckDB's built-in ``jaro_similarity`` (same metric and scale as the
    former rapidfuzz implementation), mirroring the R package. The user string
    is bound as a parameter, never interpolated into the SQL.
    """
    munis = df.assign(_pos=range(len(df)))
    con = duckdb.connect()
    try:
        con.register("munis", munis)
        rows = con.execute(
            """
            SELECT _pos, jaro_similarity(?, _fmt) AS sim
            FROM munis
            QUALIFY sim > ? AND sim = max(sim) OVER ()
            """,
            [target, threshold],
        ).fetchall()
    finally:
        con.close()
    return df.iloc[[pos for pos, _ in rows]]


def lookup_muni(
    year: int = 2010,
    name_muni=None,
    code_muni=None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Lookup municipality codes and administrative region codes.

    Parameters
    ----------
    year : int
        Year of municipal seat reference data.
    name_muni : str, optional
        Municipality name to look up.
    code_muni : str or int, optional
        Municipality code to look up. Accepts the 7-digit IBGE code or the
        6-digit code without the check digit, as used by DATASUS.
    verbose : bool
        Print informational messages.

    Returns
    -------
    pandas.DataFrame
        Municipality and region identifiers (geometry dropped).
    """
    if name_muni is not None and code_muni is not None:
        if name_muni != "all" and code_muni != "all":
            raise ValueError(
                "Arguments 'name_muni' and 'code_muni' cannot be used at the same time."
            )

    if name_muni is None and code_muni is None:
        raise ValueError("Please insert a valid municipality name or code.")

    from geobr.read_municipal_seat import read_municipal_seat

    gdf = read_municipal_seat(year=year, verbose=verbose)
    df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore"))

    if name_muni == "all" or code_muni == "all":
        if verbose:
            print("Returning results for all municipalities")
        return df

    if code_muni is not None:
        if isinstance(code_muni, float) and code_muni.is_integer():
            code_muni = int(code_muni)
        code = str(code_muni).strip()
        if not code.isdigit() or len(code) not in (6, 7):
            raise ValueError(f"Please insert a valid municipality code: {code_muni}")
        codes = df["code_muni"].astype("int64")
        if len(code) == 6:
            # 6-digit codes (used by DATASUS) omit the IBGE check digit.
            codes = codes // 10
        out = df[codes == int(code)]
        if len(code) == 6 and len(out) > 1:
            # Historical years use synthetic codes without a check digit, so
            # the 6-digit prefix is not unique there.
            raise ValueError(
                f"The 6-digit code {code} matches {len(out)} municipalities in "
                f"{year}. Please use the 7-digit code."
            )
        if len(out) == 0:
            raise ValueError(f"Please insert a valid municipality code: {code_muni}")
        if verbose:
            print(f"Returning results for municipality {out['name_muni'].iloc[0]}")
        return out

    target = _format_name(name_muni)
    df["_fmt"] = df["name_muni"].apply(_format_name)
    out = df[df["_fmt"] == target]

    if len(out) == 0:
        out = _fuzzy_match_name(df, target)
        if len(out) == 0:
            raise ValueError("Please insert a valid municipality name.")

    if verbose:
        print(f"Returning results for municipality {out['name_muni'].iloc[0]}")
    return out.drop(columns="_fmt")
