from __future__ import annotations

import pandas as pd

from geobr import utils


def _format_name(name: str) -> str:
    name = str(name).lower().strip()
    return utils.strip_accents(name)


def _jaro(a: str, b: str) -> float:
    """Jaro similarity of two strings, in ``[0, 1]``.

    The textbook definition (matching window ``max(len) // 2 - 1``, half the
    transpositions), which is what both DuckDB's ``jaro_similarity`` and
    rapidfuzz's ``Jaro.similarity`` implement — so the 0.9 threshold below
    keeps the meaning it had under either engine. Pure Python on purpose: a
    lookup helper must not need a SQL engine, and 5 570 municipality names
    take well under a second.
    """
    if a == b:
        return 1.0
    len_a, len_b = len(a), len(b)
    if not len_a or not len_b:
        return 0.0

    window = max(max(len_a, len_b) // 2 - 1, 0)
    matched_a = [False] * len_a
    matched_b = [False] * len_b
    matches = 0
    for i, char in enumerate(a):
        lo, hi = max(0, i - window), min(len_b, i + window + 1)
        for j in range(lo, hi):
            if not matched_b[j] and b[j] == char:
                matched_a[i] = matched_b[j] = True
                matches += 1
                break
    if not matches:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len_a):
        if not matched_a[i]:
            continue
        while not matched_b[k]:
            k += 1
        if a[i] != b[k]:
            transpositions += 1
        k += 1
    transpositions //= 2

    return (
        matches / len_a + matches / len_b + (matches - transpositions) / matches
    ) / 3


def _fuzzy_match_name(df: pd.DataFrame, target: str, threshold: float = 0.9) -> pd.DataFrame:
    """Rows tied at the best Jaro similarity to ``target`` on the ``_fmt`` column.

    Empty when the best score does not clear ``threshold``. Every row tied at
    the best score is returned, so homonyms (Bom Jesus in PI, RN, ...) come back
    together instead of one being picked silently — mirroring the R package.
    """
    scores = df["_fmt"].map(lambda name: _jaro(target, name))
    best = scores.max()
    if pd.isna(best) or best <= threshold:
        return df.iloc[0:0]
    return df[scores == best]


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
