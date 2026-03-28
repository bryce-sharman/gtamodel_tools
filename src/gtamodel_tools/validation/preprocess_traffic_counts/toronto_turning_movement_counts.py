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
from typing import Iterable

import pandas as pd

# local imports
from gtamodel_tools.common.gis import calc_linestring_orientation

# enums
import gtamodel_tools.enums.common as en_cmn
import gtamodel_tools.enums.validation.traffic.toronto_turning_movement_counts as en_ttmc
import gtamodel_tools.enums.validation.traffic.traffic as en_tfc

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

APPROACH_CN = 'approach'
MODE_CN = 'mode'
TURN_CN = 'turn'
DEPARTURE_CN = 'departure'
VOLUME_CN = 'volume'

INTERVAL_MINS = 15
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

def _process_count_times(cnts: pd.DataFrame) -> pd.DataFrame:
    """ Pre-processes time stamps from Toronto Midblock counts. 
    
    Args:
        cnts: original Toronto Midblock counts data read from files

    Returns:
        Modified `cnts` DataFrame with processed time columns.

    """
    cnts = cnts.copy()
    cnts[en_ttmc.STTIME_CN] = pd.to_datetime(
        cnts[en_ttmc.STTIME_CN], format=en_ttmc.TIME_FORMAT)
    cnts[en_ttmc.ENDTIME_CN] = pd.to_datetime(
        cnts[en_ttmc.ENDTIME_CN], format=en_ttmc.TIME_FORMAT)
    cnts[en_tfc.DATE_CN] = cnts[en_ttmc.STTIME_CN].dt.date
    dayofweek = cnts[en_tfc.DATE_CN].apply(lambda x: x.weekday())
    cnts[IS_WKDAY_CN] = True
    cnts.loc[dayofweek.isin([5, 6]), IS_WKDAY_CN] = False
    cnts[HR_START_CN] = cnts[en_ttmc.STTIME_CN].dt.hour
    cnts[MIN_START_CN] = cnts[en_ttmc.STTIME_CN].dt.minute
    # Map the time period to the counts table
    cnts[TIMEPERIOD_CN] = cnts[HR_START_CN].map(en_cmn.TIME_PERIOD_HR_MAPPING)
    return cnts.sort_values([en_ttmc.ID_CN, en_ttmc.STTIME_CN])

