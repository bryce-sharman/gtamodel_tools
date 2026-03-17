
import datetime
import geopandas as gpd
from os import PathLike
import pandas as pd
import shapely
from typing import Tuple

import gtamodel_tools.common.gis as gis
import gtamodel_tools.enums.validation.traffic.traffic as en_traffic
import gtamodel_tools.enums.validation.tcl as en_tcl
import gtamodel_tools.enums.validation.traffic.toronto_midblock_counts as en_tocnts
import gtamodel_tools.enums.validation.traffic.cordon_counts as en_cc
import gtamodel_tools.enums.validation.orn as en_orn


# Cordon counts
def read_cc_stations_file(fp: PathLike, sheet_name: str) -> gpd.GeoDataFrame:
    """ 
    Read cordon count stations from Excel spreadsheet. """
    stns = pd.read_excel(fp, sheet_name=sheet_name)
    print(f"Number of stations in file: {len(stns)}")

    # I have found some duplicates in the file, remove them before starting
    stns = stns.drop_duplicates(
        subset=[en_cc.CCSTNS_ID_COL, en_cc.CCSTNS_DIR_COL])
    print(f"Number of stations after cleaning duplicate entries: {len(stns)}")

    stns_geom = gpd.points_from_xy(
        x=stns[en_cc.CCSTNS_X_COL], 
        y=stns[en_cc.CCSTNS_Y_COL], 
        crs=en_cc.CCSTNS_CRS
    )
    stns = gpd.GeoDataFrame(data=stns, geometry=stns_geom)
    return stns

