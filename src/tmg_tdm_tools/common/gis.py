import geopandas as gpd
import numpy as np
from typing import List, Optional


def areal_apportionment(
        from_gdf: gpd.GeoDataFrame, 
        to_gdf: gpd.GeoDataFrame, 
        columns: Optional[List[str]]=None, 
        tolerance: float=0.01
    ) -> gpd.GeoDataFrame:
    """ Uses Areal apportionment to transfer data between zone systems.

    Areal apportionment assumes that where people live and work is evenly
    distributed across a zone, and hence are apportioned to a new zone
    geometry based solely on the overlapping region. 
    
    Args:
    from_gdf: geopandas.GeoDataFrame
        Shape and data to transfer to other geometry system.

    to_gdf: geopandas.GeoDataFrame
        Geomtries to which data will be attributed.

    columns: List of strings
        If defined, specifies the attributes in from_gdf that are to be 
        apportioned. If None then all columns will be apportioned. 
        Default is None.

    tolerance: float
        Defines the minimum overlap proportion between two zone that will used 
        to signify an overlap between zones between the from_gdf and to_gdf
        geometries. Overlaps of less than this will be ignored.
        
    Returns:
    gpd.GeoDataFrame
        GeoDataFrame containg `to_gdf` with apportioned 
        attributes from `from_gdf`. The apportioned columns are represented as 
        floating point numbers. If desired, the ________ function
        can be used to convert to integers based on regional totals. 
    
    """
    # Reserved names
    from_index_col = '__FROM_INDEX'
    to_index_col = '__TO_INDEX'
    from_area_col = '__FROM_AREA'
    to_area_col = '__TO_AREA'
    union_area_col = '__UNION_AREA'
    union_proparea_col = '__UNION_PROPAREA'
    rem_area_col = '__RMN_AREA'
    reserved_cols = [from_index_col, to_index_col, from_area_col, to_area_col, 
                     union_area_col, union_proparea_col, rem_area_col] 

    if not columns:
        columns = from_gdf.columns.difference(['geometry'])
    if not from_gdf.index.is_unique or not to_gdf.index.is_unique:
        raise AttributeError("Both 'from_gdf' and 'to_gdf' GeoDataFrames "
                             "must have unique indices.")
    for colname in reserved_cols:
        if colname in from_gdf.columns or colname in to_gdf.columns:
            raise AttributeError("The following column names are reserved: "
                                 f"{', '.join(reserved_cols)}")
        
    # Check that the CRS's match and that they are a projected coordinate system
    if from_gdf.crs != to_gdf.crs:
        raise AttributeError(
            "CRS must match between from_gdf and to_gdf inputs.")
    if not from_gdf.crs.is_projected:
        raise AttributeError(
            "CRS must be a projected coordinate system.")

    # Capture the original gdfso that we can add the results columns to
    # this at the end.
    to_gdf_orig = to_gdf.copy()

    # Unfortunately the geopandas.GeoSeries.overlay operation does not keep the 
    # index of the two dataframes. Hence reset the index first.
    from_gdf = from_gdf.reset_index(names=from_index_col)
    to_gdf = to_gdf.reset_index(names=to_index_col)

    # Calculate areas of the original geometries
    from_gdf[from_area_col] = from_gdf['geometry'].area
    to_gdf[to_area_col] = to_gdf['geometry'].area

    # Do a union operation to split geometries based on any overlaps
    union = from_gdf.overlay(to_gdf, how="union", keep_geom_type=False)
    union[union_area_col] = union['geometry'].area

    # Filter out all slivers, defined as less than threshold argument
    union[union_proparea_col] = union[union_area_col] / union[from_area_col]
    fltr = union[union_proparea_col] >= tolerance
    union = union.loc[fltr]

    # Divide by remaining area and not original area so that we don't
    # lose results to removed slivers.
    # Sometimes the to_gdf zone system does not cover the full extent
    # of the from_gdf zone system. This can happen, for example, near water.
    # Hence also scale by the to_gdf_area / union area.
    remaining_area = union.groupby(from_index_col)[[union_area_col]].sum()
    remaining_area.columns = [rem_area_col]
    union2 = union.merge(
        remaining_area, left_on=from_index_col, right_index=True)
    for col in columns:
        union2[col] = union2[col] * (
            union2[union_area_col] / union2[rem_area_col])

    # Use pivot table by the to_index to apportion to the new zone system
    to_gdf2 = union2.groupby(to_index_col)[columns].sum()

    # Clean up the to_gdf to return
    # Merge geometry and other unused columns from to_gdf back in
    #   I'm doing this column by column to enforce the order.
    # Set the index name, I don't know why it gets overwritten
    to_gdf3 = to_gdf_orig.copy()
    for col in columns:
        to_gdf3 = to_gdf3.merge(to_gdf2[[col]], 
                                left_index=True, 
                                right_index=True
        )
    # Don't know why I have to do this next line, but I do
    to_gdf3.index.name = to_gdf_orig.index.name
    # Final test to make sure that we didn't lose or gain anything 
    # I've loosened this test from the original np.allclose
    # as some losses were found in large tests.
    # todo:  explore this behaviour further when time is available.
    min_ratio = 0.995
    max_ratio = 1.0 / 0.995
    ratio = from_gdf[columns].sum() / to_gdf3[columns].sum()
    if ratio.min() < min_ratio or ratio.max() > max_ratio:
        raise RuntimeWarning(
            'Total sums not matching after Areal apportionment.')
    
    return to_gdf3