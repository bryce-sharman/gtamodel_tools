"""
Functions to read City of Toronto Speed-Volume Classificaiton (midblock)
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


import geopandas as gpd
import numpy as np
import pandas as pd
from pathlib import Path
from os import PathLike
from typing import List, Tuple

from gtamodel_tools.common.gis import calc_linestring_orientation


import gtamodel_tools.enums.validation.traffic.toronto_midblock_counts as en_tmblk
import gtamodel_tools.enums.validation.traffic.traffic as en_tfc
import gtamodel_tools.enums.validation.tcl as en_tcl


TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def read_midblock_counts(
        loc: str | PathLike,
        tcl_gdf: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
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
        print (f'  Processing file {fp.name}') 
        stns, counts = read_midblock_volume_counts(fp, tcl_gdf)
        stns_list.append(stns)
        counts_list.append(counts)
    print('')
    print('Processing raw speed-volume count files')
    for fp in loc.glob(pat_s):
        print (f'  Processing file {fp.name}') 
        stns, counts = read_midblock_speedvolume_counts(fp, tcl_gdf)
        stns_list.append(stns)
        counts_list.append(counts)
    print('')
    print('Processing raw class-volume count files')
    for fp in loc.glob(pat_c):
        print (f'  Processing file {fp.name}') 
        stns, counts = read_midblock_class_counts(fp, tcl_gdf)
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
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
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

    cols = [k for k in en_tmblk.VONLY_DTYPES.keys()]
    cnts = pd.read_csv(fp, usecols=cols, dtype=en_tmblk.VONLY_DTYPES)
    cnts = _process_count_times(cnts)
    
    # Identify the stations
    stns = _identify_to_midblock_count_stations(cnts, tcl_gdf)

    # Pre-process count data
    cnts_by_day = _test_count_covers_fullday(cnts)
    cnts2 = cnts.merge(cnts_by_day, on=[en_tmblk.ID_CN, en_tfc.DATE_CN])
    weekday_volumes = _calculate_daily_volumes(
        cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_WKDAY_CN, 'is_weekday==True')
    weekend_volumes = _calculate_daily_volumes(
        cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_WKEND_CN, 'is_weekday==False')
    ampkper_volumes = _calculate_wkday_pkper_volumes(
        'AM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_AMPKPD_CN)
    pmpkper_volumes = _calculate_wkday_pkper_volumes(
        'PM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_PMPKPD_CN)
    ampkhr_volumes = _calculate_wkday_pkhr_volumes(
        'AM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_AMPKHR_CN)
    pmpkhr_volumes = _calculate_wkday_pkhr_volumes(
        'PM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_PMPKHR_CN)
    f_cnts = pd.concat([
        ampkhr_volumes, ampkper_volumes, pmpkhr_volumes, 
        pmpkper_volumes, weekday_volumes, weekend_volumes
    ], axis=1)
    f_cnts = _finalize_counts_table(f_cnts, cnts, stns)
    return stns, f_cnts


def read_midblock_speedvolume_counts(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
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

    cols = [k for k in en_tmblk.SPDCLS_DTYPES.keys()]
    cnts = pd.read_csv(fp, usecols=cols, dtype=en_tmblk.SPDCLS_DTYPES)
    cnts = _process_count_times(cnts)

    # Add up all the counts by speed class into a single column
    # After this we can treat the exact same as the volume-only column
    cnts[en_tmblk.VOL_CN] = cnts[en_tmblk.SPDCLS_COLS].sum(axis=1)
    cnts = cnts.drop(en_tmblk.SPDCLS_COLS, axis=1)

    # Identify the stations
    stns = _identify_to_midblock_count_stations(cnts, tcl_gdf)

    # Pre-process count data
    cnts_by_day = _test_count_covers_fullday(cnts)
    cnts2 = cnts.merge(cnts_by_day, on=[en_tmblk.ID_CN, en_tfc.DATE_CN])
    weekday_volumes = _calculate_daily_volumes(
        cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_WKDAY_CN, 'is_weekday==True')
    weekend_volumes = _calculate_daily_volumes(
        cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_WKEND_CN, 'is_weekday==False')
    ampkper_volumes = _calculate_wkday_pkper_volumes(
        'AM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_AMPKPD_CN)
    pmpkper_volumes = _calculate_wkday_pkper_volumes(
        'PM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_PMPKPD_CN)
    ampkhr_volumes = _calculate_wkday_pkhr_volumes(
        'AM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_AMPKHR_CN)
    pmpkhr_volumes = _calculate_wkday_pkhr_volumes(
        'PM', cnts2, en_tmblk.VOL_CN, en_tfc.VTOT_PMPKHR_CN)
    f_cnts = pd.concat([
        ampkhr_volumes, ampkper_volumes, pmpkhr_volumes, 
        pmpkper_volumes, weekday_volumes, weekend_volumes
    ], axis=1)
    f_cnts = _finalize_counts_table(f_cnts, cnts, stns)
    return stns, f_cnts


def read_midblock_class_counts(
        fp: PathLike, 
        tcl_gdf: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
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

    cols = [k for k in en_tmblk.VEHCLASS_DTYPES.keys()]
    cnts = pd.read_csv(fp, usecols=cols, dtype=en_tmblk.VEHCLASS_DTYPES)
    cnts = _process_count_times(cnts)

    # Add up all the counts by road classification
    cnts['vol_car_15min'] = cnts[en_tmblk.CAR_VEHCLASS_COLS].sum(axis=1)
    cnts['vol_bus_15min'] = cnts[en_tmblk.BUS_VEHCLASS_COLS].sum(axis=1)
    cnts['vol_trk_15min'] = cnts[en_tmblk.TRUCK_VEHCLASS_COLS].sum(axis=1)
    cnts['vol_hvy_15min'] = cnts[en_tmblk.HVY_VEHCLASS_COLS].sum(axis=1)
    cnts['vol_all_15min'] = cnts[en_tmblk.ALL_VEHCLASS_COLS].sum(axis=1)
    

    cnts = cnts.drop(en_tmblk.ALL_VEHCLASS_COLS, axis=1)
    volume_cols = ['vol_car_15min', 'vol_bus_15min', 'vol_trk_15min', 
                   'vol_hvy_15min', 'vol_all_15min']

    # Identify the stations
    stns = _identify_to_midblock_count_stations(cnts, tcl_gdf)

    # Pre-process count data
    cnts_by_day = _test_count_covers_fullday(cnts)
    cnts2 = cnts.merge(cnts_by_day, on=[en_tmblk.ID_CN, en_tfc.DATE_CN])

    weekday_volumes = _calculate_daily_volumes(
        cnts2, 
        volume_cols, 
        [
            en_tfc.VCAR_WKDAY_CN, en_tfc.VBUS_WKDAY_CN, en_tfc.VTRK_WKDAY_CN, 
            en_tfc.VHVY_WKDAY_CN, en_tfc.VTOT_WKDAY_CN
        ], 
        'is_weekday==True'
    )
    weekend_volumes = _calculate_daily_volumes(
        cnts2, 
        volume_cols, 
        [
            en_tfc.VCAR_WKEND_CN, en_tfc.VBUS_WKEND_CN, en_tfc.VTRK_WKEND_CN, 
            en_tfc.VHVY_WKEND_CN, en_tfc.VTOT_WKEND_CN
        ],
        'is_weekday==False'
    )
    ampkper_volumes = _calculate_wkday_pkper_volumes(
        'AM', 
        cnts2, 
        volume_cols, 
        [
            en_tfc.VCAR_AMPKPD_CN, en_tfc.VBUS_AMPKPD_CN, en_tfc.VTRK_AMPKPD_CN, 
            en_tfc.VHVY_AMPKPD_CN, en_tfc.VTOT_AMPKPD_CN
        ],
    )
    pmpkper_volumes = _calculate_wkday_pkper_volumes(
        'PM', 
        cnts2, 
        volume_cols, 
        [
            en_tfc.VCAR_PMPKPD_CN, en_tfc.VBUS_PMPKPD_CN, en_tfc.VTRK_PMPKPD_CN, 
            en_tfc.VHVY_PMPKPD_CN, en_tfc.VTOT_PMPKPD_CN
        ],
    )
    ampkhr_volumes = _calculate_wkday_pkhr_volumes(
        'AM', 
        cnts2, 
        volume_cols, 
        [
            en_tfc.VCAR_AMPKHR_CN, en_tfc.VBUS_AMPKHR_CN, en_tfc.VTRK_AMPKHR_CN, 
            en_tfc.VHVY_AMPKHR_CN, en_tfc.VTOT_AMPKHR_CN
        ],
    )
    pmpkhr_volumes = _calculate_wkday_pkhr_volumes(
        'PM', 
        cnts2, 
        volume_cols, 
        [
            en_tfc.VCAR_PMPKHR_CN, en_tfc.VBUS_PMPKHR_CN, en_tfc.VTRK_PMPKHR_CN, 
            en_tfc.VHVY_PMPKHR_CN, en_tfc.VTOT_PMPKHR_CN
        ],
    )
    f_cnts = pd.concat([
        ampkhr_volumes, ampkper_volumes, pmpkhr_volumes, 
        pmpkper_volumes, weekday_volumes, weekend_volumes
    ], axis=1)
    f_cnts = _finalize_counts_table(f_cnts, cnts, stns)
    return stns, f_cnts

#region "Helper functions"
def _parse_timestring(s: pd.Series):
    time = pd.to_datetime(s, format=TIME_FORMAT)
    return time


def _process_count_times(cnts: pd.DataFrame) -> pd.DataFrame:
    """ Processes time stamps. 
    
    Args:
        cnts: original Toronto Midblock counts data read from files

    Returns:
        `cnts` DataFrame with the following modifications:
        - 'date': python date with the date of the count start time
        - 'is_weekday': True if the count day is a weekday, False otherwise
        - 'start_hr': hour (0-23) of count start time
        - 'start_min': min (0-59) of count start time
        - sorted by count_id, direction, start_time
    
    """
    cnts[en_tmblk.STTIME_CN] = _parse_timestring(cnts[en_tmblk.STTIME_CN])
    cnts[en_tmblk.ENDTIME_CN] = _parse_timestring(cnts[en_tmblk.ENDTIME_CN])

    cnts[en_tfc.DATE_CN] = cnts[en_tmblk.STTIME_CN].dt.date
    dayofweek = cnts[en_tfc.DATE_CN].apply(lambda x: x.weekday())
    cnts['is_weekday'] = True
    cnts.loc[dayofweek.isin([5, 6]), 'is_weekday'] = False
    cnts['hr_start'] = cnts[en_tmblk.STTIME_CN].dt.hour
    cnts['min_start'] = cnts[en_tmblk.STTIME_CN].dt.minute
    return cnts.sort_values(
        [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tmblk.STTIME_CN])


def _test_count_covers_fullday(df: pd.DataFrame) -> pd.Series:
    """ 
    Tests counts by count_id and date whether the count on that
    date spans the entire day.
    
    Args:
        df: counts DataFrame
    Returns
        pandas.Series with one row per count / day. 
        True if count covers entire day, False otherwise.
        
    """
    # For each count, find the number of days and the first day
    pt = df.groupby(
        [en_tmblk.ID_CN, en_tfc.DATE_CN])[
            en_tmblk.STTIME_CN].agg(['min', 'max'])
    pt.columns = ['dayfirst', 'daylast']
    
    first_hr = pt['dayfirst'].apply(lambda x: x.hour)
    first_min = pt['dayfirst'].apply(lambda x: x.minute)
    last_hr = pt['daylast'].apply(lambda x: x.hour)
    last_min = pt['daylast'].apply(lambda x: x.minute)
    pt['covers_fullday'] = False
    pt.loc[
        (first_hr == 0) & (first_min == 0) & (last_hr == 23) & (last_min==45), 
        'covers_fullday'] = True
    s = pt['covers_fullday']
    s.name = 'covers_fullday'
    return s

def _identify_to_midblock_count_stations(
        cnts: pd.DataFrame, 
        tcl_gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
    """ Identify unique count stations for storage in station database. 

    Args:
        cnts: counts DataFrame
        tcl_gdf: GeoDataFrame containing Toronto Centreline Network

    Returns:
        - GeoDataFrame of count stations

    """
    # Find unique count locations
    stns = cnts.groupby([en_tmblk.CNTRLNID_CN, en_tmblk.DIR_CN])[[
            en_tmblk.LOCNAME_CN, en_tmblk.LAT_CN, en_tmblk.LON_CN
        ]].first().reset_index()

    # Merge in network centreline
    stns = stns.merge(
        tcl_gdf[[en_tmblk.GEOM_CN]], 
        how='inner',
        left_on=[en_tmblk.CNTRLNID_CN], 
        right_index=True
    )
    stns = gpd.GeoDataFrame(
        stns, geometry=en_tcl.TCL_GEOM_COL, crs=tcl_gdf.crs)

    # Reverse the line direction when the line geometry cardinal
    # orientation does not match the count direction.
    # Need to do this operation in a projected coordinate system
    stns = stns.to_crs(en_tmblk.WORKING_CRS)

    stns['cntrln_dir'] = stns.geometry.apply(
        lambda x: calc_linestring_orientation(
            x, en_tmblk.AXIS_OFFSET, 'cartesian'))
    stns['opp_dir'] = stns['cntrln_dir'].map(en_tfc.OPPOSITE_DIR)
    stns['crossdir_flag'] = False
    for stni, stnr in stns.iterrows():
        if stnr[en_tmblk.DIR_CN] == stnr['opp_dir']:
            stns.at[stni, 'geometry'] = stns.at[stni, 'geometry'].reverse()
        elif stnr[en_tmblk.DIR_CN] != stnr['cntrln_dir']:
            stns.at[stni, 'crossdir_flag'] = True
  
    # Drop the counts where we cannot match the directions
    n_crossdir_links = stns['crossdir_flag'].sum()
    if n_crossdir_links > 0:
        print(f'    Removing counts from {n_crossdir_links} cross-direction '
              f'stations. Could not match count direction with centreline '
              f'orientation.')
        stns = stns.loc[~stns['crossdir_flag']]

    # Prepare dataframe to put into final format
    stns = stns.drop(['cntrln_dir', 'opp_dir', 'crossdir_flag'], axis=1)
    stns[en_tfc.SOURCE_CN] = en_tmblk.SOURCE
    stns = stns.rename({
        en_tmblk.CNTRLNID_CN: en_tfc.STNID_CN,
        en_tmblk.LOCNAME_CN: en_tfc.STN_DESC_CN,
        en_tmblk.LON_CN: en_tfc.STN_LON_CN,
        en_tmblk.LAT_CN: en_tfc.STN_LAT_CN,
        en_tmblk.GEOM_CN: en_tfc.STN_GEOM_CN
    }, axis=1)
    stns[en_tfc.STNID_CN] = stns[en_tfc.STNID_CN].astype(str)
    # Put into proper order and set index
    stns = stns[en_tfc.STN_FIELDS]
    stns = stns.set_index(en_tfc.STN_INDEX_CNS)
    # Convert to final projection system, and we're done
    return stns.to_crs(en_tfc.CRS)


def _finalize_counts_table(
        f_cnts: pd.DataFrame, o_cnts: pd.DataFrame, stns: pd.DataFrame
    ) -> pd.DataFrame:
    """ Formats the counts table into its final format.

    Args:
        f_cnts: Table with processed daily, peak-period
            and peak-hour counts.
        o_cnts: Original counts table, as read in from counts file.
        stns: Stations table as found by _identify_to_midblock_count_stations

    Returns:
        f_cnts table, cleaned and finalized into expected format.
        
    """
    f_cnts[en_tfc.SOURCE_CN] = en_tmblk.SOURCE
    # Merge in the station ID
    cid_stnid_map = o_cnts.groupby(
        en_tmblk.ID_CN)[en_tmblk.CNTRLNID_CN].first().astype(str)
    cid_stnid_map.name = en_tfc.STNID_CN
    f_cnts = f_cnts.reset_index()
    f_cnts = f_cnts.merge(cid_stnid_map, left_on=en_tmblk.ID_CN, right_index=True)
    f_cnts = f_cnts.set_index(
        [en_tfc.SOURCE_CN , en_tfc.STNID_CN , en_tfc.DIR_CN , en_tfc.DATE_CN])
    # Add in any unused columns
    for cn in en_tfc.COUNT_FIELDS:
        if cn not in f_cnts.columns:
            f_cnts[cn] = np.NaN
    # Set the dtypes
    for cn in en_tfc.COUNT_FIELDS:
        f_cnts[cn] = f_cnts[cn].astype(en_tfc.CNT_DTYPES[cn])

    # Remove counts that are not in the stations file
    f_cnts_nodate = f_cnts.reset_index(en_tfc.DATE_CN)
    matched_f_cnts = f_cnts_nodate.loc[stns.index]
    matched_f_cnts = matched_f_cnts.reset_index().set_index(
        [en_tfc.SOURCE_CN, en_tfc.STNID_CN, en_tfc.DIR_CN, en_tfc.DATE_CN])
    return matched_f_cnts[en_tfc.COUNT_FIELDS]


def _calculate_daily_volumes(
        df: pd.DataFrame, 
        volume_columns: str | List[str],
        colnames: str | List[str],
        filter_expr: str | None = None
    ) -> pd.DataFrame:
    """ Calculate the daily_volume by count/day, for weekdays only. 
    
    Args:
        df: counts table with columns appended by summarize_by_count_dates
        volume_columns: columns to total
        colnames: final name for each column in 'volume_columns' input
        filter_expr: Optional filter expression to be evaluated by
            pandas.eval. 
            
    Returns:
        pandas.DataFrame with daily volumes with optional filters applied.
        
    """
    err_msg = 'volume_columns and colnames  must be the same length.'
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colnames, list):
        colnames = [colnames]
    if len(volume_columns) != len(colnames):
        raise ValueError(err_msg)
    if filter_expr:
        pt = df[df.eval(filter_expr)].groupby(
                [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN]
            )[volume_columns].sum()
    else:
        pt = df.groupby(
                [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN]
            )[volume_columns].sum()

    pt.columns = colnames
    return pd.DataFrame(pt)

def _calculate_wkday_pkper_volumes(
        peak_period: str,
        df: pd.DataFrame, 
        volume_columns: str | List[str],
        colnames: str | List[str],
    ) -> pd.DataFrame:
    """ Calculate weekday peak period volumes. 
    
    Args:
        peak_period: One of 'AM' or 'PM'
        df: counts table with columns appended by summarize_by_count_dates
        volume_columns: columns to total
        colnames: final name for each column in 'volume_columns' input
            
    Returns:
        pandas.DataFrame with daily volumes with optional filters applied.
        The column names are set as specified
        
    """

    if peak_period == 'AM':
        filter_expr = 'is_weekday==True and hr_start in (6, 7, 8)'
    elif peak_period == 'PM':
        filter_expr = 'is_weekday==True and hr_start in (15, 16, 17, 18)'
    else:
        raise ValueError('peak_period must be either "AM" or "PM"')
        
    err_msg = 'volume_columns and colnames  must be the same length.'
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colnames, list):
        colnames = [colnames]
    if len(volume_columns) != len(colnames):
        raise ValueError(err_msg)
    pt = df[df.eval(filter_expr)].groupby(
        [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN])[volume_columns].sum()
    pt.columns = colnames
    return pd.DataFrame(pt)

def _calculate_wkday_pkhr_volumes(
        peak_period: str,
        df: pd.DataFrame, 
        volume_columns: str | List[str],
        colnames: str | List[str]
    ) -> pd.DataFrame:
    """ Calculate weekday peak period volumes. 
    
    Args:
        peak_period: One of 'AM' or 'PM'
        df: counts table with columns appended by summarize_by_count_dates
        volume_columns: columns to total
        colnames: final name for each column in 'volume_columns' input
            
    Returns:
        pandas.DataFrame with daily volumes with optional filters applied.
        The column names are set as specified.

    Notes:
        This function bases whether a count is in the specified period entirely
        on the count time. For example: the AM peak-hour includes count
        intervals that start at 08:30 even though the time interval extends
        beyond 9:00. It is felt that this is appropriate to capture peak
        hour volumes, but users should note potential blending in 
        counts between different periods.
        
    """
    if peak_period == 'AM':
        hours = [6, 7, 8]
    elif peak_period == 'PM':
        hours = [15, 16, 17, 18]
    else:
        raise ValueError('peak_period must be either "AM" or "PM"')
       
    err_msg = 'volume_columns and colnames  must be the same length.'
    if not isinstance(volume_columns, list):
        volume_columns = [volume_columns]
    if not isinstance(colnames, list):
        colnames = [colnames]
    if len(volume_columns) != len(colnames):
        raise ValueError(err_msg)
    
    df = df.copy()  # to not mess with the original dataframe
    
    # Add information from three following counts
    # Given the Toronto midblock use hard-coded 15-minute count intervals, 
    # the original interval + 3 more intervals gives an hour duration. 
    for i in range(1, 4):
        df[en_tmblk.ID_CN + f'_{i}'] = df[en_tmblk.ID_CN].shift(-i)
        df[en_tmblk.DIR_CN + f'_{i}'] = df[en_tmblk.DIR_CN].shift(-i)
        for vol_col in volume_columns:
            df[vol_col + f'_{i}'] = df[vol_col].shift(-i)
            
    # filter out records with no following counts
    # seen by changes in the count_id or direction
    df['has_following_counts'] = True
    for i in range(1, 4):
        df.loc[
                df[en_tmblk.ID_CN] != df[en_tmblk.ID_CN + f'_{i}'], 
                'has_following_counts'
            ] = False
        df.loc[
                df[en_tmblk.DIR_CN] != df[en_tmblk.DIR_CN + f'_{i}'], 
                'has_following_counts'
            ] = False
    dfhfc = df[df['has_following_counts']].copy()
    
    # Filter for records in the proper time period
    # Only the starting hour is tested to let the hour-long count dureation
    # extend beyond the time period end time.
    dfhfc = dfhfc[(dfhfc['is_weekday']) & (dfhfc['hr_start'].isin(hours))]

    # Sum to hourly volumes
    for vol_col in volume_columns:
        dfhfc[vol_col + '_hr'] = dfhfc[vol_col]
        for i in range(1, 4):
            dfhfc[vol_col + '_hr'] += dfhfc[vol_col + f'_{i}']
    
    # Find the max of each hourly volume column, this is the peak-hour volume
    hrly_vol_cns = []
    for vol_col in volume_columns:
        hrly_vol_cns.append(vol_col + '_hr')
    pkhr_df = dfhfc.groupby(
        [en_tmblk.ID_CN, en_tmblk.DIR_CN, en_tfc.DATE_CN])[hrly_vol_cns].max()
    pkhr_df.columns = colnames
    return pkhr_df
#endregion