def add_cc_lat_lon(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """ Add the Lat/Lon coordinates to the Point stations GeoDataFrame. """
    geom_t = gdf.geometry.to_crs(en_traffic.CRS)
    gdf[en_traffic.LAT] = geom_t.y
    gdf[en_traffic.LON] = geom_t.x
    return gdf

def identify_nearest_orn_road_segments(
        id, 
        pt: shapely.Point,
        crs: str,
        cnt_dir: str,
        orn_gdf: gpd.GeoDataFrame
    ) -> shapely.LineString | None:
    """
    Recursive function that identify the nearest road segment in a direction 
    that matches count directions.

    Args:
        pt: Point showing countpost location
        crs: crs of the 'pt' coordinates
        cnt_dir: Count direction, one of 'NB', 'EB', 'SB', 'WB'
        orn_gdf: Line GeoDataFrame. The CRS must match that of the pt.

    Returns:
        returns one of:
        - shapely.LineString: Road segment on which the traffic is counted; or
        - None: if no suitable match was found.

    """
    # Find the nearest roads
    distance_col = 'distance'
    gd = gpd.GeoDataFrame(geometry=[pt], crs=crs)

    # There can be duplicates if multiple links are the same distance,
    # likely when one link is the reverse of another. We can just 
    # take the first match when doing subsequent tests.
    gd_with_lineid = gd.sjoin_nearest(
        orn_gdf[[en_orn.GEOM_ELEMID_COL, en_orn.GEOM_COL]], 
        how='left', 
        distance_col=distance_col
    )
    if gd_with_lineid.iloc[0][distance_col] > en_cc.MAX_MATCH_DISTANCE:
        return None

    fltr = orn_gdf[en_orn.GEOM_ELEMID_COL].isin(
        gd_with_lineid[en_orn.GEOM_ELEMID_COL])
    gl = orn_gdf.loc[fltr]

    if len(gl) > 1:
        # First check all segments for the correct direction
        for _, row in gl.iterrows():
            gl_dir = gis.calc_linestring_orientation(
                row['geometry'], en_tocnts.AXIS_OFFSET, 'cartesian')
            if cnt_dir == gl_dir:
                return row['geometry']
        # Check all segments for the opposite direction
        for _, row in gl.iterrows():
            gl_dir = gis.calc_linestring_orientation(
                row['geometry'], en_tocnts.AXIS_OFFSET, 'cartesian')
            if cnt_dir == en_traffic.OPPOSITE_DIR[gl_dir]:
                return row['geometry'].reverse()
    else:
        gl_geom = gl.iloc[0]['geometry']
        gl_dir = gis.calc_linestring_orientation(
                gl_geom, en_tocnts.AXIS_OFFSET, 'cartesian')
        if cnt_dir == gl_dir:
            return gl_geom
        elif cnt_dir == en_traffic.OPPOSITE_DIR[gl_dir]:
            return gl_geom.reverse()

    # At this point, we know we are in a cross direction, either if multiple
    # links were originally found, or not. Remove these links from the 
    # search and call this function recursively.
    orn_temp = orn_gdf.loc[orn_gdf.index.drop(gl.index)]
    return identify_nearest_orn_road_segments(id, pt, crs, cnt_dir, orn_temp)

def identify_cordon_count_stations(
        ccstn_fp: PathLike,
        region: str,
        orn_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
    """ Identify unique cordon count stations for storage in station database. 

    Args:
        fp: path to Cordon Count Station Coordinates file provided by DMG.
        region: Cordon count region
        orn_gdf: GeoDataFrame containing Ontario Road Network (ORN) roads

    Returns:
        - GeoDataFrame of count stations, including match ORN road links.

    """
    stn_pts = read_cc_stations_file(ccstn_fp, f'{region}_Stations')
    # Add lat/lon coordinates
    stn_pts = add_cc_lat_lon(stn_pts)
    # We have an interim version of all columns now, rename to the 'final' names
    stn_pts = stn_pts.rename(en_cc.RENAME_STN_COLS, axis=1)
    stn_pts[en_traffic.SOURCE] = en_cc.AGENCY[region]   
    # In the cordon counts the direction is a single character,
    # add the 'B' to the end to be consistent.
    stn_pts[en_traffic.DIR] = stn_pts[en_traffic.DIR].apply(lambda x: x + 'B')
    print(f"Initial number of stations: {len(stn_pts)}")

    orn2 = orn_gdf.to_crs(en_cc.CCSTNS_CRS)
    crs = stn_pts.crs
    matched_orn_shapes = stn_pts.apply(
        lambda x: identify_nearest_orn_road_segments(
            x['station_id'], x[en_traffic.GEOM], crs, x[en_traffic.DIR], orn2), axis=1)
    matched_orn_shapes.crs = en_cc.CCSTNS_CRS
    matched_fltr = pd.notna(matched_orn_shapes)
    matched_stns = stn_pts.loc[matched_fltr]
    matched_orn_shapes = matched_orn_shapes.loc[matched_fltr]
    print(f"Number of stations with matched ORN roads: {len(matched_stns)}")
    out_gdf = gpd.GeoDataFrame(
        matched_stns,
        geometry=matched_orn_shapes.to_crs(en_traffic.CRS),
        crs=en_traffic.CRS
    )
    return out_gdf[en_traffic.STN_FIELDS].set_index(en_traffic.STN_INDEX_COLS)

def process_cc_timecol(cc_time: int):
    hour = cc_time // 100
    minute = cc_time - (hour * 100)

    # Some counts go from ... say ... 6:15 - 6:30
    # Others go from ... say ... 6:16 - 6:31
    # Convert the minutes to be one of 0, 15, 30, 45, only
    if minute in [1, 16, 31, 46]:
        minute -= 1

    return datetime.time(hour=hour, minute=minute)

def remove_invalid_cc_start_end_times(
        cnts: pd.DataFrame, col: str) -> pd.DataFrame:
    tmp_hr = cnts[col] // 100
    tmp_min = cnts[col] - (tmp_hr * 100)
    fltr = (tmp_hr >= 0) & (tmp_hr <= 23) & (tmp_min>=0) & (tmp_min<=59)
    n_invalid = len(cnts) - fltr.sum()
    if n_invalid > 0:
        print(f'{n_invalid} entries were found with invalid times in '
              f'{col} field... removing.')
        return cnts.loc[fltr]
    else:
        return cnts

def read_cordoncounts(cc_fp: PathLike) -> pd.DataFrame:
    """ Read cordon count traffic volumes.
    
    Args:
        cc_fp: path to the raw traffic volume file

    Returns:
        DataFrame of count data

    """
    # Read the station information, first getting the region and year
    # from the counts file
    with open(cc_fp, 'r') as f:
        header = f.readline()
        region, year = header.split(' ')
        region = region.strip()
        year = year.strip()
        # We've already read (popped) the first row, hence no need to skip it
        df = pd.read_csv(f, index_col=False) 

    # Process counts
    df = remove_invalid_cc_start_end_times(df, en_cc.CC_SRTTIME_COL)
    df = remove_invalid_cc_start_end_times(df, en_cc.CC_ENDTIME_COL)

    # Remove the direction from the stations column, we'll keep separate
    df[en_cc.CC_CNT_STN_COL] = df[en_cc.CC_CNT_STN_COL].str.slice(0, -1)
    # Rename index columns
    df = df.rename(en_cc.RENAME_COUNT_COLS, axis=1)
    # process the date and time columns
    df[en_traffic.DATE] = datetime.date(year=int(year), month=1, day=1)
    df[en_traffic.TIME_START] = df[en_traffic.TIME_START].apply(
        lambda x: process_cc_timecol(x))
    df[en_traffic.TIME_END] = df[en_traffic.TIME_END].apply(
            lambda x: process_cc_timecol(x))
    # Convert N, S, E, W to NB, SB, EB, WB
    df[en_traffic.DIR] = df[en_traffic.DIR].apply(lambda x: x + 'B')
    
    # Determine the subset of columns in each category
    pass_car_cols = df.columns.intersection(en_cc.PASS_CAR_COLS)
    straight_trk_cols = df.columns.intersection(en_cc.STRAIGHT_TRK_COLS)
    sngle_tr_trk_cols = df.columns.intersection(en_cc.SINGLETRAILER_TRK_COLS)
    multi_tr_trk_cols = df.columns.intersection(en_cc.MULTITRAILER_TRK_COLS)
    transit_veh_cols = df.columns.intersection(en_cc.TRANS_VEH_COLS)

    # Aggregate the cordon counts to the database classification columns
    df[en_traffic.CNT_CAR] = df[pass_car_cols].sum(axis=1)
    df[en_traffic.CNT_STRAIGHTTRK] = df[straight_trk_cols].sum(axis=1)
    df[en_traffic.CNT_1TRAILERTRK] = df[sngle_tr_trk_cols].sum(axis=1)
    df[en_traffic.CNT_MULTITRAILERTRK] = df[multi_tr_trk_cols].sum(axis=1)
    df[en_traffic.CNT_BUS] = df[transit_veh_cols].sum(axis=1)
    df[en_traffic.CNT_TRUCK] = df[en_traffic.CNT_STRAIGHTTRK] \
        + df[en_traffic.CNT_1TRAILERTRK] \
        + df[en_traffic.CNT_MULTITRAILERTRK] 
    df[en_traffic.CNT_HEAVY] = df[en_traffic.CNT_TRUCK] + df[en_traffic.CNT_BUS]
    df[en_traffic.CNT_TOTAL] = df[en_cc.TOTAL_COL]

    # Add the source column
    df[en_traffic.SOURCE] = en_cc.AGENCY[region]

    # Return parsed counts
    df = df[en_traffic.CNT_FIELDS_CLASSIFIED].set_index(
        en_traffic.CNT_FIELDS_BASE)
    return df