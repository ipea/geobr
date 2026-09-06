"""Download data of Brazilian state capitals."""

from __future__ import annotations

import pandas as pd

from geobr.read_municipal_seat import read_municipal_seat
from geobr._docstrings import docparams

_CAPITALS = pd.DataFrame(
    {
        "name_muni": [
            "São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Fortaleza",
            "Vitória", "Goiânia", "Cuiabá", "São Luís", "Teresina", "Recife", "Aracaju",
            "João Pessoa", "Natal", "Maceió", "Porto Alegre", "Curitiba", "Florianópolis",
            "Belém", "Manaus", "Palmas", "Campo Grande", "Macapá", "Rio Branco",
            "Boa Vista", "Brasília", "Porto Velho",
        ],
        "code_muni": [
            3550308, 3304557, 3106200, 2927408, 2304400, 3205309, 5208707, 5103403,
            2111300, 2211001, 2611606, 2800308, 2507507, 2408102, 2704302, 4314902,
            4106902, 4205407, 1501402, 1302603, 1721000, 5002704, 1600303, 1200401,
            1400100, 5300108, 1100205,
        ],
        "name_state": [
            "São Paulo", "Rio de Janeiro", "Minas Gerais", "Bahia", "Ceará",
            "Espírito Santo", "Goiás", "Mato Grosso", "Maranhão", "Piauí", "Pernambuco",
            "Sergipe", "Paraíba", "Rio Grande do Norte", "Alagoas", "Rio Grande do Sul",
            "Paraná", "Santa Catarina", "Pará", "Amazonas", "Tocantins",
            "Mato Grosso do Sul", "Amapá", "Acre", "Roraima", "Distrito Federal",
            "Rondônia",
        ],
        "code_state": [
            35, 33, 31, 29, 23, 32, 52, 51, 21, 22, 26, 28, 25, 24, 27, 43, 41, 42,
            15, 13, 17, 50, 16, 12, 14, 53, 11,
        ],
    }
).sort_values("code_muni")


@docparams
def read_capitals(
    year: int = 2010,
    output: str = "gpd",
    show_progress: bool = True,
    cache: bool = True,
    verbose: bool = False,
):
    """Download spatial or tabular data for the 27 state capitals.

    Parameters
    ----------
    {year}
    {output}
    {show_progress}
    {cache}
    {verbose}

    """
    codes = _CAPITALS["code_muni"].tolist()

    return read_municipal_seat(
        year=year,
        code_muni=codes,
        output=output,
        show_progress=show_progress,
        cache=cache,
        verbose=verbose
    )
