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
INTSC_INBOUND_CN = 'inbound'
INTSC_OUTBOUND_CN = 'outbound'
INOUT_CN = 'in_out'
DESC_CN = 'description'

APPROACH_CN = 'approach'
MODE_CN = 'mode'
TURN_CN = 'turn'
DEPARTURE_CN = 'departure'
VOLUME_CN = 'volume'

INTERVAL_MINS = 15
RECORDS_PER_HOUR = 60 // INTERVAL_MINS
RECORDS_PER_DAY = 24 * RECORDS_PER_HOUR

TURN_TO_DEPARTURE = {
    "n": {"l": "e", "t": "s", "r": "w"},
    "s": {"l": "w", "t": "n", "r": "e"},
    "e": {"l": "s", "t": "w", "r": "n"},
    "w": {"l": "n", "t": "e", "r": "s"},
}
DIR_LABELS = {"n": "North", "s": "South", "e": "East", "w": "West"}
COUNTS_INDEX = [
    en_ttmc.INTSC_CNTRLNID_CN, en_ttmc.LEG_DIR_CN, 
    INOUT_CN, en_tfc.DATE_CN, MODE_CN
]

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
    print('Not currently identifying stations for Toronto centreline counts. '
          'Processing for these counts may be added later.')
    return None

def _identify_intersection_stations(
        cnts: pd.DataFrame, 
        intsc_leg_map: pd.DataFrame,
        tcl_gdf: gpd.GeoDataFrame
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Identifies unique count stations from turning movement counts.

    Count stations are defined by Toronto street centreline_id and
    direction (one of 'NB', 'EB', 'WB', 'SB')
    
    Args:
        fp: 
            The path to the counts data file.
        intsc_leg_map: 
            Mapping between intersection entreline_id, and the centreline_id 
            corresponding to each leg from that intersection.
        tcl_gdf: 
            GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations.
            Index:
                - count source: 'TTMC' in this case
                - station_id
                - cardinal direction
            Fields are:
            - description
            - latitude
            - longitude
            - LineString denoting line shape [must match cardinal direction]
        - Pandas DataFrame with the mapping from intersection & leg to stations 
            GeoDataFrame.
            Index:
                - count source
                - intersection ID
                - leg
                - approach 'inbound', or departure ('outbound')
            Fields match the index of the stations GeoDataFrame

    """
    print('Identifying stations on intersection inbound and outbound legs.')
    # Map outbound and inbound directions
    intsc_leg_map[INTSC_INBOUND_CN] = \
        intsc_leg_map['leg'].map(en_ttmc.INBOUND_DIR_DICT)
    intsc_leg_map[INTSC_OUTBOUND_CN] = \
        intsc_leg_map['leg'].map(en_ttmc.OUTBOUND_DIR_DICT)
    melted_intsc_leg_map = intsc_leg_map.melt(
        en_ttmc.INTSC_CENTRNLN_CNS, 
        [INTSC_INBOUND_CN, INTSC_OUTBOUND_CN],
        INOUT_CN,
        DIR_CN
    )

    # Merge in the geometry column from TCL centreline, and calculate cardinal 
    # direction of the LineString. We may lose a few counts they are not in the
    # TCL shapefile. Not much we can do about that.
    print('  Merging in TCL line geometries')
    melted_intsc_leg_map = melted_intsc_leg_map.merge(
        tcl_gdf[['geometry']], 
        left_on=en_ttmc.LEG_CNTRLNID_CN, 
        right_index=True
    )
    melted_gdf = gpd.GeoDataFrame(
        melted_intsc_leg_map,
        geometry=en_cmn.GPD_GEOM_COL,
        crs=tcl_gdf.crs
    )
    # Count standard is to use EPSG_4326.
    melted_gdf = melted_gdf.to_crs(en_cmn.WGS_CRS)

    # Reverse geometry direction when direction is opposite the centreline direction
    # First identify cartesian direction and it's opposite direction
    print('  Flipping line directions to match traffic flow.')
    melted_gdf[CNTRLN_DIR_CN] = melted_gdf.geometry.apply(
        lambda x: calc_linestring_orientation(
            x, en_ttmc.AXIS_OFFSET, 'cartesian'))
    melted_gdf[CNTRLN_OPPDIR_CN] = melted_gdf[CNTRLN_DIR_CN].map(en_cmn.OPPOSITE_DIR)
    # Can't swap out geometry on the GeoDataFrame, instead operates on a new series
    # and then used GeoDataFrame.set_geometry to alter geometry on the dataframe
    geometry = melted_gdf.geometry
    fltr_oppdir = melted_gdf[DIR_CN] == melted_gdf[CNTRLN_OPPDIR_CN]
    switched_geometry = geometry.loc[fltr_oppdir].reverse()
    geometry.loc[fltr_oppdir] = switched_geometry
    melted_gdf = melted_gdf.set_geometry(geometry)

    # Filter out cases where the direction does not match the cardinal direction
    # First recalculate the line direction.
    melted_gdf[CNTRLN_DIR_CN] = melted_gdf.geometry.apply(
        lambda x: calc_linestring_orientation(
            x, en_ttmc.AXIS_OFFSET, 'cartesian'))
    fltr_cross_dir = melted_gdf[DIR_CN] != melted_gdf[CNTRLN_DIR_CN]
    n_cross_dir = fltr_cross_dir.sum()
    print(f'  {n_cross_dir} cases found where TCL geometry cardinal direction '
           'does not match count direction. Removing these intersection legs '
           'as they cannot be mapped to a link geometry.')
    melted_gdf = melted_gdf.loc[~fltr_cross_dir]
    
    # Merge in latitude/longitude/intection name
    # It's okay to lose records here as not all count locations in the mapping
    # file need to be included in a particular set of counts.
    print('  Merging intersection names and locations from counts files.')
    print(f'  {len(melted_gdf)}: intersection leg/approach directions '
          f'from intersection/leg mapping')
    uis = cnts.groupby(en_ttmc.CNTRLNID_CN)[[
        en_ttmc.LOCNAME_CN, en_ttmc.LAT_CN, en_ttmc.LON_CN]].first()
    melted_gdf2 = melted_gdf.merge(
        uis, left_on=en_ttmc.INTSC_CNTRLNID_CN, right_index=True)   
    print(f'    {len(melted_gdf2)} intersection leg/approach directions '
          'after merging in count locations.')

    # Identify count stations, which are defined by centreline ID and direction
    print('  Identifying count stations from intersection inbound/outbound legs')
    stns = melted_gdf2.groupby([en_ttmc.LEG_CNTRLNID_CN, DIR_CN])[
            [INOUT_CN, en_ttmc.LOCNAME_CN, en_ttmc.LON_CN, 
             en_ttmc.LAT_CN, en_ttmc.LEG_STNAME_CN, en_cmn.GPD_GEOM_COL
            ]].first().reset_index()
    print(f'  {len(stns)} stations identified from intersection-leg mapping')
    stns[DESC_CN] = stns[en_ttmc.LOCNAME_CN].str.cat(
        stns[en_ttmc.LEG_STNAME_CN], ' -- ').str.cat(
            stns[INOUT_CN], ' -- ')
    stns[en_tfc.SOURCE_CN] = en_ttmc.SOURCE
    stns = stns.rename({
            en_ttmc.LEG_CNTRLNID_CN: en_tfc.STNID_CN,
            DIR_CN: en_tfc.DIR_CN,
            DESC_CN: en_tfc.STN_DESC_CN, 
            en_ttmc.LAT_CN: en_tfc.STN_LAT_CN, 
            en_ttmc.LON_CN: en_tfc.STN_LON_CN,     
        }, axis=1)
    stns = stns.set_index(en_tfc.STN_INDEX_CNS)
    stn_fields = list(set(en_tfc.STN_FIELDS) - set(en_tfc.STN_INDEX_CNS))
    stns = stns[[
        en_tfc.STN_LAT_CN, en_tfc.STN_LON_CN, en_tfc.STN_DESC_CN, en_cmn.GPD_GEOM_COL]]

    # Create the mapping between intersection-leg-direction and count stations
    intsn_mv_stn_mapping = melted_gdf.set_index(
        [en_ttmc.INTSC_CNTRLNID_CN, en_ttmc.LEG_DIR_CN, INOUT_CN], 
        drop=False    # Need the leg direction later on
    )
    intsn_mv_stn_mapping[en_tfc.SOURCE_CN] = en_ttmc.SOURCE
    intsn_mv_stn_mapping = intsn_mv_stn_mapping[
        [en_tfc.SOURCE_CN, en_ttmc.LEG_CNTRLNID_CN, en_ttmc.LEG_DIR_CN]]
    intsn_mv_stn_mapping.columns = [
        en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN]
    intsn_mv_stn_mapping = intsn_mv_stn_mapping.sort_index()
    print("  Completed station identification.")
    return stns, intsn_mv_stn_mapping

def _calculate_daily_volumes(
        cnts: pd.DataFrame,
        direction:str
    ) -> pd.Series:
    """ Calculate the daily_volume for inbound traffic to intersections.
        
    Will return a NaN if count information is not available for all 24 hours
    of the day.
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        direction:
            One of 'inbound' or 'outbound'
            
    Returns:
        pandas.Series
            Counts by intersection approach leg
             Index is ['centreline_id', 'leg', 'in-out', 'date', 'mode']
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
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CNTRLNID_CN, 
            APPROACH_CN: en_ttmc.LEG_DIR_CN
        }
        inout_dir = INTSC_INBOUND_CN
    elif direction == 'outbound':
        cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, MODE_CN]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CNTRLNID_CN, 
            DEPARTURE_CN: en_ttmc.LEG_DIR_CN
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
    # Change format to match intersection and leg format
    dly_cnts = dly_cnts.reset_index()
    dly_cnts = dly_cnts.rename(final_rename_dict, axis=1)
    dly_cnts[INOUT_CN] = inout_dir   # add the in-out direction
    return dly_cnts.set_index(COUNTS_INDEX)[VOLUME_CN]

