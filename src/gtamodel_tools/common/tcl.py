""" Module for reading and filtering Toronto Centreline (TCL) data. """

# import pyogrio   # Seem to need to import before geopandas for some reason
import geopandas as gpd
from os import PathLike

import gtamodel_tools.enums.common as en_cmn
import gtamodel_tools.enums.validation.tcl as en_tcl
from gtamodel_tools.enums.validation.common import LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR 

def read_tcl(fp: PathLike, include_direction_fields: bool) -> gpd.GeoDataFrame:
    """ Reads Toronto Centreline data.

    Args:
        fp: 
            Path to the TCL spatial data.
        include_direction_fields:
            Whether to expect the direction fields ['_from_dir_', '_to_dir_', 
            '_ft_dir_'] in the GeoDataFrame. 
    Returns:
        geopandas GeoDataFrame with the kept roads, including their geometries.

    Notes:
        Toronto centreline data is available from the City of Toronto 
        Open Data. https://open.toronto.ca/dataset/toronto-centreline-tcl/
    """
    cols = [en_tcl.TCL_INDEX, en_tcl.TCL_RDCLS_COL, en_tcl.TCL_ONEWAYCODE_COL, 
            en_tcl.TCL_FROM_INTSC, en_tcl.TCL_TO_INTSC, en_cmn.GPD_GEOM_COL]
    if include_direction_fields:
        cols.extend([LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR])

    gdf = gpd.read_file(fp, engine='pyogrio')
    gdf = gdf[cols].set_index(en_tcl.TCL_INDEX)

    # Filter to road classes 
    return gdf.loc[gdf[en_tcl.TCL_RDCLS_COL].isin(en_tcl.CLASSES_ROAD)].copy()


def filter_by_roadclass(
        gdf: gpd.GeoDataFrame,
        road_levels: list[str],
    ) -> gpd.GeoDataFrame:
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