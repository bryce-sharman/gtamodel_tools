"""
Functions to read City of Toronto Speed-Volume Classification (midblock)
count data, saving into traffic count database format expected by traffic 
validation tools.

The City of Toronto's Transportation Services Division collects short-term 
traffic count data across the City on an ad-hoc basis to support a variety of 
safety initiatives and projects.

Note that the City of Toronto SVC traffic counts reference the Toronto 
Centreline shapefiles, which must also be downloaded.

Toronto SVC traffic counts can be found on Toronto Open Data at
https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/

Toronto CentreLine shapefile can be found on Toronto Open Data at 
https://open.toronto.ca/dataset/toronto-centreline-tcl/

There are different types of SVC count data files:
1.  Summary Data (svc_summary_data): Provides metadata about every 
    Speed / Volume / Classification Count available, including information about 
    the count location and count date, as well as summary data about each count 
    (total vehicle volumes, average daily volumes, a.m. and p.m. peak hour 
    volumes, average / 85 percentile / 95 percentile speeds, where available, 
    and heavy vehicle percentage, where available).
2.  Most Recent Count Data (svc_most_recent_summary_data): Provides metadata 
    about the most recent Speed / Volume / Classification Count data available 
    at each location for which a count exists, including information about the 
    count location and count date, as well as the summary data provided in the 
    “Summary Data” file (see above).
3.  Raw Data: Raw data is available in 15-minute intervals, and is distributed 
    into one of three different file types based on the count type: volume-only, 
    speed and volume, or classification and volume.
    -   Volume Raw Data: These files provide volume data in 15-minute intervals, 
        for each direction separately. This data only appears to be available
        up until August 2022.
    -   Speed and Volume Raw Data:  These files provide volume data aggregated 
        into speed bins in approximately 5 km/h increments. Speed data are not 
        available for all counts. This data appears to continue to be updated
        as of Oct 2025.
    -   Classification and Volume Raw Data: These files provide volume data 
        aggregated into vehicle type bins by the number of axles, according to 
        the FHWA classification system. Classification data are not available 
        for all counts. This data only appears to be available
        up until August 2023.

The summary data is felt to be insufficient for traffic validation purposes as
it:
    - only provides higher of the a.m. and p.m. peak hour volumes, not both
    - does not provide either peak-period volumes
    - does not provide off-peak volumes
Hence this module provides functions to read the raw data files, only.

The classification raw data can also distinguish between different vehicle
  classes. Note that the Toronto turning movement counts (TMCs) only distinguish
  between cars, trucks and buses. Hence it only makes to process the count
  data to this level of detail, at a maximum.

It is not anticipate that speed data will be used for validation as speed
validation is likely better against the HERE travel time data available
to City staff. Hence volume speed data are processed to provide total
volumes only.

"""

from copy import deepcopy
import geopandas as gpd
import numpy as np
import pandas as pd
from pathlib import Path
from os import PathLike

# gtamodel_tools enums
import gtamodel_tools.enums.validation.traffic.toronto_midblock_counts as en_tmblk
import gtamodel_tools.enums.validation.traffic.traffic as en_tfc

from gtamodel_tools.enums.common import GPD_GEOM_COL, OPPOSITE_DIR, \
    TIME_PERIOD_HR_MAPPING, TIME_PERIOD_NHOURS, WGS_CRS
from gtamodel_tools.enums.validation.common import LS_FT_DIR 

npdtype = np.dtype
idx = pd.IndexSlice

# Internal columns
IS_WKDAY_CN = 'is_weekday'
HR_START_CN = 'hr_start'
MIN_START_CN = 'min_start'
DLY_TOTAL_VOL_CN = 'daily_total_volume'
TIMEPERIOD_CN = 'time_period'

MIN_PER_HR = 60
INTERVAL_MINS = 15
INTERVAL_SECS = INTERVAL_MINS * 60
RECORDS_PER_HOUR = 60 // INTERVAL_MINS
RECORDS_PER_DAY = 24 * RECORDS_PER_HOUR


