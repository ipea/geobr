"""List available geobr datasets."""

from __future__ import annotations

import pandas as pd

from geobr.utils import download_metadata_v2

_CATALOG = pd.DataFrame(
    {
        "Function": [
            "read_country", "read_region", "read_state", "read_meso_region",
            "read_micro_region", "read_intermediate_region", "read_immediate_region",
            "read_municipality", "read_municipal_seat", "read_weighting_area",
            "read_census_tract", "read_statistical_grid", "read_metro_area",
            "read_urban_area", "read_amazon", "read_biomes",
            "read_conservation_units", "read_disaster_risk_area",
            "read_indigenous_land", "read_semiarid", "read_health_facilities",
            "read_health_region", "read_neighborhood", "read_schools",
            "read_comparable_areas", "read_urban_concentrations",
            "read_pop_arrangements", "read_favela", "read_polling_places",
            "read_quilombola_land", "read_addresses",
        ],
        "geography": [
            "Country", "Region", "States", "Meso region", "Micro region",
            "Intermediate region", "Immediate region", "Municipality",
            "Municipality seats", "Census weighting area", "Census tract",
            "Statistical Grid", "Metropolitan areas", "Urban footprints",
            "Brazil's Legal Amazon", "Biomes", "Conservation Units",
            "Disaster risk areas", "Indigenous lands", "Semi Arid region",
            "Health facilities", "Health regions", "Neighborhood limits",
            "Schools", "Comparable municipalities (AMCs)",
            "Urban concentrations", "Population arrangements",
            "Favelas", "Polling places", "Quilombola lands",
            "Addresses (CNEFE)",
        ],
        "source": [
            "IBGE", "IBGE", "IBGE", "IBGE", "IBGE", "IBGE", "IBGE", "IBGE", "IBGE",
            "IBGE", "IBGE", "IBGE", "IBGE", "IBGE", "MMA", "IBGE", "MMA",
            "CEMADEN/IBGE", "FUNAI", "IBGE", "CNES", "DataSUS", "IBGE", "INEP",
            "IBGE", "IBGE", "IBGE", "IBGE", "TSE", "INCRA", "IBGE",
        ],
        "alias": [
            "country", "regions", "states", "mesoregions", "microregions",
            "intermediateregions", "immediateregions", "municipalities",
            "municipalseats", "weightingareas", "censustracts", "statsgrid",
            "metroarea", "urbanareas", "amazonialegal", "biomes",
            "conservationunits", "disasterriskareas", "indigenouslands",
            "semiarid", "healthfacilities", "healthregions", "neighborhoods",
            "schools", "amc", "poparrangements", "poparrangements",
            "favelas", "pollingplaces", "quilombolalands", "cnefe",
        ],
    }
)


def list_geobr(wide: bool = True) -> pd.DataFrame:
    """Return a catalog of geobr datasets with available years from live metadata.

    Parameters
    ----------
    wide : bool
        If True (default), years are comma-separated per function. If False, long format.

    Returns
    -------
    pandas.DataFrame
        Dataset catalog joined with available years.
    """
    try:
        meta = download_metadata_v2()
        years_df = (
            meta.groupby("geo")["year"]
            .apply(lambda s: ", ".join(str(int(y)) for y in sorted(s.dropna().unique())))
            .reset_index()
            .rename(columns={"geo": "alias", "year": "years_available"})
        )
        out = _CATALOG.merge(years_df, on="alias", how="left")
        if "years_available" not in out.columns:
            out["years_available"] = None
    except Exception:
        out = _CATALOG.copy()
        out["years_available"] = None

    if wide:
        return out

    out["year"] = out["years_available"].fillna("").str.split(", ")
    out_expandido = out.explode("year")
    out_expandido["year"] = out_expandido["year"].str.strip()
    out_expandido = out_expandido.drop(columns=["years_available"])
    return out_expandido