def _identify_centreline_stations(
        cnts: pd.DataFrame, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> None:
    # Centreline recorded counts 
    # 
    #  In the 2020-2029 data, only 2.7% of TMC counts are midblock counts
    #  Given their relative paucity and that they are harder to 
    #  process, do not process these now.
    
    # Centreline cnts procedure
    #  1. Find unique centreline_id[s]
    #  For each centreline ID
    #    - find vertex closest to the stop location
    #    - identify all other roads coming from that vertex
    #    - calculate orientation for all lines 
    #    - relate each line to 
    print('  Not currently identifying stations for Toronto centreline counts.'
          ' Processing for these counts may be added later.')
    return None


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
    # Merge in the geometry column from TCL centreline
    intsc_legs = intsc_legs.merge(
            tcl_gdf[['geometry']], 
            left_on=en_ttmc.LEG_CNTRLN_CN, 
            right_index=True
    )
    gdf = gpd.GeoDataFrame(
        intsc_legs, geometry=en_cmn.GPD_GEOM_COL, crs=tcl_gdf.crs)
    print(f'    {len(gdf)} intersection in and out movements '
          f'after merging TCL geometry')

    # Reverse geometry direction when centreline direction is the opposite
    # of the traffic direction
    print('    Flipping line directions to match traffic flow.')
    gdf = gdf.to_crs(en_cmn.COT_CRS) # Need a projected CRS
    gdf[CNTRLN_DIR_CN] = gdf.geometry.apply(
        lambda x: calc_linestring_orientation(
            x, en_ttmc.AXIS_OFFSET, 'cartesian'))
    gdf[CNTRLN_OPPDIR_CN] = gdf[CNTRLN_DIR_CN].map(en_cmn.OPPOSITE_DIR)

    # Can't swap out geometry on the GeoDataFrame, instead operates on a new series
    # and then used GeoDataFrame.set_geometry to alter geometry on the dataframe
    geometry = gdf.geometry
    fltr_oppdir = (gdf[en_tfc.DIR_CN] == gdf[CNTRLN_OPPDIR_CN])
    switched_geometry = geometry.loc[fltr_oppdir].reverse()
    geometry.loc[fltr_oppdir] = switched_geometry
    gdf = gdf.set_geometry(geometry)

    # First recalculate the line direction.
    # Check that direction is never the opposite direction
    # Filter out cross-direction cases (e.g. NB count with EB line)
    gdf[CNTRLN_DIR_CN] = gdf.geometry.apply(
        lambda x: calc_linestring_orientation(
            x, en_ttmc.AXIS_OFFSET, 'cartesian'))
    gdf[CNTRLN_OPPDIR_CN] = gdf[CNTRLN_DIR_CN].map(en_cmn.OPPOSITE_DIR)
    fltr_oppdir = (gdf[en_tfc.DIR_CN] == gdf[CNTRLN_OPPDIR_CN])
    fltr_cross_dir = gdf[en_tfc.DIR_CN] != gdf[CNTRLN_DIR_CN]
    n_opp_dir = fltr_oppdir.sum()
    if n_opp_dir > 0:
        raise RuntimeError('Opposite direction links remain.')
    n_cross_dir = fltr_cross_dir.sum()
    print(f'    {n_cross_dir} in/out movements found where TCL geometry '
          f'cardinal direction does not match count direction.')
    print('Removing these intersection legs as they cannot be mapped to a '
          'link geometry.')
    gdf = gdf.loc[~fltr_cross_dir]
    return gdf.drop([CNTRLN_DIR_CN, CNTRLN_OPPDIR_CN], axis=1)


def _identify_intersection_stations(
        cnts: pd.DataFrame, 
        intsc_legs: pd.DataFrame,
        tcl_gdf: gpd.GeoDataFrame,
        street_names: pd.Series
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Identifies unique count stations from turning movement counts.

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
    print('  Identifying road-based count stations')
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
    print('  Merging intersection names and locations from counts files.')
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
    print('  Identifying count stations from intersection inbound/outbound legs')
    gdf2[en_tfc.SOURCE_CN] = en_ttmc.SOURCE
    stns = gdf2.groupby(
        [en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN])[[
            en_tfc.STN_LAT_CN, en_tfc.STN_LON_CN, 
            en_cmn.GPD_GEOM_COL, en_tfc.STN_DESC_CN]].first()
    stns = gpd.GeoDataFrame(stns, geometry=en_cmn.GPD_GEOM_COL, crs=gdf2.crs)
    print(f'  {len(stns)} stations identified from intersection-leg mapping')
    intsc_stn_df = gdf2.set_index(
        [en_tfc.SOURCE_CN, en_ttmc.INTSC_CN, en_ttmc.LEG_DIR_CN, INOUT_CN], 
        drop=False    # Need the leg direction later on
    )[[en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN]]

    # Project stations to WGS84 as this is the count standards
    stns = stns.to_crs(en_cmn.WGS_CRS)
    print("  Completed station identification.")
    return stns, intsc_stn_df


def _combine_in_out_daily_counts(
        in_df: pd.DataFrame, 
        out_df: pd.DataFrame, 
        in_col_label: str,
        out_col_label: str,
        label: str
    ) -> pd.DataFrame:
    """ Combine the inbound and outbound counts into a single dataframe. """
    df = pd.concat([in_df, out_df], axis=1)
    mode_cols = [v for v in TMC_MODE_MAPPING.values()] + ['TOT']
    for mode in mode_cols:
        base_cn = f'{mode}_{label}'
        in_cn = f'{mode}_{in_col_label}'
        out_cn = f'{mode}_{out_col_label}'
        cols_to_sum = [in_cn, out_cn]
        df[base_cn] = df[cols_to_sum].sum(axis=1, skipna=True)
        # Because we did a sum with skipna = True, the sum is when 
        # both are NAs. go back and rewrite those
        fltr_in = pd.isna(df[in_cn])
        fltr_out = pd.isna(df[out_cn])
        df.loc[fltr_in & fltr_out, base_cn] = np.nan
        df = df.drop([in_cn, out_cn], axis=1)
    return df


def _combine_in_out_period_counts(
        in_df: pd.DataFrame, 
        out_df: pd.DataFrame, 
        in_col_label: str,
        out_col_label: str,
        label: str
    ) -> pd.DataFrame:
    """ 
    Combine the inbound and outbound time-period-separated counts into a 
    single dataframe. 
    
    """
    df = pd.concat([in_df, out_df], axis=1)

    mode_cols = [v for v in TMC_MODE_MAPPING.values()] + ['TOT']
    for mode in mode_cols:
        for tp in en_cmn.TIME_PERIODS:
            base_cn = f'{mode}_{label}_{tp}'
            in_cn = f'{mode}_{in_col_label}_{tp}'
            out_cn = f'{mode}_{out_col_label}_{tp}'
            cols_to_sum = [in_cn, out_cn]
            df[base_cn] = df[cols_to_sum].sum(axis=1, skipna=True)
            # Because we did a sum with skipna = True, the sum 0 is when 
            # both are NAs, go back and rewrite those
            fltr_in = pd.isna(df[in_cn])
            fltr_out = pd.isna(df[out_cn])
            df.loc[fltr_in & fltr_out, base_cn] = np.nan
            df = df.drop([in_cn, out_cn], axis=1)
    return df


def _calculate_daily_volumes(
        cnts: pd.DataFrame,
        direction:str,
        colname_description: str
    ) -> pd.DataFrame:
    """ Calculate the daily_volume for inbound traffic to intersections.
        
    Will return a NaN if count information is not available for all 24 hours
    of the day.
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        direction:
            One of 'inbound' or 'outbound'
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
    n_records_cn = 'n_records'
    exp_ncnts = 3 * RECORDS_PER_DAY
    # This procedure assumes the there are always 3 turns per approach 
    # in the melted counts table. Check to make sure this is the case.
    if direction == 'inbound':
        cnts = cnts.copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, MODE_CN]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
            APPROACH_CN: en_ttmc.LEG_DIR_CN,
            VOLUME_CN: colname_description
        }
        inout_dir = INTSC_INBOUND_CN
    elif direction == 'outbound':
        cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, MODE_CN]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
            DEPARTURE_CN: en_ttmc.LEG_DIR_CN,
            VOLUME_CN: colname_description
        }
        inout_dir = INTSC_OUTBOUND_CN
    else:
        raise ValueError("direction must be either 'inbound' or 'outbound'")
    
    # Sum daily counts and number of observations
    agg_funcs = {
        HR_START_CN: 'count',
        VOLUME_CN: 'sum'
    }
    dly_cnts = cnts.groupby(grpby_index_cols).agg(agg_funcs)
    dly_cnts.columns = [n_records_cn, VOLUME_CN]
    # Filter observations that don't span the whole day
    dly_cnts.loc[dly_cnts[n_records_cn] < exp_ncnts] = np.nan


    dly_cnts = dly_cnts.reset_index()
    dly_cnts = dly_cnts.drop([n_records_cn], axis=1)
    # add the in-out direction
    dly_cnts[INOUT_CN] = inout_dir   
    # Remove pedestrian and cycling modes -- at least for now
    modes_to_keep = [k for k in TMC_MODE_MAPPING.keys()]
    dly_cnts = dly_cnts.loc[dly_cnts[MODE_CN].isin(modes_to_keep)]
    dly_cnts[MODE_CN] = dly_cnts[MODE_CN].map(TMC_MODE_MAPPING)

    # Unstack by mode to convert to wide format
    dly_cnts = dly_cnts.rename(final_rename_dict, axis=1)
    dly_cnts = dly_cnts.set_index(COUNTS_INDEX)
    f = dly_cnts.unstack(MODE_CN)
    # Calculate the total volume
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    # Convert columns to final format (mode_label)
    f.columns = f.columns.swaplevel()
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]

    return f

def _calculate_period_volumes(
        cnts: pd.DataFrame, 
        direction:str,
        colname_description: str
    ) -> pd.DataFrame:
    """ Calculates period volumes by station, day and time period. 
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        direction:
            One of 'inbound' or 'outbound'
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
    N_HRS_CN = 'n_hours_in_tp'
    EXP_RECORDS_CN = 'expected_records'
    OBSV_RECORDS_CN = 'observed_records'

    if direction == 'inbound':
        cnts = cnts.copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
            APPROACH_CN: en_ttmc.LEG_DIR_CN,
            VOLUME_CN: colname_description
        }
        inout_dir = INTSC_INBOUND_CN
    elif direction == 'outbound':
        cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
            DEPARTURE_CN: en_ttmc.LEG_DIR_CN,
            VOLUME_CN: colname_description
        }
        inout_dir = INTSC_OUTBOUND_CN
    else:
        raise ValueError("direction must be either 'inbound' or 'outbound'")

    # Sum count volumes and number of counts
    agg_funcs = {
        HR_START_CN: 'count',
        VOLUME_CN: 'sum'
    }
    per_cnts = cnts.groupby(grpby_index_cols).agg(agg_funcs)
    per_cnts.columns = [OBSV_RECORDS_CN, VOLUME_CN]

    # Filter out time periods with incomplete counts
    per_cnts[N_HRS_CN] = \
        per_cnts.index.get_level_values(TIMEPERIOD_CN).map(
            en_cmn.TIME_PERIOD_NHOURS)
    per_cnts[EXP_RECORDS_CN] = per_cnts[N_HRS_CN] * RECORDS_PER_HOUR * 3
    per_cnts.loc[
            per_cnts[OBSV_RECORDS_CN] < per_cnts[EXP_RECORDS_CN],
            VOLUME_CN
        ] = np.nan
    per_cnts = per_cnts.reset_index()
    per_cnts = per_cnts.drop([EXP_RECORDS_CN, OBSV_RECORDS_CN, N_HRS_CN], axis=1)
    # add the in-out direction
    per_cnts[INOUT_CN] = inout_dir   
    # Remove pedestrian and cycling modes -- at least for now
    modes_to_keep = [k for k in TMC_MODE_MAPPING.keys()]
    per_cnts = per_cnts.loc[per_cnts[MODE_CN].isin(modes_to_keep)]
    per_cnts[MODE_CN] = per_cnts[MODE_CN].map(TMC_MODE_MAPPING)


    per_cnts = per_cnts.rename(final_rename_dict, axis=1)
    per_cnts = per_cnts.set_index(COUNTS_INDEX + [TIMEPERIOD_CN])
  
    # Unstack by mode to convert to wide format
    f = pd.DataFrame(per_cnts.unstack(MODE_CN)) 
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    f.columns.names = ['label', MODE_CN]
    # Now unstack the time period, then swap column levels to
    # mode, label, time period
    f = pd.DataFrame(f.unstack(TIMEPERIOD_CN))
    f.columns = f.columns.swaplevel('label', MODE_CN)
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]
    return f