def _calculate_period_volumes(
        cnts: pd.DataFrame, 
        direction:str,
        colname_prefix: str
    ) -> pd.DataFrame:
    """ Calculates period volumes by station, day and time period. 
    
    Args:
        cnts: 
            Turning movement volumes in long (melted) format.
        direction:
            One of 'inbound' or 'outbound'
        colname_prefix: 
            final name, will be prepended with the time period to create 
            the final column names
    Returns:
        pandas.DataFrame with period volumes by station and day.

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
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CNTRLNID_CN, 
            APPROACH_CN: en_ttmc.LEG_DIR_CN
        }
        inout_dir = INTSC_INBOUND_CN
    elif direction == 'outbound':
        cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CNTRLNID_CN, 
            DEPARTURE_CN: en_ttmc.LEG_DIR_CN
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
    per_cnts.columns = [OBSV_RECORDS_CN, colname_prefix]

    # Filter out time periods with incomplete counts
    per_cnts[N_HRS_CN] = \
        per_cnts.index.get_level_values(TIMEPERIOD_CN).map(
            en_cmn.TIME_PERIOD_NHOURS)
    per_cnts[EXP_RECORDS_CN] = per_cnts[N_HRS_CN] * RECORDS_PER_HOUR * 3
    per_cnts.loc[
            per_cnts[OBSV_RECORDS_CN] < per_cnts[EXP_RECORDS_CN],
            colname_prefix
        ] = np.nan

    # Change format to match intersection and leg format
    per_cnts = per_cnts[[colname_prefix]]   
    f = pd.DataFrame(per_cnts.unstack())  # keep the type hinting happy
    f.columns = ["".join(c) for c in f.columns.to_flat_index()]
    f = f.reset_index()
    f = f.rename(final_rename_dict, axis=1)
    f[INOUT_CN] = inout_dir   # add the in-out direction
    f = f.set_index(COUNTS_INDEX)
    return f


def _calculate_peakhour_volumes(
    cnts: pd.DataFrame,
    direction:str,
    colname_prefix: str
) -> pd.DataFrame:
    """Return peak 60-minute windows from interval data within each group.
    
    Args:

        cnts: 
            Turning movement volumes in long (melted) format.
        direction:
            One of 'inbound' or 'outbound'
        colname_prefix: 
            final name, will be prepended with the time period to create 
            the final column names

    Assumes a rolling window of 60 minutes composed of consecutive intervals.
    For 15-minute data, this is 4 intervals.
    """
    IN_TP_CN = 'following_in_tp'
    ID_CN = en_ttmc.ID_CN
    TP_CN = TIMEPERIOD_CN
    SHIFT = RECORDS_PER_HOUR - 1
    ROLLING_VOL_CN = VOLUME_CN + '_rs'

    if direction == 'inbound':
        cnts = cnts.copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, APPROACH_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CNTRLNID_CN, 
            APPROACH_CN: en_ttmc.LEG_DIR_CN
        }
        inout_dir = INTSC_INBOUND_CN
    elif direction == 'outbound':
        cnts = cnts.loc[cnts[DEPARTURE_CN] != ''].copy()
        grpby_index_cols = [
            en_ttmc.CNTRLNID_CN, DEPARTURE_CN, en_tfc.DATE_CN, 
            MODE_CN, TIMEPERIOD_CN
        ]
        final_rename_dict = {
            en_ttmc.CNTRLNID_CN: en_ttmc.INTSC_CNTRLNID_CN, 
            DEPARTURE_CN: en_ttmc.LEG_DIR_CN
        }
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
    pkhr_df.columns = [colname_prefix]

    f = pd.DataFrame(pkhr_df.unstack())  # keep the type hinting happy
    f.columns = ["".join(c) for c in f.columns.to_flat_index()]
    f = f.reset_index()
    f = f.rename(final_rename_dict, axis=1)
    f[INOUT_CN] = inout_dir   # add the in-out direction
    f = f.set_index(COUNTS_INDEX)
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