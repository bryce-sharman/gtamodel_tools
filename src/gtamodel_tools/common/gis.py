import geopandas as gpd
import math
import numpy as np
import pandas as pd
from shapely import Point, LineString, MultiLineString
import warnings

from gtamodel_tools.common.utilities import unit_clamp
from gtamodel_tools.enums.common import GPD_GEOM_COL
from gtamodel_tools.enums.validation.common import LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR 


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

    columns: 
        If defined, specifies the attributes in from_gdf that are to be 
        apportioned. If None then all columns will be apportioned. 
        Default is None.

    tolerance:
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
        columns = from_gdf.columns.difference([GPD_GEOM_COL])
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
    union[union_area_col] = union[GPD_GEOM_COL].area

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


def prepare_gdf_for_count_processing(
        gdf: gpd.GeoDataFrame | gpd.GeoSeries,
        axis_offset: float=0.0,
    ) -> gpd.GeoDataFrame:
    """ Preprocesses a GeoDataFrame for validation purposes.

    This function calculates the direction at the start, the end and from the 
    start to the end of a linestring to prepare a GeoDataFrame to processess
    count data.

    The benefit of precalculating these is that they can be modified
    later in case the directions from the count data do not reflect a 
    geographic representation. This usually occurs when a specific 
    line is not oriented along the locally predominant N, S, E or W directions. 

    Args:
        gdf: 
            GeoDataFrame to be modified
        axis_offset: a
            Angle in degrees between absolute east and local east directions.
    Returns:
        Modified GeoDataFrame, adding the following fields:
        - _from_dir_: Cartesian direction [NB, SB, EB, WB] at the line start
        - _to_dir_: Cartesian direction [NB, SB, EB, WB] at the line end
        - _ft_dir_: Cartesian direction [NB, SB, EB, WB] from first 
                    to last vertex
    """
    gdf = gpd.GeoDataFrame(gdf)
    gdf[[LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR]] = gdf.apply(
            lambda row: calculate_ls_angles(row, axis_offset),
            axis=1,
            result_type='expand'
        )
    return gdf


def calculate_ls_angles(
        row: pd.Series,
        axis_offset: float
    ) -> tuple[str, str, str]:
    """ Calculates angles on a linestring to prepare for validation counts."""
    ls = ensure_linestring(row.geometry)


    first_pt = Point(ls.coords[0][0], ls.coords[0][1])
    second_pt = Point(ls.coords[1][0], ls.coords[1][1])
    secondlast_pt = Point(ls.coords[-2][0], ls.coords[-2][1])
    last_pt = Point(ls.coords[-1][0], ls.coords[-1][1])

    from_dir = calculate_direction(first_pt, second_pt, axis_offset)
    to_dir = calculate_direction(secondlast_pt, last_pt, axis_offset)
    ft_dir = calculate_direction(first_pt, last_pt, axis_offset)
    return (from_dir, to_dir, ft_dir)


def calculate_direction(
        st_pt: Point, end_pt: Point, axis_offset: float
    ) -> str:
    """ Calculate cartesian direction (NB, SB, EB, WB) between two points. """
    angle = calculate_angle(st_pt, end_pt)
    angle = rotate_angle(angle, axis_offset)
    return convert_angle_to_cartesian(angle)


def calculate_ls_bearing(ls: LineString) -> float:
    """
    Bearing in degrees from the first coordinate to the last coordinate.
    Direction is important:
    A -> B is different from B -> A.
    """
    first_pt = Point(ls.coords[0][0], ls.coords[0][1])
    last_pt = Point(ls.coords[-1][0], ls.coords[-1][1])
    return calculate_angle(first_pt, last_pt)


def ensure_linestring(geom: LineString | MultiLineString) -> LineString:
    """ 
    If valid geometry, returns a LineString representation of the geometry.

    If geometry is a MultiLineString, returns the geometry with the longest
    length.

    """
    if isinstance(geom, LineString):
        return geom
    elif geom.geom_type == "MultiLineString":
        # returns the linestring of the longest part
        parts = list(geom.geoms)
        if len(parts) > 1:
            warnings.warn(
                'Multipart linestring found, only keeping longest section.')
        ls_to_keep = max(parts, key=lambda g: g.length)
        return LineString(ls_to_keep)
    else:
        raise AttributeError(
            'geom must be either a LineString or MultiLineString.')


def calculate_angle(st_pt: Point, end_pt: Point) -> float:
    """ Calculate the angle between two points, between 0 and 360.

    Args:
        st_pt:
            Start point
        end_pt:
            End point

    Returns:
        Angle from st_pt to end_pt in the coordinate system, in degrees.

    """
    dy = end_pt.y - st_pt.y
    dx = end_pt.x - st_pt.x
    if dx == 0.0 and dy == 0.0:
        return np.nan
    return math.degrees(math.atan2(dy, dx)) % 360

   
def angular_difference_degrees(angle_a, angle_b):
    """
    Directed angular difference in degrees.
    0 means same direction. 180 means opposite direction.
    """
    if np.isnan(angle_a) or np.isnan(angle_b):
        return np.nan
    diff = abs(angle_a - angle_b) % 360
    return diff


