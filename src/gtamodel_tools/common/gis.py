import geopandas as gpd
from math import atan2, pi
import numpy as np
import pandas as pd
from shapely import Point, LineString, MultiLineString

import gtamodel_tools.enums.common as en_cmn


def areal_apportionment(
        from_gdf: gpd.GeoDataFrame, 
        to_gdf: gpd.GeoDataFrame, 
        columns: list[str] | None=None, 
        tolerance: float=0.01
    ) -> pd.DataFrame:
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
    pd.DataFrame
        DataFrame containg `to_gdf` with apportioned 
        attributes from `from_gdf`. The apportioned columns are represented as 
        floating point numbers. If desired, the gis.data.round_to_totals
        function can be used to convert to integers based on regional totals. 
    
    """
    # Reserved names
    from_index_col = '__FROM_INDEX'
    to_index_col = '__TO_INDEX'
    from_area_col = '__FROM_AREA'
    union_area_col = '__UNION_AREA'
    union_proparea_col = '__UNION_PROPAREA'
    reserved_cols = [from_index_col, to_index_col, from_area_col, 
                     union_area_col, union_proparea_col] 

    if not columns:
        columns = from_gdf.columns.difference([en_cmn.GPD_GEOM_COL])
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
    
    # Work on a copy of original to_gdf, allowing us to keep the original
    # for the end.
    to_gdf2 = to_gdf.copy()

    # Do a union operation to split geometries based on any overlaps
    # Unfortunately the geopandas.GeoSeries.overlay operation does not keep the 
    # index of the two dataframes. Hence reset the index first.
    from_gdf = from_gdf.reset_index(names=from_index_col)
    to_gdf2 = to_gdf2.reset_index(names=to_index_col)
    union = from_gdf.overlay(to_gdf2, how="union", keep_geom_type=False)
    union[union_area_col] = union[en_cmn.GPD_GEOM_COL].area

    # Remove union geometries with areas below the tolerance.
    # Note that in doing an "inner" join in the merge operation we are
    # removing any geometry outside of the from_gdf, 
    # which is okay as there is no info to transfer.
    from_area = union.groupby(from_index_col)[union_area_col].sum()
    from_area.name = from_area_col
    union2 = union.merge(
        from_area, how="inner", left_on=from_index_col, right_index=True)
    union2[union_proparea_col] = union2[union_area_col] / union2[from_area_col]
    if len(union2) > len(union):
        raise RuntimeError("Length increase after from_area merge.")
    union2 = union2.loc[union2[union_proparea_col] >= tolerance]

    # At this point we have filtered out all union geographies not in the 
    # from_gdf and all slivers. Recalculate the remaining area by 
    # from_gdf geometry. This assumes that any attribute is distributed evenly
    # in remaining geometries and is 0 is all removed slivers.
    # Then recalculate the area proportions.
    union2 = union2.drop([from_area_col, union_proparea_col], axis=1)
    from_area = union2.groupby(from_index_col)[union_area_col].sum()
    from_area.name = from_area_col
    union3 = union2.merge(
        from_area, how="inner", left_on=from_index_col, right_index=True)
    if len(union3) != len(union2):
        raise RuntimeError("Should not have length change when recalculating "
                           "area proportions.")
    union3[union_proparea_col] = union3[union_area_col] / union3[from_area_col]

    # Remove geometries outside of to_gdf. 
    # Note that we've already removed outside of from_gdf
    union3 = union3.loc[~pd.isna(union3[to_index_col])]

    # Scale the value of all columns by the area proportion, then use pivot 
    # table to sum to to_gdf geometries. Finally, make sure the final index has 
    # all the zones of the orginal to_gdf.
    for col in columns:
        union3[col] = union3[col] * union3[union_area_col] / union3[from_area_col]
    final_df = union3.groupby(to_index_col)[columns].sum()
    final_df.index.name = to_gdf.index.name
    final_df = final_df.reindex(to_gdf.index, fill_value=0.0)
    return final_df.sort_index()


def calc_linestring_orientation(
        ls: LineString | MultiLineString, 
        axis_offset: float=0.0,
        return_type: str='cartesian'
    ) -> float | str:
    """ 
    Calculate the road orientation w.r.t. offset axis. The orientation is 
    calculated based on the start and end points. 

    Args:
        ls: 
            Line shape
        axis_offset: a
            Angle in degrees between absolute east and local east directions.
        return_type: 
            either 'angle' or 'cartesian'. Default is 'cartesian'
    Returns 
        if return_type == 'angle' returns the angle in degrees between -180 
            and 180, with 0 being the offset axis direction, positive angles
            being counter-clockwise from the offset axis.
        if return_type == 'cartesian', return the cartesian direction with 
            respect to the offset axis [NB, EB, WB or SB].

    """
    # Find the linestring start and end points
    st_pt = find_linestring_pt_by_index(ls, 0)
    end_pt = find_linestring_pt_by_index(ls, -1)
    angle = calc_angle(st_pt, end_pt)
    angle = offset_linestring_angle(angle, axis_offset)

    # return values
    if return_type == 'angle':
        return angle
    elif return_type == 'cartesian':
        return convert_angle_to_cartesian(angle)
    else:
        raise ValueError("Invalid return_type.")


def calc_angle(st_pt: Point, end_pt: Point) -> float:
    # Calculate the orientation
    dy = end_pt.y - st_pt.y
    dx = end_pt.x - st_pt.x
    return atan2(dy, dx) * 180.0 / pi


def calc_euclidean_distance(st_pt: Point, end_pt: Point) -> float:
    """ Calculate Euclidean distance between to points.
    
    Points should be in a projected coordinate system.

    Args:
        st_pt:
            Start point
        end_pt:
            End point


    Returns:
        Distance in units of the coordinate system.
    """
    dx = end_pt.x - st_pt.x
    dy = end_pt.y - st_pt.y
    return np.sqrt(dx*dx + dy*dy)


def find_linestring_pt_by_index(
        x: LineString | MultiLineString, 
        i: int
    ) -> Point:
    """ Retrive the coordinates of the i-th vertex in the LineString. 
    
    Args:
        x: 
            Line geometry, can either be a LineString or MultiLineString 
            with one geometry.
        i: 
            index on line string to return

    Returns:
        Vertex coordinates as shapely Point.

    Raises:
        IndexError: 
            If index is out of range.
        AttributeError: 
            If MultiLineString has more than one geometry.
    
    """
    err_msg = "Invalid geometry, must be shapely LineString or a " \
              "MultiLineString with a single geometry."
    if isinstance(x, LineString):
        return Point(x.coords[i][0], x.coords[i][1])
    elif isinstance(x, MultiLineString):
        if len(x.geoms) > 1:
            raise AttributeError(err_msg)
        return Point(x.geoms[0].coords[i][0], x.geoms[0].coords[i][1])
    else:
        raise AttributeError(err_msg)
    

def offset_linestring_angle(angle: float, axis_offset: float) -> float:
    """ Offset linestring angle to account for local orientation.
    
    Args:
        angle:
            Calculated linestring angle in degrees.
        axis_offset:
            Difference between geometry axis and locally referenced
            cardinal axis.
    Returns:
        Offset angle in degrees.
        
    """
    angle = angle - axis_offset
    if angle > 180.0:
        angle = angle - 360.0
    elif angle < -180.0:
        angle = angle + 360.0
    return angle


def convert_angle_to_cartesian(angle: float) -> str:
    """ Convert angle to cartesian (NB, SB, EB, WB) direction.

    Args:
        angle: angle in degrees
    
    Returns:
        Cartesian direction
    """
    if -45 <= angle < 45:
        return 'EB'
    elif 45 <= angle < 135:
        return 'NB'
    elif -135 <= angle < -45:
        return 'SB'
    else:
        return 'WB'
    
