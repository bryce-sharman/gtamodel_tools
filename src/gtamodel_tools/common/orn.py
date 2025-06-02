'''
Functions to read Ontario Road Network (ORN) shapefile.
'''

import pyogrio   # Seem to need to import before geopandas for some reason
from geopandas import read_file, GeoDataFrame
from pandas import DataFrame
from typing import List

import gtamodel_tools.enums.validation.orn as en_orn

def _read_gdb_layer(fp, layer_name, usecols):
    # Much faster to read using pyogrio engine.
    gdf = read_file(fp, layer=layer_name, engine='pyogrio')
    return gdf[usecols].copy()


def read_geometry(fp) -> GeoDataFrame:
    """ Read ORN geometry from 'ORN_ROAD_NET_ELEMENT' layer.

    Args:
        fp: path to ORN .gdb file.

    Returns:
        ORN geometry as a gpd.GeoDataFRame
    """
    gdf = _read_gdb_layer(fp, en_orn.GEOM_LAYERNAME, en_orn.GEOM_USECOLS)
    gdf[en_orn.GEOM_ELEMID_COL] = gdf[en_orn.GEOM_ELEMID_COL].astype(str)
    return gdf

def read_roadclass(fp) -> DataFrame:
    """ Read ORN road class attributes from ORN_ROAD_CLASS layer.

    Args:
        fp: path to ORN .gdb file.

    Returns:
        ORN road class information as a pandas.DataFrame
    """
    df = _read_gdb_layer(fp, en_orn.RDCLS_LAYERNAME, en_orn.RDCLS_USECOLS)
    df[en_orn.RDCLS_ELEMID_COL] = df[en_orn.RDCLS_ELEMID_COL].astype(str)
    return df

def read_jurisdiction(fp) -> DataFrame:
    """ Read ORN jurisdiction attributes from ORN_JURISDICTION layer.

    Args:
        fp: path to ORN .gdb file.

    Returns:
        ORN road class information as a pandas.DataFrame
    """
    df = _read_gdb_layer(
        fp, en_orn.JURDICTN_LAYERNAME, en_orn.JURDICTN_USECOLS)
    df[en_orn.JURDICTN_ELEMID_COL] = df[en_orn.JURDICTN_ELEMID_COL].astype(str)
    return df


def filter_by_jurisdiction(
        gdf: GeoDataFrame, df: DataFrame, region_filter: str) -> GeoDataFrame:
    """ 
    Filters the ORN road network to GTHA, GGH or 2022 TTS extents using 
    jurisdiction attribute.
    
    Args
        gdf: GeoDataFrame containing the ORN geometry
        df: pandas DataFrame containing the 'ORN_JURISDICTION' layer 
        region_filter: Must be one of 'GTHA', 'GGH', or 'TTS_2022'

    Returns:
        Filtered `gdf` GeoDataFrame
    """
    if region_filter == 'GTHA':
        agencies = en_orn.JURISDICTIONS_GTHA
    elif region_filter == 'GGH':
        agencies = en_orn.JURISDICTIONS_GGH
    elif region_filter == 'TTS_2022':
        agencies = en_orn.JURISDICTIONS_TTS_2022
    else:
        raise ValueError(
            "region_filter argument must be one of ['GTHA', 'GGH', 'TTS_2022']")
    gdf2 = gdf.merge(
        df, left_on=en_orn.GEOM_ELEMID_COL, right_on=en_orn.JURDICTN_ELEMID_COL)
    return gdf2.loc[gdf2[en_orn.JURDICTN_JURDICTN_COL].isin(agencies), 
                    gdf.columns].copy()

def filter_by_roadclass(
        gdf: GeoDataFrame, 
        df: DataFrame, 
        road_levels: List[str],
    ) -> GeoDataFrame:
    """ Filters the ORN road network to by road class.

    Args:
        gdf: GeoDataFrame containing the ORN geometry
        df: pandas DataFrame containing the 'ORN_JURISDICTION' layer 
        road_levels: Possible levels include 
            ['freeway', 'arterial', 'collector', 'local', 'service', transit']

    Returns:
        Filtered `gdf` GeoDataFrame
    """
    if isinstance(road_levels, str):
        road_levels = [road_levels]
    road_classes = []
    for rl in road_levels:
        if rl == 'freeway':
            road_classes.extend(en_orn.CLASSES_FREEWAY)
        elif rl == 'arterial':
            road_classes.extend(en_orn.CLASSES_ARTERIAL)
        elif rl == 'collector':
            road_classes.extend(en_orn.CLASSES_COLLECTOR)
        elif rl == 'local':
            road_classes.extend(en_orn.CLASSES_LOCAL)
        elif rl == 'service':
            road_classes.extend(en_orn.CLASSES_SERVICE)
        elif rl == 'transit':
            road_classes.extend(en_orn.CLASSES_TRANSIT)
        else:
            raise ValueError( 
                "Invalid road_levels. Must be one of: "
                "['freeway', 'arterial', 'collector', "
                "'local', 'service', transit']"
            )
    gdf2 = gdf.merge(
        df, left_on=en_orn.GEOM_ELEMID_COL, right_on=en_orn.RDCLS_ELEMID_COL)
    return gdf2.loc[gdf2[en_orn.RDCLS_RDCLS_COL].isin(road_classes), 
                    gdf.columns].copy()
