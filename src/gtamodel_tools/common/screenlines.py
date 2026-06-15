""" Module for reading traffic and transit screenlines from shapefile. """

import geopandas as gpd
from os import PathLike
import pandas as pd

import gtamodel_tools.enums.common as en_cmn


equiv_cols = ['EquivNB', 'EquivSB', 'EquivEB', 'EquivWB']
allowed_equivalents = pd.Index(en_cmn.DIRECTIONS)


def read_screenlines(fp: PathLike, index_col: str) -> gpd.GeoDataFrame:
    """ Reads screenlines from a shapefile (or equivalent).

        The input file is expected to have the following format:
        - A column representing the screenline name
        - geometry column is a LineString that defines the screenline
        - Four columns: Equiv_NB, Equiv_Eb, Equiv_SB, Equiv_WB, which
            apply a direction label to links, based on their cartesian
            angle ('NB', 'EB', 'SB', 'WB', respectively). For example,
            if 'Equiv_NB' is set to 'C1', then all NB links are marked
            as being in the direction 'C1'.

        Args:
            fp: Path to shapefile, or equivalent
            index_col: column in geospatial data containing the 
                screenlines names.

        Returns:
            gpd.GeoDataFrame

    """
    gdf = gpd.read_file(fp)
    gdf = gdf.set_index(index_col)
    for col in equiv_cols:
        if col not in gdf.columns:
            raise ValueError(
                f'The screenlines file is expected to contain the columns '
                f'{equiv_cols}, which are used to allow a screenline to '
                f'treat a direction as a different direction.'
            )
        unique_equivalents = pd.Index(gdf[col].unique())
        if len(unique_equivalents.difference(allowed_equivalents)) > 0:
            raise ValueError(
                f'Equivalent directions must be a cardinal direction: '
                f'{en_cmn.DIRECTIONS}'
            )
    return gdf
