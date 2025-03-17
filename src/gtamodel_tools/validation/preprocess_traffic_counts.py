""" Functions to read and process traffic count data. """

import datetime
import geopandas as gpd
from os import PathLike
import pandas as pd
import shapely
from typing import Tuple

import gtamodel_tools.common.gis as gis
import gtamodel_tools.enums.validation.traffic.traffic as en_traffic
import gtamodel_tools.enums.validation.tcl as en_tcl
import gtamodel_tools.enums.validation.traffic.toronto as en_tocnts
import gtamodel_tools.enums.validation.traffic.cordon_counts as en_cc
import gtamodel_tools.enums.validation.orn as en_orn

SHPDIR_COL = 'shp_dir'
OPPDIR_COL = 'opp_dir'
FLAG_COL = 'flag'
FLAG_SAMEDIR = 'same_dir'
FLAG_OPPDIR = 'opp_dir'
FLAG_CROSSDIR = 'cross_dir'


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

def reverse_line_directions(stns: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """ Reverse Shapefile line directions to match count station directions.
    
    Args:
        stns: the geometry column is the tentative LineString of the road
            segment on which the count was taken.

    Returns
        gpd.GeoDataFrame: Count stations with modified geometry so that the 
            direction matches the count direction
    """
    
    stns[SHPDIR_COL] = stns.geometry.apply(
        lambda x: gis.calc_linestring_orientation(
            x, en_tocnts.AXIS_OFFSET, 'cartesian'))
    stns[OPPDIR_COL] = stns[SHPDIR_COL].map(en_traffic.OPPOSITE_DIR)
    stns[FLAG_COL] = ''
    stns = stns.copy()  # Ensure a fresh dataset before going line-by-line
    for stni, stnr in stns.iterrows():
        if stnr[en_traffic.DIR] == stnr[OPPDIR_COL]:
            stns.at[stni, FLAG_COL] = FLAG_OPPDIR
            stns.loc[stni].geometry = stns.loc[stni].geometry.reverse()
        elif stnr[en_traffic.DIR] == stnr[SHPDIR_COL]:
            stns.at[stni, FLAG_COL] = SHPDIR_COL
        else:
            stns.at[stni, FLAG_COL] = FLAG_CROSSDIR
    return stns


# Toronto counts
def identify_toronto_count_stations(
        cnts: pd.DataFrame, 
        tcl_gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
    """ Identify unique count stations for storage in station database. 

    Args:
        fp: path to the raw traffic volume file
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations

    """
    # Find unique count posts
    stns = cnts.groupby(
        [en_tocnts.STNID_COL, en_tocnts.DIR_COL])[[
            en_tocnts.STNDESC_COL, en_tocnts.LAT_COL, 
            en_tocnts.LON_COL, en_tocnts.SHPID_COL
        ]].first().reset_index()

    # Merge in network centreline
    stns = stns.merge(
        tcl_gdf[[en_tcl.TCL_GEOM_COL]], 
        left_on=en_tocnts.SHPID_COL, 
        right_index=True
    )
    stns = gpd.GeoDataFrame(stns, geometry=en_tcl.TCL_GEOM_COL, crs=tcl_gdf.crs)
    # We have an interim version of all columns now, rename to the 'final' names
    stns = stns.rename(en_tocnts.RENAME_STNS, axis=1)
    stns[en_traffic.SOURCE] = en_tocnts.SOURCE   

    # The line direction does not necessarily match the count direction
    # Flip the line direction where required.
    # Need to work in a projected coordinate system to find link orientation
    stns = stns.to_crs(en_tocnts.WORKING_CRS)
    stns = reverse_line_directions(stns)

    # Drop the counts where we cannot match the directions
    stns = stns.loc[stns[FLAG_COL] != FLAG_CROSSDIR]

    # Prepare stations DataFrame
    stns = stns.drop([
        en_tocnts.SHPID_COL, SHPDIR_COL, OPPDIR_COL, FLAG_COL], axis=1)
    stns = stns.to_crs(en_traffic.CRS)
    return stns[en_traffic.STN_FIELDS].set_index(en_traffic.STN_INDEX_COLS)

def read_toronto_totalonly_volumes(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Read total counts from Toronto Open Data Raw Volume counts.

    Args:
        fp: path to the raw traffic volume file
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    """
    # Read in the traffic count data
    cnts = pd.read_csv(
        fp, 
        index_col=en_tocnts.INDEX_COL, 
        parse_dates=[en_tocnts.STTIME_COL, en_tocnts.ENDTIME_COL]
    )

    # Identify unique stations
    cnt_stations = identify_toronto_count_stations(cnts, tcl_gdf)

    cnts = cnts.reset_index()
    cnts = cnts.rename(en_tocnts.RENAME_CNTS_VOLONLY, axis=1)
    cnts[en_traffic.DATE] = cnts[en_traffic.TIME_START].dt.date
    cnts[en_traffic.TIME_START] = cnts[en_traffic.TIME_START].dt.time
    cnts[en_traffic.TIME_END] = cnts[en_traffic.TIME_END].dt.time
    # Read the count data ensuring that fields are in the proper order
    cnts[en_traffic.SOURCE] = en_tocnts.SOURCE   

    cnts = cnts[en_traffic.CNT_FIELDS_VOLONLY].set_index(
        en_traffic.CNT_FIELDS_BASE)
    return cnt_stations, cnts

def read_toronto_trafficclass_volumes(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Read vehicle class-specific counts from Toronto Open Data.

    Args:
        fp: File path to class-specific traffic counts
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    """
    # Read in the traffic count data
    cnts = pd.read_csv(
        fp, 
        index_col=en_tocnts.INDEX_COL, 
        parse_dates=[en_tocnts.STTIME_COL, en_tocnts.ENDTIME_COL]
    )

    # Identify unique stations
    cnt_stations = identify_toronto_count_stations(cnts, tcl_gdf)
    # Now drop the station information from the counts database
    cnts = cnts.reset_index()
    # Rename the base columns
    cnts = cnts.rename(en_tocnts.RENAME_CNTS_BASE, axis=1)

    cnts[en_traffic.DATE] = cnts[en_traffic.TIME_START].dt.date
    cnts[en_traffic.TIME_START] = cnts[en_traffic.TIME_START].dt.time
    cnts[en_traffic.TIME_END] = cnts[en_traffic.TIME_END].dt.time
    # Read the count data ensuring that fields are in the proper order

    # Sum FHWA veh class counts to aggregated categories
    cnts[en_traffic.CNT_CAR] = cnts[en_tocnts.FHWA01_COL] \
        + cnts[en_tocnts.FHWA02_COL] + cnts[en_tocnts.FHWA03_COL]
    cnts[en_traffic.CNT_BUS] = cnts[en_tocnts.FHWA04_COL]
    cnts[en_traffic.CNT_STRAIGHTTRK] = cnts[en_tocnts.FHWA05_COL] \
        + cnts[en_tocnts.FHWA06_COL] + cnts[en_tocnts.FHWA07_COL]
    cnts[en_traffic.CNT_1TRAILERTRK] = cnts[en_tocnts.FHWA08_COL] \
        + cnts[en_tocnts.FHWA09_COL] + cnts[en_tocnts.FHWA10_COL]
    cnts[en_traffic.CNT_MULTITRAILERTRK] = cnts[en_tocnts.FHWA11_COL] \
        + cnts[en_tocnts.FHWA12_COL] + cnts[en_tocnts.FHWA13_COL]
    cnts[en_traffic.CNT_TRUCK] = cnts[en_traffic.CNT_STRAIGHTTRK] \
        + cnts[en_traffic.CNT_1TRAILERTRK] \
        + cnts[en_traffic.CNT_MULTITRAILERTRK]
    cnts[en_traffic.CNT_HEAVY] = cnts[en_traffic.CNT_TRUCK] \
        + cnts[en_traffic.CNT_BUS] 
    cnts[en_traffic.CNT_TOTAL] = cnts[en_traffic.CNT_HEAVY] \
        + cnts[en_traffic.CNT_CAR] 

    cnts[en_traffic.SOURCE] = en_tocnts.SOURCE  
    cnts = cnts[en_traffic.CNT_FIELDS_CLASSIFIED].set_index(
        en_traffic.CNT_FIELDS_BASE)
    return cnt_stations, cnts

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