"""Process turning movement count (TMC) data by approach and departure.

This script expects a wide-format CSV similar to the uploaded Toronto TMC file,
with columns such as:
    n_appr_cars_r, n_appr_cars_t, n_appr_cars_l,
    s_appr_truck_r, ..., n_appr_peds, w_appr_bike

"""

import geopandas as gpd
import numpy as np
from os import PathLike
import pandas as pd
from pathlib import Path

# enums
import gtamodel_tools.enums.common as en_cmn
import gtamodel_tools.enums.validation.traffic.toronto_turning_movement_counts as en_ttmc
import gtamodel_tools.enums.validation.traffic.traffic as en_tfc
import gtamodel_tools.enums.validation.tcl as en_tcl
from gtamodel_tools.enums.validation.common import LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR

# Module-level constants
IS_WKDAY_CN = 'is_weekday'
HR_START_CN = 'hr_start'
MIN_START_CN = 'min_start'
DLY_TOTAL_VOL_CN = 'daily_total_volume'
TIMEPERIOD_CN = 'time_period'

DIR_CN = 'direction'
CNTRLN_DIR_CN = 'cntrln_dir'
CNTRLN_OPPDIR_CN = 'cntrln_oppdir'
IN_CN = 'inbound'
OUT_CN = 'outbound'
INOUT_CN = 'in_out'
MOVEMENT_CN = 'movement'
APPROACH_CN = 'approach'
MODE_CN = 'mode'
TURN_CN = 'turn'
DEPARTURE_CN = 'departure'
VOLUME_CN = 'volume'

TURN_TO_DEPARTURE = {
    "n": {"l": "e", "t": "s", "r": "w"},
    "s": {"l": "w", "t": "n", "r": "e"},
    "e": {"l": "s", "t": "w", "r": "n"},
    "w": {"l": "n", "t": "e", "r": "s"},
}
DIR_LABELS = {"n": "north", "s": "south", "e": "east", "w": "west"}

INTERVAL_MINS = 15
INTERVAL_SECS = INTERVAL_MINS * 60
RECORDS_PER_HOUR = 60 // INTERVAL_MINS
RECORDS_PER_DAY = 24 * RECORDS_PER_HOUR

COUNTS_INDEX = [
    en_ttmc.INTSC_CN, en_ttmc.LEG_DIR_CN, 
    INOUT_CN, en_tfc.DATE_CN, MODE_CN
]

TMC_MODE_MAPPING = {
    'bus': 'BUS', 
    'cars': 'CAR',
    'truck': 'TRK'
}

DIR_LABEL_MAPPING = {
    'n': 'north',
    's': 'south',
    'e': 'east',
    'w': 'west'
}

