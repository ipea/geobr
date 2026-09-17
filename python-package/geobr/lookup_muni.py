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
        Municipality code to look up.
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
        code = int(code_muni)
        out = df[df["code_muni"] == code]
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