def read_midblock_counts(
        loc: str | PathLike,
        tcl_gdf: gpd.GeoDataFrame
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Read all Toronto Mid-block traffic counts from directory.

    Args:
        loc: File directory containing count data
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    Notes:
        - Count data can be downloaded from Toronto Open Data Portal:
          https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/
    """

    loc = Path(loc)
    pat_v = 'svc_raw_data_volume_[0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9].csv'
    pat_s = 'svc_raw_data_speed_[0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9].csv'
    pat_c = 'svc_raw_data_class_[0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9].csv'
    stns_list = []
    counts_list = []
    
    print('Processing raw volume count files')
    for fp in loc.glob(pat_v):
        stns, counts = read_midblock_volume_counts(fp, tcl_gdf)
        stns_list.append(stns)
        counts_list.append(counts)
    print('')
    print('Processing raw speed-volume count files')
    for fp in loc.glob(pat_s):
        stns, counts = read_midblock_speedvolume_counts(fp, tcl_gdf)
        stns_list.append(stns)
        counts_list.append(counts)
    print('')
    print('Processing raw class-volume count files')
    for fp in loc.glob(pat_c):
        stns, counts = read_midblock_classvolume_counts(fp, tcl_gdf)
        stns_list.append(stns)
        counts_list.append(counts)
    print('All files processed')

    stns = pd.concat(stns_list)
    stns = gpd.GeoDataFrame(stns)  # this is to keep the type hinting happy
    cnts = pd.concat(counts_list)
    # Remove station duplicates
    stns = stns.loc[~stns.index.duplicated()]
    return stns, cnts


def read_midblock_volume_counts(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Reads City of Toronto Midblock count raw volume from CSV file.

    Args:
        fp: The path to the counts data file.
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    Notes:
        - Count data can be downloaded from Toronto Open Data Portal:
          https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/
        - See the the file svc_data_dictionary on the Open Data Portal for a
          a description of the data fields.
        - The files are svc_raw_data_volume_[start year]_[end year].csv
        - This data only appears to be available up until August 2022. 
          Confirm this in the future if using this data at a later date.

    """
    print(f'  Reading in volume only counts: {fp}') 
    total_volume_cn = en_tmblk.VOLUME_TOTONLY_CNS[0]
    # Read in the traffic counts from file
    dtypes = deepcopy(en_tmblk.COMMON_DTYPES)
    dtypes[total_volume_cn] = npdtype('f4')
    usecols = list(dtypes.keys())
    cnts = pd.read_csv(fp, usecols=usecols, dtype=dtypes)

    print('  Identifying count stations.')
    stns = _identify_midblock_count_stations(cnts, tcl_gdf)
    
    print('  Calculating count summaries.')
    # Process count times from strings to date/time objects and identifies
    # weekday / weekend counts
    cnts = _process_count_times(cnts)
    cnts_wkday = cnts.loc[cnts[IS_WKDAY_CN]]
    cnts_wkend = cnts.loc[~cnts[IS_WKDAY_CN]]

    # Pre-process count data
    wkday_volumes = _calculate_daily_volumes(
        cnts_wkday, total_volume_cn, 'TOT_WKDAY')
    wkend_volumes = _calculate_daily_volumes(
        cnts_wkend, total_volume_cn, 'TOT_WKEND')
    per_volumes = _calculate_period_volumes(
        cnts_wkday,total_volume_cn,'TOT_PER_')
    pkhr_volumes = _calculate_peakhour_volumes(
        cnts_wkday, total_volume_cn, 'TOT_PKHR_')
    max_15min_volumes = _calculate_max15min_volumes(
        cnts, total_volume_cn, 'TOT_MAX15MIN')

    # Completed all the parts, time to put it together
    f_cnts = pd.concat([
            wkday_volumes, per_volumes, pkhr_volumes, wkend_volumes, 
            max_15min_volumes
        ], axis=1
    )
    f_cnts = f_cnts.rename(en_tfc.V_CNS, axis=1)
    f_cnts = _finalize_counts_table(f_cnts, cnts, stns)
    print('  Completed') 
    return stns, f_cnts


def read_midblock_speedvolume_counts(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Reads City of Toronto Midblock count raw speed-volume from CSV file.

    Args:
        fp: The path to the counts data file.
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    Notes:
        - Count data can be downloaded from Toronto Open Data Portal:
          https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/
        - See the the file svc_data_dictionary on the Open Data Portal for a
          a description of the data fields.
        - The files are svc_raw_data_speed_[start year]_[end year].csv
        - This data is being updated as of Nov 2025. 

    """
    print(f'  Reading in speed-volume only counts: {fp}') 
    total_volume_cn = en_tmblk.VOLUME_TOTONLY_CNS[0]
    dtypes =deepcopy(en_tmblk.COMMON_DTYPES)
    for cn in en_tmblk.VOLUME_SPDCLS_CNS:
        dtypes[cn] = npdtype('f4')
    usecols = list(dtypes.keys())
    cnts = pd.read_csv(fp, usecols=usecols, dtype=dtypes)
    
    print('  Identifying count stations.')
    stns = _identify_midblock_count_stations(cnts, tcl_gdf)

    print('  Calculating count summaries.')
    # Process count times from strings to date/time objects
    cnts = _process_count_times(cnts)

    # Add up all the counts by speed class into a single column
    # After this we can treat the exact same as the volume-only column
    cnts[total_volume_cn] = cnts[en_tmblk.VOLUME_SPDCLS_CNS].sum(axis=1)
    cnts = cnts.drop(en_tmblk.VOLUME_SPDCLS_CNS, axis=1)
     # Separate into weekday / weekend counts
    cnts_wkday = cnts.loc[cnts[IS_WKDAY_CN]]
    cnts_wkend = cnts.loc[~cnts[IS_WKDAY_CN]]

    # Pre-process count data
    wkday_volumes = _calculate_daily_volumes(
        cnts_wkday,  total_volume_cn,  'TOT_WKDAY')
    wkend_volumes = _calculate_daily_volumes(
        cnts_wkend,  total_volume_cn,  'TOT_WKEND')
    per_volumes = _calculate_period_volumes(
        cnts_wkday, total_volume_cn, 'TOT_PER_')
    pkhr_volumes = _calculate_peakhour_volumes(
        cnts_wkday, total_volume_cn, 'TOT_PKHR_')
    max_15min_volumes = _calculate_max15min_volumes(
        cnts, total_volume_cn, 'TOT_MAX15MIN')

    # Completed all the parts, time to put it together
    f_cnts = pd.concat([
        wkday_volumes, per_volumes, pkhr_volumes, wkend_volumes, 
        max_15min_volumes
        ], axis=1
    )
    f_cnts = f_cnts.rename(en_tfc.V_CNS, axis=1)
    f_cnts = _finalize_counts_table(f_cnts, cnts, stns)
    print('  Completed') 
    return stns, f_cnts


def read_midblock_classvolume_counts(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ 
    Reads City of Toronto Midblock count raw classification counts from CSV file.

    Args:
        fp: The path to the counts data file.
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    Notes:
        - Count data can be downloaded from Toronto Open Data Portal:
          https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/
        - See the the file svc_data_dictionary on the Open Data Portal for a
          a description of the data fields.
        - The files are svc_raw_data_class_[start year]_[end year].csv
        - This data was last updated in August 2023.

    """
    print(f'  Reading in volume by vehicle class counts: {fp}') 

    dtypes =deepcopy(en_tmblk.COMMON_DTYPES)
    for cn in en_tmblk.ALL_CLASS_CNS:
        dtypes[cn] = npdtype('f4')
    usecols = list(dtypes.keys())
    cnts = pd.read_csv(fp, usecols=usecols, dtype=dtypes)

    print('  Identifying count stations.')
    stns = _identify_midblock_count_stations(cnts, tcl_gdf)

    print('  Calculating count summaries.')
    # Process count times from strings to date/time objects
    cnts = _process_count_times(cnts)

    # Add up all the counts by vehicle class into a single column
    cnts['CAR'] = cnts[en_tmblk.CAR_CLASS_CNS].sum(axis=1)
    cnts['BUS'] = cnts[en_tmblk.BUS_CLASS_CNS].sum(axis=1)
    cnts['TRK'] = cnts[en_tmblk.TRUCK_CLASS_CNS].sum(axis=1)
    cnts['TOT'] = cnts[en_tmblk.ALL_CLASS_CNS].sum(axis=1)
    cnts = cnts.drop(en_tmblk.ALL_CLASS_CNS, axis=1)

    # Separate into weekday / weekend counts
    cnts_wkday = cnts.loc[cnts[IS_WKDAY_CN]]
    cnts_wkend = cnts.loc[~cnts[IS_WKDAY_CN]]

    all_cols = ['CAR', 'BUS', 'TRK', 'TOT']
    wkday_volumes = _calculate_daily_volumes(
        cnts_wkday,  
        all_cols,  
        ['CAR_WKDAY', 'BUS_WKDAY', 'TRK_WKDAY', 'TOT_WKDAY']
    )
    wkend_volumes = _calculate_daily_volumes(
        cnts_wkend,  
        all_cols,  
        ['CAR_WKEND', 'BUS_WKEND', 'TRK_WKEND', 'TOT_WKEND']
    )
    per_volumes = _calculate_period_volumes(
        cnts_wkday, 
        all_cols, 
        ['CAR_PER_', 'BUS_PER_', 'TRK_PER_', 'TOT_PER_'])
    pkhr_volumes = _calculate_peakhour_volumes(
        cnts_wkday, 
        all_cols, 
        ['CAR_PKHR_', 'BUS_PKHR_', 'TRK_PKHR_', 'TOT_PKHR_']
    )
    max_15min_volumes = _calculate_max15min_volumes(
        cnts, ['TOT'], 'TOT_MAX15MIN')

    # Completed all the parts, time to put it together
    f_cnts = pd.concat([
        wkday_volumes, per_volumes, pkhr_volumes, wkend_volumes,
        max_15min_volumes
        ], axis=1
    )
    f_cnts = f_cnts.rename(en_tfc.V_CNS, axis=1)
    f_cnts = _finalize_counts_table(f_cnts, cnts, stns)
    print('  Completed') 
    return stns, f_cnts


def _process_count_times(cnts: pd.DataFrame) -> pd.DataFrame:
    """ Processes time stamps from Toronto Midblock counts. 
    
    Args:
        cnts: original Toronto Midblock counts data read from files

    Returns:
        Modified `cnts` DataFrame with processed time columns.

    """
    cnts = cnts.copy()
    cnts[en_tmblk.STTIME_CN] = pd.to_datetime(
        cnts[en_tmblk.STTIME_CN], format=en_tmblk.TIME_FORMAT)
    cnts[en_tmblk.ENDTIME_CN] = pd.to_datetime(
        cnts[en_tmblk.ENDTIME_CN], format=en_tmblk.TIME_FORMAT)

    # Check that the interval is the expected 15 minutes, dropping 
    # those where this is not the case since the rest of the code
    # is expecting consistent interval durations.
    intvl = (cnts[en_tmblk.ENDTIME_CN] - cnts[en_tmblk.STTIME_CN]).dt.seconds
    correct_intvl = intvl == INTERVAL_SECS
    cnts = cnts.loc[correct_intvl]
    cnts = cnts.drop(en_tmblk.ENDTIME_CN, axis=1)
    
    cnts[en_tfc.DATE_CN] = cnts[en_tmblk.STTIME_CN].dt.date
    dayofweek = cnts[en_tfc.DATE_CN].apply(lambda x: x.weekday())
    cnts[IS_WKDAY_CN] = True
    cnts.loc[dayofweek.isin([5, 6]), IS_WKDAY_CN] = False
    cnts[HR_START_CN] = cnts[en_tmblk.STTIME_CN].dt.hour
    cnts[MIN_START_CN] = cnts[en_tmblk.STTIME_CN].dt.minute
    # Map the time period to the counts table
    cnts[TIMEPERIOD_CN] = cnts[HR_START_CN].map(TIME_PERIOD_HR_MAPPING)
    return cnts.sort_values(
        [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tmblk.STTIME_CN])


def _identify_midblock_count_stations(
        cnts: pd.DataFrame, 
        tcl_gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
    """ Identify unique count stations for storage in station database. 

    Args:
        cnts: counts DataFrame
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations. Station information includes:
            - source: denotes Toronto midblock in this case
            - station_id
            - cardinal direction
            - description
            - latitude
            - longitude
            - LineString denoting line shape [must match cardinal direction]

    """
    # working column names within this function
    OPPDIR_CN = 'opp_dir'
    
    # Find unique count locations, which in this case can be found from the 
    # combination of the TCL centreline ID and the direction
    stns = cnts.groupby([en_tmblk.CNTRLNID_CN, en_tmblk.DIR_CN])[[
            en_tmblk.LOCNAME_CN, en_tmblk.LAT_CN, en_tmblk.LON_CN
        ]].first().reset_index()

    # Merge in network centreline
    stns = stns.merge(
        tcl_gdf[[LS_FT_DIR, GPD_GEOM_COL]], 
        how='inner',
        left_on=[en_tmblk.CNTRLNID_CN], 
        right_index=True
    )
    stns = gpd.GeoDataFrame(
        stns, geometry=GPD_GEOM_COL, crs=tcl_gdf.crs)

    # Identify where the line geometry cardinal orientation does not match 
    # the count direction.
    stns[OPPDIR_CN] = stns[LS_FT_DIR].map(OPPOSITE_DIR)
    fltr_oppdir = (stns[en_tfc.DIR_CN] == stns[OPPDIR_CN])
    fltr_cross_dir = (stns[en_tfc.DIR_CN] != stns[LS_FT_DIR]) & \
        (stns[en_tfc.DIR_CN] != stns[OPPDIR_CN])

    # Reverse direction on elements where the line orientation is reverse
    # of the count direction. Can't swap out geometry on the GeoDataFrame, 
    # instead operates on a new series and then used GeoDataFrame.set_geometry 
    # to alter geometry on the dataframe.
    geometry = stns.geometry
    switched_geometry = geometry.loc[fltr_oppdir].reverse()
    geometry.loc[fltr_oppdir] = switched_geometry
    stns = stns.set_geometry(geometry)

    # Print and drop cross-direction count locations
    n_cross_dir_stns = fltr_cross_dir.sum()
    if n_cross_dir_stns > 0:
        print(f'    {n_cross_dir_stns} stations found where the count '
              f'direction is cross to the centreline direction '
              f'(e.g. NB count on EB link). You can manually change the '
              f'{LS_FT_DIR} field in the TCL file to manually adjust '
              f'directions for those roads.')

        if pd.options.display.max_rows is not None:
            prev_max_rows = pd.options.display.max_rows
            pd.options.display.max_rows = int(max(n_cross_dir_stns, prev_max_rows))
        print(stns.loc[
                fltr_cross_dir,  
                [en_tmblk.CNTRLNID_CN, en_tmblk.DIR_CN, LS_FT_DIR]
                ]
        )
        if pd.options.display.max_rows is not None:
            pd.options.display.max_rows = prev_max_rows
        stn_index_to_drop = stns.loc[fltr_cross_dir].index
        stns = stns.drop(stn_index_to_drop, axis=0)

    # Prepare dataframe to put into final format
    stns = stns.drop([LS_FT_DIR, OPPDIR_CN], axis=1)
    stns[en_tfc.SOURCE_CN] = en_tmblk.SOURCE
    stns = stns.rename({
        en_tmblk.CNTRLNID_CN: en_tfc.STNID_CN,
        en_tmblk.LOCNAME_CN: en_tfc.STN_DESC_CN,
        en_tmblk.LON_CN: en_tfc.STN_LON_CN,
        en_tmblk.LAT_CN: en_tfc.STN_LAT_CN,
    }, axis=1)
    stns[en_tfc.STNID_CN] = stns[en_tfc.STNID_CN].astype(str)
    # Put into proper order and set index
    stns = stns[en_tfc.STN_FIELDS]
    stns = stns.set_index(en_tfc.STN_INDEX_CNS)
    # Convert to final projection system, and we're done
    return stns.to_crs(WGS_CRS)


def _finalize_counts_table(
        f_cnts: pd.DataFrame, o_cnts: pd.DataFrame, stns: pd.DataFrame
    ) -> pd.DataFrame:
    """ Formats the midblock counts table into its final format.

    Args:
        f_cnts: Table with processed daily, peak-period
            and peak-hour counts.
        o_cnts: Original counts table, as read in from counts file.
        stns: Stations table as found by _identify_to_midblock_count_stations

    Returns:
        f_cnts table, cleaned and finalized into expected format.
        
    """
    f_cnts = f_cnts.copy()
    f_cnts[en_tfc.SOURCE_CN] = en_tmblk.SOURCE

    # Merge in the station ID
    cid_stnid_map = o_cnts.groupby(
        en_tmblk.ID_CN)[en_tmblk.CNTRLNID_CN].first().astype(str)

    cid_stnid_map.name = en_tfc.STNID_CN

    f_cnts = f_cnts.reset_index()
    f_cnts = f_cnts.merge(
        cid_stnid_map, left_on=en_tmblk.ID_CN, right_index=True)
    f_cnts = f_cnts.set_index(
        [en_tfc.SOURCE_CN , en_tfc.STNID_CN , en_tfc.DIR_CN , en_tfc.DATE_CN])

    # Add in any unused volume columns and ensure dtypes
    for cn in en_tfc.V_CNS.values():
        if cn not in f_cnts.columns:
            f_cnts[cn] = np.nan
        f_cnts[cn] = f_cnts[cn].astype(npdtype('f4'))

    # Remove counts that are not in the stations file
    f_cnts = f_cnts.loc[idx[
        stns.index.get_level_values(0), 
        stns.index.get_level_values(1), 
        stns.index.get_level_values(2), :]]
    return f_cnts[en_tfc.V_CNS.values()]


def _calculate_daily_volumes(
        cnts: pd.DataFrame, 
        volume_columns: str | list[str],
        colnames: str | list[str],
    ) -> pd.DataFrame:
    """ Calculate the daily_volume by station and day.
        
    Will return a NaN if count information is not available for all 24 hours
    of the day.
    
    Args:
        cnts: 
            counts table with columns appended by summarize_by_count_dates
        volume_columns: 
            columns to total
        colnames: 
            final name for each column in 'volume_columns' input
            
    Returns:
        pandas.DataFrame with daily volumes with optional filters applied.
        
    """
    n_records_cn = 'n_records'
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colnames, list):
        colnames = [colnames]
    if len(volume_columns) != len(colnames):
        raise ValueError(
            'volume_columns and colnames must be the same length.')
        
    grp_cns = [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN] 
    agg_funcs = {HR_START_CN: 'count'}
    for vc in volume_columns:
        agg_funcs[vc] = 'sum'
    dly_cnts = cnts.groupby(grp_cns).agg(agg_funcs)
    dly_cnts.columns = [n_records_cn] + colnames      
    dly_cnts.loc[dly_cnts[n_records_cn] < RECORDS_PER_DAY, colnames] = np.nan
    return dly_cnts[colnames]


def _calculate_period_volumes(
        cnts: pd.DataFrame, 
        volume_columns: str | list[str],
        colname_prefixes: str | list[str],
    ) -> pd.DataFrame:
    """ Calculates period volumes by station, day and time period. 
    
    Args:
        cnts: 
            counts table with columns appended by summarize_by_count_dates
        volume_columns: 
            columns representing the volumes to be summed into period volumes
        colname_prefixes: 
            final name for each column in 'volume_columns' input, will be 
            prepended to the time period to create the final column name
            
    Returns:
        pandas.DataFrame with period volumes by station and day.

    """
    OBSV_RECORDS_CN = 'observed_records'
    N_HRS_CN = 'n_hours_in_tp'
    EXP_RECORDS_CN = 'expected_records'
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colname_prefixes, list):
        colname_prefixes = [colname_prefixes]
    if len(volume_columns) != len(colname_prefixes):
        raise ValueError(
            'volume_columns and colname_prefixes must be the same length.')

    # Sum counts by time period
    grp_cns = [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN, TIMEPERIOD_CN]
    agg_funcs = {HR_START_CN: 'count'}
    for vc in volume_columns:
        agg_funcs[vc] = 'sum'
    per_cnts = cnts.groupby(grp_cns).agg(agg_funcs)
    per_cnts.columns = [OBSV_RECORDS_CN] + colname_prefixes

    # Filter out time periods with incomplete counts
    per_cnts[N_HRS_CN] = per_cnts.index.get_level_values(
        TIMEPERIOD_CN).map(TIME_PERIOD_NHOURS)
    per_cnts[EXP_RECORDS_CN] = per_cnts[N_HRS_CN] * RECORDS_PER_HOUR
    per_cnts.loc[per_cnts[OBSV_RECORDS_CN] < per_cnts[EXP_RECORDS_CN]] = np.nan
    per_cnts = per_cnts[colname_prefixes]

    # Unstack to produce period-level counts
    f = pd.DataFrame(per_cnts.unstack())  # keep the type hinting happy
    f.columns = ["".join(c) for c in f.columns.to_flat_index()]
    return f


def _calculate_peakhour_volumes(
        cnts: pd.DataFrame, 
        volume_columns: str | list[str],
        colname_prefixes: str | list[str]
    ) -> pd.DataFrame:
    """ Calculates peak-hour volumes by station, day and time period.  
    Args:
        cnts: 
            counts table with columns appended by summarize_by_count_dates
        volume_columns: 
            columns to total
        colname_prefixes: 
            final name for each column in 'volume_columns' input, will be 
            prepended to the time period to create the final column name
            
    Returns:
        pandas.DataFrame with peak-hour volumes.

    """  
    intp_cn = 'following_in_tp'
    id_cn = en_tmblk.ID_CN
    dir_cn = en_tmblk.DIR_CN
    tp_cn = TIMEPERIOD_CN
    shift = RECORDS_PER_HOUR - 1
    
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colname_prefixes, list):
        colname_prefixes = [colname_prefixes]
    if len(volume_columns) != len(colname_prefixes):
        raise ValueError(
            'volume_columns and colname_prefixes  must be the same length.')
    cnts = cnts.copy()  # to not mess with the original dataframe

    # Mark records that have 3 successive counts from same station and
    # direction. (Given the Toronto midblock use hard-coded 15-minute count 
    # intervals, the original interval + 3 more intervals gives an hour 
    # duration.
    cnts[intp_cn] = True
    cnts.loc[cnts[id_cn] != cnts[id_cn].shift(-shift), intp_cn] = False
    cnts.loc[cnts[dir_cn] != cnts[dir_cn].shift(-shift), intp_cn] = False
    cnts.loc[cnts[tp_cn] != cnts[tp_cn].shift(-shift), intp_cn] = False
    
    # Now look for a break in the counts in the 
    # current, current+1 and current_2 positions. (current+3) is ok.
    cnts['break_cn'] = False
    st_cn = en_tmblk.STTIME_CN
    cnts.loc[
        (cnts[st_cn].shift(-1) - cnts[st_cn]).dt.seconds != INTERVAL_SECS,
        'break_cn'
    ] = True
    for i in [0, 1, 2]:
        fltr = cnts['break_cn'].shift(-i)
        fltr = fltr.fillna(False)
        cnts.loc[fltr.to_numpy(), intp_cn] = False
    
    # Rolling sum to hourly volumes -- the sum will be incorrect where the has 
    # following flag is False. This is okay as those will be filtered out in 
    # the next step
    indexer = pd.api.indexers.FixedForwardWindowIndexer(
        window_size=RECORDS_PER_HOUR)
    rolling_sum_cns = [v_cn + '_rs' for v_cn in volume_columns]
    cnts[rolling_sum_cns] = cnts[volume_columns].rolling(window=indexer).sum()

    # Filter by has following counts flag
    cnts = cnts.loc[cnts[intp_cn]]

    # Find the max of each hourly volume column, this is the peak-hour volume
    grp_cns = [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN, tp_cn]
    pkhr_df = cnts.groupby(grp_cns)[rolling_sum_cns].max()
    pkhr_df.columns = colname_prefixes
    f = pd.DataFrame(pkhr_df.unstack())  # keep the type hinting happy
    f.columns = ["".join(c) for c in f.columns.to_flat_index()]
    return f


def _calculate_max15min_volumes(
        cnts: pd.DataFrame, 
        volume_columns: str | list[str],
        colnames: str | list[str],
    ) -> pd.DataFrame:
    """ Finds maximum 15-minute count by station and day.  
    Args:
        cnts: 
            counts table with columns appended by summarize_by_count_dates
        volume_columns: 
            columns to total
        colnames: 
            final name for each column in 'volume_columns' input
            
    Returns:
        pandas.DataFrame with peak-hour volumes.

    """  
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colnames, list):
        colnames = [colnames]
    if len(volume_columns) != len(colnames):
        raise ValueError(
            'volume_columns and colnames must be the same length.')
        
    grp_cns = [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN] 
    max_volumes = cnts.groupby(grp_cns)[volume_columns].max()
    max_volumes.columns = colnames
    return max_volumes[colnames]
