""" Module for reading and filtering Toronto Centreline (TCL) data. """

import pyogrio   # Seem to need to import before geopandas for some reason
from geopandas import read_file, GeoDataFrame
from os import PathLike
from typing import List

import gtamodel_tools.enums.validation.tcl as en_tcl


def read_tcl_gpkg(fp: PathLike,) -> GeoDataFrame:
    """ Reads Toronto Centreline data, downloaded as a geopackage.

    Args:
        fp: Path to the TCL spatial data.

    Returns:
        geopandas GeoDataFrame with the kept roads, including their geometries.

    Notes:
        Toronto centreline data is available from the City of Toronto 
        Open Data. https://open.toronto.ca/dataset/toronto-centreline-tcl/
    """
    gdf = read_file(fp, engine='pyogrio')
    gdf = gdf.set_index(en_tcl.TCL_INDEX)
    return gdf[[en_tcl.TCL_RDCLS_COL, en_tcl.TCL_ONEWAYCODE_COL, 
                en_tcl.TCL_GEOM_COL]].copy()

def filter_by_roadclass(
        gdf: GeoDataFrame,
        road_levels: List[str],
    ) -> GeoDataFrame:
    """ Filters Toronto Centreline data by road class.

    Args:
        gdf: GeoDataFrame containing the ORN geometry
        road_levels: one of ['freeway', 'arterial', 'collector',
            'local', 'service', transit', 'active']

    Returns:
        Filtered `gdf` GeoDataFrame

    """
    if isinstance(road_levels, str):
        road_levels = [road_levels]
    road_classes = []
    for rl in road_levels:
        if rl == 'freeway':
            road_classes.extend(en_tcl.CLASSES_FREEWAY)
        elif rl == 'arterial':
            road_classes.extend(en_tcl.CLASSES_ARTERIAL)
        elif rl == 'collector':
            road_classes.extend(en_tcl.CLASSES_COLLECTOR)
        elif rl == 'local':
            road_classes.extend(en_tcl.CLASSES_LOCAL)
        elif rl == 'service':
            road_classes.extend(en_tcl.CLASSES_SERVICE)
        elif rl == 'transit':
            road_classes.extend(en_tcl.CLASSES_TRANSIT)
        elif rl == 'active':
            road_classes.extend(en_tcl.CLASSES_ACTIVE)
        else:
            raise ValueError( 
                "Invalid road_levels. Must be one of: "
                "['freeway', 'arterial', 'collector', "
                "'local', 'service', transit']"
            )
    return gdf.loc[gdf[en_tcl.TCL_RDCLS_COL].isin(road_classes)].copy()