def rotate_angle(angle: float, axis_offset: float) -> float:
    """ Rotate angle to account for local N-S-E-W orientation.

    Returns:
        Rotated angle in degrees, between 0 and 360.
        
    """
    if np.isnan(angle):
        return np.nan
    return (angle - axis_offset) % 360


def convert_angle_to_cartesian(angle: float) -> str:
    """ Convert angle to cartesian (NB, SB, EB, WB) direction.

    Args:
        angle: angle in degrees
    
    Returns:
        Cartesian direction
    """
    if np.isnan(angle): # this will occur in hypernetworks
        return ''
    if 0 <= angle < 45 or 315 <= angle <= 360:
        return 'EB'
    elif 45 <= angle < 135:
        return 'NB'
    elif 225 <= angle < 315:
        return 'SB'
    else:
        return 'WB'


def sample_line_points(line, step) -> list[Point]:
    """
    Sample points along a LineString at regular distance intervals.
    Includes both start and end points.
    """
    length = line.length
    if length == 0:
        return []
    distances = np.arange(0, length, step)
    if len(distances) == 0 or distances[-1] < length:
        distances = np.append(distances, length)
    return [line.interpolate(d) for d in distances]


def coverage_metrics(
        line_a: LineString, 
        line_b: LineString, 
        tolerance: float, 
        sample_step: float
    ) -> tuple[float, float]:
    """
    Measures how much of line_a is within distance tolerance of line_b.

    Returns:
        coverage_fraction_a:
            approximate fraction of line_a within distance tolerance of line_b
        median_distance_a_to_b:
            median sampled distance from line_a to line_b
    """
    # Calculate the distance from each point on line 1 to line_b
    pts = sample_line_points(line_a, sample_step)
    if not pts:
        return (0, np.inf)
    distances = np.array([pt.distance(line_b) for pt in pts])
    close_mask = distances <= tolerance
    return (float(close_mask.mean()), float(np.median(distances)))


def calc_req_coverage_short_lines(
        adj_min_line_length_ratio: float,
        min_coverage: float,
        tolerance: float,
        sample_step: float
    ) -> tuple[float, float, float]:
    """ Calculate short line minimum coverage parameters.

    Testing found cases for small lines that were matched to another line when
    then met end to end. This is because the angles match and the points
    within the tolerance factor are still caught. For short links, these points
    near the end may account for enough of the points that the link meets
    the minimum adjustment requirement. Hence increase this parameter for 
    short links.

    Returns:
        min_transition:
            Lines below this length must have 100% coverage
        max_transition: 
            Lines above this length will use the standard minimum coverage.
        slope:
            Slope of required coverage vs length for lines whose length
            is between min_transition and max_transition.

    """
    min_transition = tolerance+sample_step
    max_transition = adj_min_line_length_ratio * tolerance
    
    # We want the slope of a line that starts at [min_transition, 1]
    # and ends at [max_transition, min_a_coverage]
    slope = -(1.0 - min_coverage) / (max_transition - min_transition)
    return min_transition, max_transition, slope