def read_turning_movement_counts_from_dir(
        loc: str | PathLike,
        intsc_leg_fp: PathLike,
        tcl_gdf: gpd.GeoDataFrame,
        *,
        drop_intersections: list[int] | None = None
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Read all Toronto turning movement counts from directory.

    Args:
        loc: 
            File directory containing count data
        intsc_leg_fp: 
            Path to the file containing the mapping between intersection
            centreline_id, and the centreline_id corresponding to each
            leg from that intersection.
        tcl_gdf: 
            GeoDataFrame containing Toronto Centreline Network
        drop_intersections:
            Optional list of count intersections to drop.

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    Notes:
        - Count data can be downloaded from Toronto Open Data Portal:
          https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/
        - See the the file svc_data_dictionary on the Open Data Portal for a
          a description of the data fields.
    """

    loc = Path(loc)
    pat = 'tmc_raw_data_[0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9].csv'
    stns_list = []
    counts_list = []
    
    print('Processing turning movement count files')
    for fp in loc.glob(pat):
        stns, counts = read_turning_movement_counts_from_file(
            fp, intsc_leg_fp, tcl_gdf, drop_intersections=drop_intersections)
        stns_list.append(stns)
        counts_list.append(counts)
    print('All files processed')

    stns = pd.concat(stns_list)
    stns = gpd.GeoDataFrame(stns)  # this is to keep the type hinting happy
    cnts = pd.concat(counts_list)
    # Remove station duplicates
    stns = stns.loc[~stns.index.duplicated()]
    return stns, cnts


def read_turning_movement_counts_from_file(
        cnts_fp: PathLike, 
        intsc_leg_fp: PathLike,
        tcl_gdf: gpd.GeoDataFrame,
        *,
        drop_intersections: list[int] | None = None
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ 
    Reads and processes City of Toronto Turning Movement Counts from 
    'raw' files.

    Args:
        cnts_fp: 
            The path to the counts data file.
        intsc_leg_fp: 
            Path to the file containing the mapping between intersection
            centreline_id, and the centreline_id corresponding to each
            leg from that intersection.
        tcl_gdf: 
            GeoDataFrame containing Toronto Centreline Network
        drop_intersections:
            Optional list of count intersections to drop.

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    Notes:
        - Count data can be downloaded from Toronto Open Data Portal:
          https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/
        - See the the file svc_data_dictionary on the Open Data Portal for a
          a description of the data fields.

    """
    cnts = _read_tmc_counts(cnts_fp)
    intsc_legs, street_names = _read_intersection_legs(intsc_leg_fp)
    
    # The TMC counts centreline_id can refer to either the centreline layer
    # denoted by centreline_type = 1, or by the intersection layer, which is
    # denoted by centreline_type = 2.
    c_cnts = cnts.loc[cnts[en_ttmc.CNTTYPE_CN] == en_ttmc.TYPE_CENTERLINE]
    i_cnts = cnts.loc[cnts[en_ttmc.CNTTYPE_CN] == en_ttmc.TYPE_INTERSECTION]
    i_cnts = i_cnts.loc[~i_cnts[en_ttmc.CNTRLNID_CN].isin(drop_intersections)]
    print(f'    {len(c_cnts)} count records are referenced by centreline. ')
    print(f'    {len(i_cnts)} count records are referenced by intersection.')

    # Identify unique count stations
    _identify_centreline_stations(c_cnts, tcl_gdf)
    stns, intsc_stn_df = _identify_intersection_stations(
        i_cnts, intsc_legs, tcl_gdf, street_names)

    # Process count times from strings to date/time objects and identifies
    # weekday / weekend counts
    i_cnts = _process_count_times(i_cnts)

    # Melt from wide to long format
    id_cols = [en_ttmc.ID_CN, en_ttmc.CNTRLNID_CN, en_tfc.DATE_CN,
               en_ttmc.STTIME_CN, IS_WKDAY_CN, HR_START_CN, 
               MIN_START_CN, TIMEPERIOD_CN]
    cnts_long = i_cnts[id_cols + en_ttmc.MOVEMENT_CNS].melt(
        id_vars=id_cols,
        value_vars=en_ttmc.MOVEMENT_CNS,
        var_name=MOVEMENT_CN,
        value_name=VOLUME_CN,
    )
    cnts_long[VOLUME_CN] = pd.to_numeric(
        cnts_long[VOLUME_CN], errors="coerce").fillna(0)

    # Parse approach and departure directions
    cnts_long = _parse_mode_approach_departure_directions(cnts_long)

    # Remove pedestrian and cycling modes -- at least for now
    # Check that the departure column name always has a value
    print('  Removing non-motorized modes.')
    modes_to_keep = [k for k in TMC_MODE_MAPPING.values()]
    cnts_long = cnts_long.loc[cnts_long[MODE_CN].isin(modes_to_keep)]
    if (cnts_long[DEPARTURE_CN] == '').sum() > 0:
        raise RuntimeError('   Blank departure direction for motorized mode.')
    
    print('  Calculating weekday and weekend daily volumes')
    cnts_wkday = cnts_long.loc[cnts_long[IS_WKDAY_CN]]
    cnts_wkend = cnts_long.loc[~cnts_long[IS_WKDAY_CN]]
    wkday = _calculate_daily_volumes(cnts_wkday, 'WKDAY')
    wkend = _calculate_daily_volumes(cnts_wkend, 'WKEND')

    print('  Calculating time-period and peak-hour volumes')
    per = _calculate_period_volumes(cnts_wkday, 'PER')
    pkhr = _calculate_pkhr_volumes(cnts_wkday, 'PKHR')
    print('  Calculating peak 15 minute volumes')
    max15m = _calculate_max15min_volumes(cnts_long, 'MAX15MIN')

    combined = pd.concat([wkday, wkend, per, pkhr, max15m], axis=1) 
    final_cnts = _finalize_counts_table(combined, intsc_stn_df)
    return stns, final_cnts


def _read_tmc_counts(cnts_fp: PathLike) -> pd.DataFrame:
    """ Read TMC counts file. 
    
    Args:
        cnts_fp: 
            The path to the counts data file.

    Returns:
        pandas.DataFrame of counts
    
    """
    print(f'  Reading in Toronto Turning Movement counts: {cnts_fp}') 
    dtypes = en_ttmc.DTYPES
    usecols = list(dtypes.keys())
    df = pd.read_csv(cnts_fp, usecols=usecols, dtype=dtypes)
    print(f'    {len(df)} count records read.')
    return df


def _read_intersection_legs(
        intsc_leg_fp: PathLike
    ) -> tuple[pd.DataFrame, pd.Series]:
    """ Reads intersection-leg relationship file. 

    Args:
        intsc_leg_fp: 
            Path to the file containing the mapping between intersection
            centreline_id, and the centreline_id corresponding to each
            leg from that intersection.

    Returns:
        pd.DataFrame of intersection legs:
            Columns are: intersection_centreline_id, leg_centreline_id, leg
        pd.Series of mapping between leg_centreline_id and street name
    
    """
    print('  Reading Intersection centreline_id to leg centreline_id mapping')
    dtypes = en_ttmc.INTSC_MAPPING_DTYPES
    usecols = list(dtypes.keys())
    df = pd.read_csv(intsc_leg_fp, usecols=usecols, dtype=dtypes)
    print(f'    {len(df)} intersection-leg records read.')
    streets = df.groupby(en_ttmc.LEG_CNTRLN_CN)[en_ttmc.LEG_STNAME_CN].first()
    
    return (df.drop(en_ttmc.LEG_STNAME_CN, axis=1), streets)


def _merge_tcl_geometries(
        intsc_legs: pd.DataFrame,
        tcl_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
    """ Merge TCL geometries to intersection legs, ensuring correct orientation.
    
    Args:
        intsc_legs:
            Intersection legs with in and out directions.
        tcl_gdf: 
            GeoDataFrame containing Toronto Centreline Network

    Returns:
        GeoDataFrame containing intersection legs with merged TCL geometries.

    """
    FR_CN = en_tcl.TCL_FROM_INTSC
    TO_CN = en_tcl.TCL_TO_INTSC
    FR_ODIR_CN = '_from_oppdir_'
    TO_ODIR_CN = '_to_oppdir_'
    FT_ODIR_CN = '_fromto_oppdir_'
    GEOM_CN = en_cmn.GPD_GEOM_COL
    
    # Merge in the geometry, from_intersection and to_intersection columns
    # from TCL centreline
    intsc_legs = intsc_legs.merge(
            tcl_gdf[[FR_CN, TO_CN, LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR, GEOM_CN]], 
            left_on=en_ttmc.LEG_CNTRLN_CN, 
            right_index=True
    )
    gdf = gpd.GeoDataFrame(
        intsc_legs, geometry=en_cmn.GPD_GEOM_COL, crs=tcl_gdf.crs)
    print(f'    {len(gdf)} intersection in and out movements '
          f'after merging TCL geometry')

    # Reverse geometry direction when centreline direction is the opposite
    # of the traffic direction using the 'TO' fields for inbound and the 'FROM' 
    # fields for inbound legs.
    print('    Flipping line directions to match traffic flow.')
    gdf = gdf.to_crs(en_cmn.COT_CRS) # Need a projected CRS
    gdf[FR_ODIR_CN] = gdf[LS_FROM_DIR].map(en_cmn.OPPOSITE_DIR)
    gdf[TO_ODIR_CN] = gdf[LS_TO_DIR].map(en_cmn.OPPOSITE_DIR)
    gdf[FT_ODIR_CN] = gdf[LS_FT_DIR].map(en_cmn.OPPOSITE_DIR)

    fltr_oppdir = pd.Series(False, index=gdf.index)
    fltr_oppdir.loc[
            (gdf[en_ttmc.INTSC_CN]==gdf[en_tcl.TCL_FROM_INTSC]) & 
            (gdf[DIR_CN]==gdf[FR_ODIR_CN])
        ] = True
    fltr_oppdir.loc[(
            gdf[en_ttmc.INTSC_CN]==gdf[en_tcl.TCL_TO_INTSC]) & (
            gdf[DIR_CN]==gdf[TO_ODIR_CN])
        ] = True

    fltr_crossdir = pd.Series(False, index=gdf.index)
    fltr_crossdir.loc[
            (gdf[en_ttmc.INTSC_CN]==gdf[en_tcl.TCL_FROM_INTSC]) & (
            gdf[DIR_CN]!=gdf[LS_FROM_DIR]) & (
            gdf[DIR_CN]!=gdf[FR_ODIR_CN])
        ] = True
    fltr_crossdir.loc[
            (gdf[en_ttmc.INTSC_CN]==gdf[en_tcl.TCL_TO_INTSC]) & (
            gdf[DIR_CN]!=gdf[LS_TO_DIR]) & (
            gdf[DIR_CN]!=gdf[TO_ODIR_CN])
        ] = True

    # Reverse direction on elements where the line orientation is reverse
    # of the count direction. Can't swap out geometry on the GeoDataFrame, 
    # instead operates on a new series and then used GeoDataFrame.set_geometry 
    # to alter geometry on the dataframe.
    # Because we're switching direction, also need to switch the FROM and TO
    # intersections.
    # 1. switch the geometry
    geometry = gdf.geometry
    switched_geometry = geometry.loc[fltr_oppdir].reverse()
    geometry.loc[fltr_oppdir] = switched_geometry
    gdf = gdf.set_geometry(geometry)
    # 2. switch the from and to intersections
    from_intsc = gdf.loc[fltr_oppdir, FR_CN]
    gdf.loc[fltr_oppdir, FR_CN] = gdf.loc[fltr_oppdir, TO_CN]
    gdf.loc[fltr_oppdir, TO_CN] = from_intsc
    # 3. switch the link-level from-to coordinate
    gdf.loc[fltr_oppdir, LS_FT_DIR] = gdf.loc[fltr_oppdir, FT_ODIR_CN]

    # Print and drop cross-direction count locations
    n_cross_dir_stns = fltr_crossdir.sum()
    if n_cross_dir_stns > 0:
        print(f'    {n_cross_dir_stns} stations found where the count '
              f'direction is cross to the centreline direction '
              f'(e.g. NB count on EB link). You can manually change the '
              f'{LS_FROM_DIR} and {LS_FROM_DIR} fields in the TCL file to '
              f'manually adjust directions for those roads.'
        )
        if pd.options.display.max_rows is not None:
            prev_max_rows = pd.options.display.max_rows
            pd.options.display.max_rows = int(max(n_cross_dir_stns, prev_max_rows))
        print(gdf.loc[
                fltr_crossdir,  
                [en_ttmc.INTSC_CN, en_ttmc.LEG_CNTRLN_CN, en_ttmc.LEG_DIR_CN, 
                 INOUT_CN, DIR_CN, FR_CN, TO_CN, LS_FROM_DIR, LS_TO_DIR]
            ].to_string(index=False)
        )
        if pd.options.display.max_rows is not None:
            pd.options.display.max_rows = prev_max_rows         
        gdf_index_to_drop = gdf.loc[fltr_crossdir].index
        gdf = gdf.drop(gdf_index_to_drop, axis=0)

    # Note that the count direction from an intersection is not necessarily a
    # reflection of the orientation of the line, but may be a best fit as to
    # where the road lies in an intersection. Hence swap out the direction 
    # with the line from-to direction
    gdf[DIR_CN] = gdf[LS_FT_DIR]

    return gdf.drop(
        [LS_FROM_DIR, LS_TO_DIR, LS_FT_DIR, FR_ODIR_CN, TO_ODIR_CN, FT_ODIR_CN], 
        axis=1
    )


def _identify_centreline_stations(
        cnts: pd.DataFrame, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> None:
    """ 
    Identifies unique count stations from road-based turning movement counts.

    Not yet implemented: 

    Notes:
        In the 2020-2029 data, only 2.7% of TMC counts are midblock counts
        Given their relatively few entries and that they are harder to 
        process, do not process these now.
        
        Centreline cnts procedure
        1. Find unique centreline_id[s]
        For each centreline ID
        - find vertex closest to the stop location
        - identify all other roads coming from that vertex
        - calculate orientation for all lines 
        - relate each line to 
    """
    pass


def _identify_intersection_stations(
        cnts: pd.DataFrame, 
        intsc_legs: pd.DataFrame,
        tcl_gdf: gpd.GeoDataFrame,
        street_names: pd.Series,
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ 
    Identifies unique count stations from intersection turning movement counts.

    Count stations are defined by Toronto street centreline_id and
    direction (one of 'NB', 'EB', 'WB', 'SB')
    
    Args:
        cnts: 
            Counts data filtered by centreline_type = 2, which denotes that
            the centreline_id refers to this field in the intersections layer.
        intsc_legs: 
            Mapping between intersection entreline_id, and the centreline_id 
            corresponding to each leg from that intersection.
        tcl_gdf: 
            GeoDataFrame containing Toronto Centreline Network
        street_names:
            Centreline streetnames.
    
    Returns:
        - GeoDataFrame of count stations.
            Index:
                - count source: 'TTMC' in this case
                - station_id
                - cardinal direction
            Fields are:
            - latitude
            - longitude
            - description
            - LineString denoting line shape [must match cardinal direction]
        - Pandas DataFrame with the mapping from intersection & leg to stations 
            GeoDataFrame.
            Index:
                - count source
                - intersection ID
                - leg
                - approach 'inbound', or departure ('outbound')
            Fields match the index of the stations GeoDataFrame
            Note that multiple intersection in-out legs can refer to the same
            station. This occurs when counts are taken at adjacent 
            intersections. In this case multiple count data will be available
            for that station, which is a bonus.

    """
    print('  Identifying intersection-based count stations')
    # Filter intesections to those included in counts file
    unique_intersections = cnts[en_ttmc.CNTRLNID_CN].unique()
    intsc_legs = intsc_legs[
        intsc_legs[en_ttmc.INTSC_CN].isin(unique_intersections)]
    print(f'    {len(intsc_legs)} intersection-leg records at intersections '
          f'where counts were conducted.')

    # Map outbound and inbound directions based on leg direction
    # Then stack to create a separate entry for each inbound/outbound leg
    intsc_legs[IN_CN] = intsc_legs['leg'].map(en_ttmc.IN_DIR_DICT)
    intsc_legs[OUT_CN] = intsc_legs['leg'].map(en_ttmc.OUT_DIR_DICT)

    melted = intsc_legs.melt(
        en_ttmc.INTSC_CENTRNLN_CNS, [IN_CN, OUT_CN], INOUT_CN, en_tfc.DIR_CN)
    print(f'    {len(melted)} intersection in and out movements')

    # Merge geometries from TCL shapefile
    gdf = _merge_tcl_geometries(melted, tcl_gdf)
    print(f'    {len(gdf)} movements after merging TCL line geometries.')

    # It is the count data that contains the intersection lat, lon 
    # and description. Merge those in here, alongside the centreline
    # streetnames
    print('    Merging intersection names and locations from counts files.')
    uis = cnts.groupby(en_ttmc.CNTRLNID_CN)[[
        en_ttmc.LOCNAME_CN, en_ttmc.LAT_CN, en_ttmc.LON_CN]].first()
    gdf2 = gdf.merge(
        uis, left_on=en_ttmc.INTSC_CN, right_index=True).merge(
            street_names, left_on=en_ttmc.LEG_CNTRLN_CN, right_index=True)
    print(f'    {len(gdf2)} movements after merging intersection and'
          f' street attributes.')

    # Create station description from intersection name, in-out, streetname
    gdf2[en_tfc.STN_DESC_CN] = ''
    fltr = gdf2[INOUT_CN] == OUT_CN
    gdf2.loc[fltr, en_tfc.STN_DESC_CN] = \
        gdf2.loc[fltr, en_ttmc.LEG_STNAME_CN].str.cat(
            gdf2[en_ttmc.LOCNAME_CN], ' outbound from ')
    fltr = gdf2[INOUT_CN] == IN_CN
    gdf2.loc[fltr, en_tfc.STN_DESC_CN] = \
        gdf2.loc[fltr, en_ttmc.LEG_STNAME_CN].str.cat(
            gdf2[en_ttmc.LOCNAME_CN], ' inbound to ')
    gdf2 = gdf2.drop([en_ttmc.LEG_STNAME_CN, en_ttmc.LOCNAME_CN], axis=1)

    # Start to finalize table by moving names from TMC naming convention to  
    # final naming convention
    gdf2 = gdf2.rename({
            en_ttmc.LEG_CNTRLN_CN: en_tfc.STNID_CN,
            en_ttmc.LAT_CN: en_tfc.STN_LAT_CN, 
            en_ttmc.LON_CN: en_tfc.STN_LON_CN,     
        }, axis=1)
    
    # Create the stations and the mapping between movements 
    # (source-intersection-leg-inout) and station (source-centreline-direction)
    print('    Identifying count stations from intersection in/out legs')
    gdf2[en_tfc.SOURCE_CN] = en_ttmc.SOURCE
    gdf2[en_tfc.STNID_CN] = gdf2[en_tfc.STNID_CN].astype(str)
    stns = gdf2.groupby(
        [en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN])[[
            en_tfc.STN_LAT_CN, en_tfc.STN_LON_CN, 
            en_cmn.GPD_GEOM_COL, en_tfc.STN_DESC_CN]].first()
    stns = gpd.GeoDataFrame(stns, geometry=en_cmn.GPD_GEOM_COL, crs=gdf2.crs)
    print(f'    {len(stns)} stations identified from intersection-leg mapping')
    intsc_stn_df = gdf2.set_index(
        [en_tfc.SOURCE_CN, en_ttmc.INTSC_CN, en_ttmc.LEG_DIR_CN, INOUT_CN], 
        drop=False    # Need the leg direction later on
    )[[en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN]]

    # Project stations to WGS84 as this is the count standards
    stns = stns.to_crs(en_cmn.WGS_CRS)
    print("    Completed station identification.")
    return stns, intsc_stn_df


def _process_count_times(cnts: pd.DataFrame) -> pd.DataFrame:
    """ Pre-processes time stamps from Toronto Midblock counts. 
    
    Args:
        cnts: original Toronto Midblock counts data read from files

    Returns:
        Modified `cnts` DataFrame with processed time columns.

    """
    print('  Parsing count start/end times')
    cnts = cnts.copy()
    cnts[en_ttmc.STTIME_CN] = pd.to_datetime(
        cnts[en_ttmc.STTIME_CN], format=en_ttmc.TIME_FORMAT)
    cnts[en_ttmc.ENDTIME_CN] = pd.to_datetime(
        cnts[en_ttmc.ENDTIME_CN], format=en_ttmc.TIME_FORMAT)
    
    # Check that the interval is the expected 15 minutes
    intvl = (cnts[en_ttmc.ENDTIME_CN] - cnts[en_ttmc.STTIME_CN]).dt.seconds
    correct_intvl = intvl == INTERVAL_MINS * 60
    cnts = cnts.loc[correct_intvl]
    cnts = cnts.drop(en_ttmc.ENDTIME_CN, axis=1)

    # Identify weekday vs weekend counts
    cnts[en_tfc.DATE_CN] = cnts[en_ttmc.STTIME_CN].dt.date
    dayofweek = cnts[en_tfc.DATE_CN].apply(lambda x: x.weekday())
    cnts[IS_WKDAY_CN] = True
    cnts.loc[dayofweek.isin([5, 6]), IS_WKDAY_CN] = False

    # Map the time period to the counts table
    cnts[HR_START_CN] = cnts[en_ttmc.STTIME_CN].dt.hour
    cnts[MIN_START_CN] = cnts[en_ttmc.STTIME_CN].dt.minute
    cnts[TIMEPERIOD_CN] = cnts[HR_START_CN].map(en_cmn.TIME_PERIOD_HR_MAPPING)
    return cnts.sort_values([en_ttmc.ID_CN, en_ttmc.STTIME_CN])


def _parse_mode_approach_departure_directions(
        cnts_l: pd.DataFrame) -> pd.DataFrame:
    """
    Parse mode, and approach and departure directions from melted column names. 
    """
    
    print('  Parsing mode, and approach and departure directions')
    cnts_l = cnts_l.copy()
    cnts_l[[APPROACH_CN, "appr", MODE_CN, TURN_CN]] = \
        cnts_l[MOVEMENT_CN].str.split('_', expand=True)
    cnts_l = cnts_l.drop("appr", axis=1)
    # Find departure direction from inbound direction and turn
    cnts_l[DEPARTURE_CN] = ''
    for approach, turn_dirs in TURN_TO_DEPARTURE.items():
        fltr_approach = cnts_l[APPROACH_CN] == approach
        for turn_dir, dep_dir in turn_dirs.items():
            fltr_turndir = cnts_l[TURN_CN] == turn_dir
            cnts_l.loc[fltr_approach & fltr_turndir, DEPARTURE_CN] = dep_dir
    cnts_l[APPROACH_CN] = cnts_l[APPROACH_CN].map(DIR_LABELS)
    cnts_l[DEPARTURE_CN] = cnts_l[DEPARTURE_CN].map(DIR_LABELS)
    cnts_l[MODE_CN] = cnts_l[MODE_CN].map(TMC_MODE_MAPPING)
    _validate_unique_turns(cnts_l)
    return cnts_l


def _validate_unique_turns(cnts: pd.DataFrame) -> None:
    grpby_cns_in = [en_ttmc.CNTRLNID_CN, APPROACH_CN]
    grpby_cns_out = [en_ttmc.CNTRLNID_CN, DEPARTURE_CN]
    n_unique_turns = cnts.groupby(grpby_cns_in)[TURN_CN].nunique().unique()
    if n_unique_turns != [3]:
        raise RuntimeError(
            'Intersections exist where number turns from a leg  is not 3. ' \
            'Look into this.')
    cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
    n_unique_turns = cnts.groupby(grpby_cns_out)[TURN_CN].nunique().unique()
    if n_unique_turns != [3]:
        raise RuntimeError(
            'Intersections exist where number turns to a leg  is not 3. ' \
            'Look into this.')    


def _calculate_daily_volumes_inner(
        cnts: pd.DataFrame, 
        index_cols: list[str], 
        direction: str, 
        colname_description: str
    ) -> pd.DataFrame:
    """ Direction based daily count volumes """
    exp_ncnts = 3 * RECORDS_PER_DAY
    n_records_cn = 'n_records'
    agg_funcs = {
        HR_START_CN: 'count',
        VOLUME_CN: 'sum'
    }
    rename_dict = {
        en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
        VOLUME_CN: colname_description,
        APPROACH_CN: en_ttmc.LEG_DIR_CN,
        DEPARTURE_CN: en_ttmc.LEG_DIR_CN
    }
    
    # Sum daily counts and number of observations
    dly_cnts = cnts.groupby(index_cols).agg(agg_funcs)
    dly_cnts.columns = [n_records_cn, VOLUME_CN]
    # Filter observations that don't span the whole day
    dly_cnts.loc[dly_cnts[n_records_cn] < exp_ncnts, VOLUME_CN] = np.nan

    dly_cnts = dly_cnts.drop([n_records_cn], axis=1)
    dly_cnts = dly_cnts.reset_index()
    # add the in-out direction
    dly_cnts[INOUT_CN] = direction   
    # rename to intersection column names
    dly_cnts = dly_cnts.rename(rename_dict, axis=1)

    # Unstack by mode, then calculate total volume
    # Then put into the form '{MODE}_{provided description}_
    dly_cnts = dly_cnts.set_index(COUNTS_INDEX)
    f = pd.DataFrame(dly_cnts.unstack(MODE_CN))
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    f.columns = f.columns.swaplevel()
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]
    return f


def _calculate_daily_volumes(
        cnts: pd.DataFrame,
        colname_description: str
    ) -> pd.DataFrame:
    """ Calculate the daily_volume to and from intersections.
        
    Will return a NaN if count information is not available for all 24 hours
    of the day.
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        colname_description: 
            final name, will be appended with the mode to create 
            the final column name.
    Returns:
        pandas.DataFrame
            Counts by intersection approach leg
             Index is ['centreline_id', 'leg', 'in-out', 'date']
             Columns are volumes by mode. For example, if
             e.g. if colname_description is 'WKDAY, columns will be
            'CAR_WKDAY', 'BUS_WKDAY', 'TRK_WKDAY', 'TOT_WKDAY'

    """
    index_in_cns = [
        en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, MODE_CN]
    index_out_cns = [
        en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, MODE_CN]
    dly_cnts_in = _calculate_daily_volumes_inner(
        cnts, index_in_cns, IN_CN, colname_description)
    dly_cnts_out = _calculate_daily_volumes_inner(
        cnts, index_out_cns, OUT_CN, colname_description)
    return pd.concat([dly_cnts_in, dly_cnts_out])


def _calculate_max15min_volumes_inner(
        cnts: pd.DataFrame, 
        index_cols: list[str], 
        direction: str, 
        colname_description: str
    ) -> pd.DataFrame:
    """ Direction based daily count volumes """
    rename_dict = {
        en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
        VOLUME_CN: colname_description,
        APPROACH_CN: en_ttmc.LEG_DIR_CN,
        DEPARTURE_CN: en_ttmc.LEG_DIR_CN
    }
    
    # Sum daily counts and number of observations
    dly_cnts = cnts.groupby(index_cols)[VOLUME_CN].max()
    dly_cnts = dly_cnts.reset_index()
    # add the in-out direction
    dly_cnts[INOUT_CN] = direction   
    # rename to intersection column names
    dly_cnts = dly_cnts.rename(rename_dict, axis=1)
    # Unstack by mode, then calculate total volume
    # Then put into the form '{MODE}_{provided description}_
    dly_cnts = dly_cnts.set_index(COUNTS_INDEX)
    f = pd.DataFrame(dly_cnts.unstack(MODE_CN))
    columns = f.columns
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    # Only keep the Total columns
    f = f.drop(columns, axis=1)
    f.columns = f.columns.swaplevel()
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]
    return f


def _calculate_max15min_volumes(
        cnts: pd.DataFrame,
        colname_description: str
    ) -> pd.DataFrame:
    """ Calculate the maximum 15-minute count volumes to and from intersections.
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        colname_description: 
            final name, will be appended with the mode to create 
            the final column name.
    Returns:
        pandas.DataFrame
            Counts by intersection approach leg
             Index is ['centreline_id', 'leg', 'in-out', 'date']
             Columns are volumes by mode. For example, if
             e.g. if colname_description is 'WKDAY, columns will be
            'CAR_WKDAY', 'BUS_WKDAY', 'TRK_WKDAY', 'TOT_WKDAY'

    """
    print('In _calculate_max15min_volumes')
    index_in_cns = [
        en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, MODE_CN]
    index_out_cns = [
        en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, MODE_CN]
    cnts_in = _calculate_max15min_volumes_inner(
        cnts, index_in_cns, IN_CN, colname_description)
    cnts_out = _calculate_max15min_volumes_inner(
        cnts, index_out_cns, OUT_CN, colname_description)
    final = pd.concat([cnts_in, cnts_out])
    return final


def _calculate_period_volumes_inner(
        cnts: pd.DataFrame,
        index_cols: list[str],
        direction: str,
        colname_description: str
    ) -> pd.DataFrame:
    """ Direction based period count volumes """
    nhrs_cn = 'n_hours_in_tp'
    exprecords_cn = 'expected_records'
    obsvrecords_cn = 'observed_records'
    agg_funcs = {
        HR_START_CN: 'count',
        VOLUME_CN: 'sum'
    }
    rename_dict = {
        en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
        APPROACH_CN: en_ttmc.LEG_DIR_CN,
        DEPARTURE_CN: en_ttmc.LEG_DIR_CN,
        VOLUME_CN: colname_description
    }
    
    # Sum count volumes and number of counts
    per_cnts = cnts.groupby(index_cols).agg(agg_funcs)
    per_cnts.columns = [obsvrecords_cn, VOLUME_CN]

    # Filter out time periods where observations don't span the whole period
    per_cnts[nhrs_cn] = \
        per_cnts.index.get_level_values(TIMEPERIOD_CN).map(
            en_cmn.TIME_PERIOD_NHOURS)
    per_cnts[exprecords_cn] = per_cnts[nhrs_cn] * RECORDS_PER_HOUR * 3
    per_cnts.loc[
            per_cnts[obsvrecords_cn] < per_cnts[exprecords_cn], VOLUME_CN
        ] = np.nan
    per_cnts = per_cnts.drop([exprecords_cn, obsvrecords_cn, nhrs_cn], axis=1)
    per_cnts = per_cnts.reset_index()
    # add the in-out direction
    per_cnts[INOUT_CN] = direction
    # rename to intersection column names
    per_cnts = per_cnts.rename(rename_dict, axis=1)

    # Unstack by mode, then calculate total volume for the time period
    per_cnts = per_cnts.set_index(COUNTS_INDEX + [TIMEPERIOD_CN])
    f = pd.DataFrame(per_cnts.unstack(MODE_CN)) 
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    f.columns.names = ['label', MODE_CN]

    # Now unstack the time period, then swap column levels to
    # put into the form '{mode}_{provided description}_{time period}
    f = pd.DataFrame(f.unstack(TIMEPERIOD_CN))
    f.columns = f.columns.swaplevel('label', MODE_CN)
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]
    return f


def _calculate_period_volumes(
        cnts: pd.DataFrame, 
        colname_description: str
    ) -> pd.DataFrame:
    """ Calculates period volumes by station, day and time period. 
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        colname_description: 
            Label that is added to the columns in conjunction with
            the mode and time period.
    Returns:
        Counts by intersection leg, mode and time period.
             - Index is ['centreline_id', 'leg', 'in-out', 'date']
             - Columns are volumes by mode and time period. For example, if
               e.g. if colname_description is 'PER, columns will be
               'CAR_PER_AM', 'CAR_PER_MD', ...

    """
    index_in_cns = [
        en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, 
        MODE_CN, TIMEPERIOD_CN]
    index_out_cns = [
        en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN,
        MODE_CN, TIMEPERIOD_CN]

    per_cnts_in = _calculate_period_volumes_inner(
        cnts, index_in_cns, IN_CN, colname_description)
    per_cnts_out = _calculate_period_volumes_inner(
        cnts, index_out_cns, OUT_CN, colname_description)
    return pd.concat([per_cnts_in, per_cnts_out])
    

def _calculate_pkhr_volumes_inner(
        cnts: pd.DataFrame,
        index_cols: list[str],
        direction: str,
        colname_description: str   
    ) -> pd.DataFrame:
    """ Direction-based peak-hour count volumes. """
    intp_cn = 'following_in_tp'
    id_cn = en_ttmc.ID_CN
    tp_cn = TIMEPERIOD_CN
    shift = RECORDS_PER_HOUR - 1
    rollingvolume_cn = VOLUME_CN + '_rs'
    rename_dict = {
        en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
        rollingvolume_cn: colname_description,
        APPROACH_CN: en_ttmc.LEG_DIR_CN,
        DEPARTURE_CN: en_ttmc.LEG_DIR_CN
    }
    # We're modifying cnts table, so make a copy
    cnts = cnts.copy()
    
    # Mark records that have 3 successive counts from same station and
    # direction. (Given the Toronto midblock use hard-coded 15-minute count 
    # intervals, the original interval + 3 more intervals gives an hour 
    # duration. Also look for breaks in the counts
    cnts[intp_cn] = True
    cnts.loc[cnts[id_cn] != cnts[id_cn].shift(-shift), intp_cn] = False
    cnts.loc[cnts[tp_cn] != cnts[tp_cn].shift(-shift), intp_cn] = False

    # Now look for a break in the counts in the 
    # current, current+1 and current_2 positions. (current+3) is ok.
    for i in [0, 1, 2]:
        fltr = cnts['break_cn'].shift(-i)
        fltr = fltr.fillna(False)
        cnts.loc[fltr.to_numpy(), intp_cn] = False

    # Rolling sum to hourly volumes -- the sum will be incorrect where the has 
    # following flag is False. This is okay as those will be filtered out in 
    # the next step
    indexer = pd.api.indexers.FixedForwardWindowIndexer(
        window_size=RECORDS_PER_HOUR)
    cnts[rollingvolume_cn] = cnts[VOLUME_CN].rolling(window=indexer).sum()
    # Filter by has following counts flag
    cnts.loc[~cnts[intp_cn], rollingvolume_cn] = np.nan

    # Find the maximum rolling volume for each time period,
    # this is our peak-hour volume
    pkhr_df = cnts.groupby(index_cols)[[rollingvolume_cn]].max()
    pkhr_df = pkhr_df.reset_index()
    # add the in-out direction
    pkhr_df[INOUT_CN] = direction
    # rename to intersection column names
    pkhr_df = pkhr_df.rename(rename_dict, axis=1)
    
    # Unstack by mode, then calculate total volume for the time period
    pkhr_df = pkhr_df.set_index(COUNTS_INDEX + [TIMEPERIOD_CN])
    f = pd.DataFrame(pkhr_df.unstack(MODE_CN)) 
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    f.columns.names = ['label', MODE_CN]

    # Now unstack the time period, then swap column levels to
    # put into the form '{mode}_{provided description}_{time period} 
    f = pd.DataFrame(f.unstack(TIMEPERIOD_CN))
    f.columns = f.columns.swaplevel('label', MODE_CN)
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]

    return f


def _calculate_pkhr_volumes(
        cnts: pd.DataFrame,
        colname_description: str
    ) -> pd.DataFrame:
    """Return peak 60-minute windows from interval data within each group.
    
    Args:

        cnts: 
            Turning movement volumes in long (melted) format.
        colname_description: 
            Label that is added to the columns in conjunction with
            the mode and time period.
    Returns:
        Counts by intersection leg, mode and time period.
             - Index is ['centreline_id', 'leg', 'in-out', 'date']
             - Columns are volumes by mode and time period. For example, if
               e.g. if colname_description is 'PKHR, columns will be
               'CAR_PKHR_AM', 'CAR_PKHR_MD', ...
    Assumes a rolling window of 60 minutes composed of consecutive intervals.
    For 15-minute data, this is 4 intervals.
    """
    index_in_cns = [
        en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, 
        MODE_CN, TIMEPERIOD_CN]
    index_out_cns = [
        en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN,
        MODE_CN, TIMEPERIOD_CN]

    # Really need to ensure that the counts are sorted properly so that
    # can add counts from subsequent records togther
    cnts = cnts.sort_values(
        [en_ttmc.ID_CN, en_tfc.DATE_CN, MODE_CN, 
         APPROACH_CN, TURN_CN, en_ttmc.STTIME_CN]
    )
    # Flag breaks in the counts
    cnts['break_cn'] = False
    st_cn = en_ttmc.STTIME_CN
    cnts.loc[
        (cnts[st_cn].shift(-1) - cnts[st_cn]).dt.seconds != INTERVAL_SECS,
        'break_cn'
    ] = True
    
    pkhr_cnts_in = _calculate_pkhr_volumes_inner(
        cnts, index_in_cns, IN_CN, colname_description)
    pkhr_cnts_out = _calculate_pkhr_volumes_inner(
        cnts, index_out_cns, OUT_CN, colname_description)
    return pd.concat([pkhr_cnts_in, pkhr_cnts_out])


def _finalize_counts_table(
        proc_cnts: pd.DataFrame, intsc_stn_df: pd.DataFrame) -> pd.DataFrame:
    """ Convert the final processed counts into the final format. """
    # Convert from intersection-leg to count station using intsc_stn_df
    df = proc_cnts.reset_index()
    df[en_tfc.SOURCE_CN] = en_ttmc.SOURCE
    df2 = df.merge(
        intsc_stn_df, 
        left_on=[en_tfc.SOURCE_CN, en_ttmc.INTSC_CN, 
                 en_ttmc.LEG_DIR_CN, INOUT_CN], 
        right_index=True,
        suffixes=['', '_dup']
    )
    df2[en_tfc.STNID_CN] = df2[en_tfc.STNID_CN].astype(str)
    df2 = df2.set_index([
        en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN, en_tfc.DATE_CN])
    df2 = df2.rename(en_tfc.V_CNS, axis=1)

    # Only keep volume columns, ensuring that all expected volume columns are 
    # present.
    for c in en_tfc.V_CNS.values():
        if c not in df2.columns:
            df2[c] = np.nan
    return df2[en_tfc.V_CNS.values()] 