def _calculate_pkhr_volumes(
        cnts: pd.DataFrame,
        direction:str,
        colname_description: str
    ) -> pd.DataFrame:
    """Return peak 60-minute windows from interval data within each group.
    
    Args:

        cnts: 
            Turning movement volumes in long (melted) format.
        direction:
            One of 'inbound' or 'outbound'
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
    IN_TP_CN = 'following_in_tp'
    ID_CN = en_ttmc.ID_CN
    TP_CN = TIMEPERIOD_CN
    SHIFT = RECORDS_PER_HOUR - 1
    ROLLING_VOL_CN = VOLUME_CN + '_rs'
    final_rename_dict = {
        en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CN, 
        ROLLING_VOL_CN: colname_description
    }
    
    if direction == 'inbound':
        cnts = cnts.copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict[APPROACH_CN] = en_ttmc.LEG_DIR_CN
        inout_dir = INTSC_INBOUND_CN
    elif direction == 'outbound':
        cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict[DEPARTURE_CN] = en_ttmc.LEG_DIR_CN
        inout_dir = INTSC_OUTBOUND_CN
    else:
        raise ValueError("direction must be either 'inbound' or 'outbound'")
    
    # Mark records that have 3 successive counts from same station and
    # direction. (Given the Toronto midblock use hard-coded 15-minute count 
    # intervals, the original interval + 3 more intervals gives an hour 
    # duration.
    cnts[IN_TP_CN] = True
    cnts.loc[cnts[ID_CN] != cnts[ID_CN].shift(-SHIFT), IN_TP_CN] = False
    cnts.loc[cnts[TP_CN] != cnts[TP_CN].shift(-SHIFT), IN_TP_CN] = False

    # Rolling sum to hourly volumes -- the sum will be incorrect where the has 
    # following flag is False. This is okay as those will be filtered out in 
    # the next step
    indexer = pd.api.indexers.FixedForwardWindowIndexer(
        window_size=RECORDS_PER_HOUR)
    cnts[ROLLING_VOL_CN] = cnts[VOLUME_CN].rolling(window=indexer).sum()

    # Filter by has following counts flag
    cnts = cnts.loc[cnts[IN_TP_CN]]

    pkhr_df = cnts.groupby(grpby_index_cols)[[ROLLING_VOL_CN]].max()
    pkhr_df = pkhr_df.reset_index()

    # Remove pedestrian and cycling modes -- at least for now
    modes_to_keep = [k for k in TMC_MODE_MAPPING.keys()]
    pkhr_df = pkhr_df.loc[pkhr_df[MODE_CN].isin(modes_to_keep)]
    pkhr_df[MODE_CN] = pkhr_df[MODE_CN].map(TMC_MODE_MAPPING)    

    # Set the index to match intersection-leg to station mapping
    pkhr_df = pkhr_df.rename(final_rename_dict, axis=1)
    pkhr_df[INOUT_CN] = inout_dir 
    pkhr_df = pkhr_df.set_index(COUNTS_INDEX + [TIMEPERIOD_CN])

    # Unstack by mode, then compute total by time period
    f = pd.DataFrame(pkhr_df.unstack(MODE_CN)) 
    f[(colname_description, 'TOT')] = f.sum(axis=1, skipna=False)
    f.columns.names = ['label', MODE_CN]

    # Now unstack the time period, then swap column levels to
    # mode, label, time period
    f = pd.DataFrame(f.unstack(TIMEPERIOD_CN))
    f.columns = f.columns.swaplevel('label', MODE_CN)
    f.columns = ["_".join(c) for c in f.columns.to_flat_index()]
    return f


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