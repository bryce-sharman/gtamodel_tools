import geopandas as gpd
from math import atan2, pi
import numpy as np
import pandas as pd
from shapely import Point, LineString, MultiLineString
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
    union_area_col = '__UNION_AREA'
    union_proparea_col = '__UNION_PROPAREA'
    reserved_cols = [from_index_col, to_index_col, from_area_col, 
                     union_area_col, union_proparea_col] 

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
    
    # Work on a copy of original to_gdf, allowing us to keep the original
    # for the end.
    to_gdf2 = to_gdf.copy()

    # Do a union operation to split geometries based on any overlaps
    # Unfortunately the geopandas.GeoSeries.overlay operation does not keep the 
    # index of the two dataframes. Hence reset the index first.
    from_gdf = from_gdf.reset_index(names=from_index_col)
    to_gdf2 = to_gdf2.reset_index(names=to_index_col)
    union = from_gdf.overlay(to_gdf2, how="union", keep_geom_type=False)
    union[union_area_col] = union['geometry'].area

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
    to_gdf2 = union3.groupby(to_index_col)[columns].sum()
    to_gdf2.index.name = to_gdf.index.name
    to_gdf2 = to_gdf2.reindex(to_gdf.index, fill_value=0.0)
    return to_gdf2



def create_vertices_on_line(
        line: LineString,
        target_segment_length: float,

    ) -> List[Point]:
    ''' Return a list of vertices on a line.

    An initial set of vertices are created as follows:
    - Start and end points
    - Internal vertices
    - Segments (between two vertices ) are split if their length exceeds
      `max_segment_length`

    A vertex is removed if the sum of the lengths on both sides of the vertex
    is less than target_segment_length.

    Args:
        line: Line which to represent as a list of Points
        target_segment_length: Target length of all segments between 
            adjacent returned points. 
    
    Returns:
        - List of Points that represent the line.

    '''
    pass



def find_closest_line_to_point(
        pt: Point,
        lines: gpd.GeoSeries,
        coarse_threshold: float
    ) -> int | str:
    """ Find the closest LineString to a given point.

    Args:
        pt: point of interest
        lines: shapely.GeoSeries containing the lines to search
        coarse_threshold: only consider lines whose bounding box
            is within this threshold (X or Y direction) of the point for
            more detailed search.

    Returns:
        Index of the closest line in `lines` GeoSeries.
    
    """
    pass


def calc_linestring_orientation(
        x: LineString | MultiLineString, 
        axis_offset: float,
        return_type: str) -> float | str:
    """ Calculate the road orientation w.r.t. offset axis.

    Args:
        x: Line shape
        axis_offset: angle in degrees between absolute east and local east 
            directions.
        return_type: if 'angle', return the angle w.r.t. offset axis,
            if 'cartesian', return the cartesian direction w.r.t. offset 
                axis. [NB, EB, WB or SB]

    """
    if isinstance(x, LineString):
        st = Point(x.coords[0][0], x.coords[0][1])
        ed = Point(x.coords[-1][0], x.coords[-1][1])
    elif isinstance(x, MultiLineString):
        st = Point(x.geoms[0].coords[0][0], x.geoms[0].coords[0][1])
        ed = Point(x.geoms[-1].coords[-1][0], x.geoms[-1].coords[-1][1])
    else:
        raise AttributeError(
            "Invalid geometry, must be shapely LineString or MultiLineString")
    # Calcualte the orientation
    dy = ed.y - st.y
    dx = ed.x - st.x
    angle = atan2(dy, dx) * 180.0 / pi
    # Calculate angle w.r.t. offset axis
    angle = angle - axis_offset
    if angle > 180.0:
        angle = angle - 360.0
    elif angle < -180.0:
        angle = angle + 360.0

    # return values
    if return_type == 'angle':
        return angle
    elif return_type == 'cartesian':
        if -45 <= angle < 45:
            return "EB"
        elif 45 <= angle < 135:
            return "NB"
        elif -135 <= angle < -45:
            return "SB"
        else:
            return "WB"
    else:
        raise ValueError("Invalid 'return_type' argument.")