def match_directed_lines(
        gdf_a: gpd.GeoDataFrame,
        gdf_b: gpd.GeoDataFrame,
        *,
        tolerance:float=20,
        search_radius:float=30,
        sample_step:float=10,
        max_angle_difference:float=25,
        min_coverage:float=0.2,
        min_score:float=0.35,
        adj_min_line_length_ratio=10,
    ) -> gpd.GeoDataFrame | None:
    """
    Match LineStrings in gdf_a to best match in gdf_b, when a sufficient 
    quality match is present.

    Args:
        gdf_a, gdf_b : 
            Line GIS files to match. The index is expected to uniquely identify
            each line.
        tolerance:
            Maximum distance, in projected CRS units, for sampled points to 
            count as overlapping. This is for used for the final scoring.
        search_radius: float
            Spatial index search buffer around each line in A in projected CRS . 
            units Used in initial screening.
        sample_step:
            Distance interval used for sampling along lines.
        max_angle_difference:
            Maximum directed angle difference allowed.
            Because direction matters, an opposite-direction line will usually have
            an angle difference near 180 and will be excluded.
        min_coverage: 
            Minimum fraction line that must be close to target line.
        min_score:
            Minimum final match score required to record a match.
        adj_min_line_length_ratio:
            Multiplied by tolerance to identify short links, which require
            a higher minimum coverage to be matched. Default is 10.

    Returns: 
        GeoDataFrame containing A-B matches, or None if no matches are returned.

    """
    if gdf_a.empty or gdf_b.empty:
        raise ValueError("One or both input files are empty.")
    if gdf_a.crs is None or gdf_b.crs is None:
        raise ValueError("Both input files must have a CRS.")
    if gdf_a.crs != gdf_b.crs:
        raise ValueError("gdf_a and gdf_b must have the sme CRS.")
    if not gdf_a.crs.is_projected:
        raise ValueError("gdf_a must use projected CRS")
    if not (gdf_a.index.is_unique and gdf_b.index.is_unique):
        raise ValueError("gdf_a and gdf_b must have a unique index that "
                         "identifies each line.")

    min_transition, max_transition, adj_min_slope = \
        calc_req_coverage_short_lines(
            adj_min_line_length_ratio, 
            min_coverage, 
            tolerance, 
            sample_step
        )

    # Ensure that geometry is a LineString and not a MultiLineString
    gdf_a.geometry = gdf_a.geometry.map(ensure_linestring)
    gdf_b.geometry = gdf_b.geometry.map(ensure_linestring)
    gdf_a["_bearing"] = gdf_a.geometry.apply(calculate_ls_bearing)
    gdf_b["_bearing"] = gdf_b.geometry.apply(calculate_ls_bearing)

    sindex_b = gdf_b.sindex
    match_rows = []
    for idx_a, row_a in gdf_a.iterrows():
        geom_a = row_a.geometry
        if geom_a is None or geom_a.is_empty or geom_a.length == 0:
            continue

        # Candidate prefilter - find all rows in gdf_b whose bbox 
        # intersects a search buffer around geom_a
        search_geom = geom_a.buffer(search_radius)
        candidate_idx = list(
            sindex_b.query(search_geom, predicate="intersects")
        )
        bearing_a = row_a["_bearing"]
        best_score = 0
        for idx_b in candidate_idx:
            row_b = gdf_b.iloc[idx_b]
            geom_b = row_b.geometry
            if geom_b is None or geom_b.is_empty or geom_b.length == 0:
                continue

            # Quick reject by true distance if not within 'search_radius' or
            # if angle difference not within 'max_angle_difference' arguments.
            min_distance = geom_a.distance(geom_b)
            if min_distance > search_radius:
                continue
            bearing_b = row_b["_bearing"]
            angle_diff = angular_difference_degrees(bearing_a, bearing_b)
            if np.isnan(angle_diff) or angle_diff > max_angle_difference:
                continue

            # Coverage from A to B
            a_coverage, a_mdn_dist = coverage_metrics(
                geom_a,
                geom_b,
                tolerance=tolerance,
                sample_step=sample_step,
            )
            # Coverage from B to A
            b_coverage, _ = coverage_metrics(
                geom_b,
                geom_a,
                tolerance=tolerance,
                sample_step=sample_step,
            )

            # Using the maximum coverage of both direcions for identifying 
            # candidate targets
            coverage = max(a_coverage, b_coverage)

            # Adjust minimum coverage ratio for short links
            if geom_a.length >= max_transition:
                rev_min_coverage = min_coverage
            elif geom_a.length < min_transition:
                rev_min_coverage = 1.0
            else:
                # Gradually increase required minimum adjustment for short
                # links (as a function
                rev_min_coverage = \
                    1.0 + adj_min_slope * (geom_a.length - min_transition)
            if coverage < rev_min_coverage:
                continue

            # Currently only using A->B distance for scoring
            distance_score = unit_clamp(1.0 - a_mdn_dist / tolerance)
            # Direction score: 1 when same orientation, 0 at max allowable 
            # difference
            angle_score = unit_clamp(1.0 - angle_diff / max_angle_difference)

            # Composite score
            # Currently heavily weighting a_coverage and a_mdn_dist 
            # (in distance score) compared with reverse direction.
            score = (
                0.42 * a_coverage
                + 0.21 * b_coverage
                + 0.21 * distance_score
                + 0.16 * angle_score
            )

            if score >= best_score:
                best_score = score
                new_row = {
                    "idx_a": idx_a,
                    "idx_b": row_b.name,
                    "a_length": geom_a.length,
                    "b_length": geom_b.length,
                    "min_distance": min_distance,
                    "median_distance_a_to_b": a_mdn_dist,
                    "bearing_a": bearing_a,
                    "bearing_b": bearing_b,
                    "angle_difference": angle_diff,
                    "a_coverage_fraction": a_coverage,
                    "min_coverage_fraction": rev_min_coverage,
                    "b_coverage_fraction": b_coverage,
                    "distance_score": distance_score,
                    "angle_score": angle_score,
                    "match_score": score,
                    "geometry": geom_a,
                }

        # Add an entry for all matches that exceed the minimum score
        if best_score > min_score:        
            match_rows.append(new_row)
        else:
            match_rows.append({
                    "idx_a": idx_a,
                    "idx_b": 'NO_MATCH',
                    "a_length": geom_a.length,
                    "b_length": np.nan,
                    "min_distance": np.nan,
                    "median_distance_a_to_b": np.nan,
                    "bearing_a": bearing_a,
                    "bearing_b": np.nan,
                    "angle_difference": np.nan,
                    "a_coverage_fraction": np.nan,
                    "min_coverage_fraction": rev_min_coverage,
                    "b_coverage_fraction": np.nan,
                    "distance_score": np.nan,
                    "angle_score": np.nan,
                    "match_score": np.nan,
                    "geometry": geom_a,
                }
            )

    if not match_rows:
        return None
    matches = gpd.GeoDataFrame(
        match_rows,
        geometry="geometry",
        crs=gdf_a.crs,
    )
    return matches.sort_values(
        ["idx_a", "match_score"], ascending=[True, False]).set_index(
            "idx_a")