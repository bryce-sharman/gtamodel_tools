""" Functions to read and process traffic count data. """

import geopandas as gpd
import pandas as pd


def add_stations(
        existing_stns: gpd.GeoDataFrame | None, 
        stns_to_add: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
    """ Add stations to complete stations 'database'.

    Args:
        existing_stns: gpd.GeoDataFrame with existing stations 'database'
        stns_to_add: gpd.GeoDataFrame with new stations

    Returns:
        gpd.GeoDataFrame with revised stations database

    """
    if existing_stns is None:
        return stns_to_add.copy()
    new_stations_idx = stns_to_add.index.difference(existing_stns.index)
    new_stations = stns_to_add.loc[new_stations_idx]
    return pd.concat([existing_stns, new_stations], axis=0)


def add_counts(
        existing_cnts: pd.DataFrame | None, 
        cnts_to_add: pd.DataFrame
    ) -> pd.DataFrame:
    """ Add counts to complete counts 'database'.

    Args:
        existing_cnts: DataFrame with existing counts 'database'
        cnts_to_add: DataFrame with new counts

    Returns:
        DataFrame with revised counts 'database'

    """
    if existing_cnts is None:
        return cnts_to_add.copy()
    new_cnts_idx = cnts_to_add.index.difference(existing_cnts.index)
    new_cnts = cnts_to_add.loc[new_cnts_idx]
    return pd.concat([existing_cnts, new_cnts], axis=0)



