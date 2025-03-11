from datetime import date, datetime, time
import geopandas as gpd
from math import ceil
import numpy as np
from os import PathLike
from pathlib import Path
import pandas as pd
from typing import Hashable, List, Tuple

import gtamodel_tools.enums.validation.traffic.cordon_counts as en_cc
import gtamodel_tools.enums.validation.traffic.toronto as en_tocnts
import gtamodel_tools.enums.validation.traffic.traffic as en_traffic



def read_trafficcount_db(
        stations_fp: PathLike,
        counts_fp: PathLike,
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """ Read traffic count dataase

    Args:
        stations_fp: path to stations file
        counts_fp: path to counts file

    Returns:
        - GeoDataFrame of count stations
        - DataFrame of count data

    """
    # We can't set the index or dtypes in gpd.read_file, so set afterwards
    stns = gpd.read_file(stations_fp)
    for field, dtype in en_traffic.STN_DTYPES.items():
        stns[field] = stns[field].astype(dtype)
    stns = stns.set_index(en_traffic.STN_INDEX_COLS)
    if not stns.index.is_unique:
        raise ValueError('Non-unique index in stations table, look into this.')

    cnts = pd.read_csv(
        counts_fp, 
        dtype=en_traffic.CNT_DTYPES
    )
    cnts[en_traffic.DATE] = pd.to_datetime(
        cnts[en_traffic.DATE],
        format='%Y-%m-%d'
    )
    cnts[en_traffic.TIME_START] = pd.to_datetime(
        cnts[en_traffic.TIME_START],
        format='%H:%M:%S'
    )
    cnts[en_traffic.TIME_END] = pd.to_datetime(
        cnts[en_traffic.TIME_END],
        format='%H:%M:%S'
    )

    # Even after cleaning up the start times of some of the cordon counts
    # (which is done in preprocessing), there are a couple ... well currently 
    # only 1 ... counts with weird start and end times, remove these counts.
    fltr_sttime = cnts[en_traffic.TIME_START].dt.minute.isin([0, 15, 30, 45])
    fltr_endtime = cnts[en_traffic.TIME_END].dt.minute.isin([0, 15, 30, 45])
    cnts = cnts.loc[fltr_sttime & fltr_endtime]

    cnts = cnts.set_index(en_traffic.CNT_FIELDS_BASE)
    if not cnts.index.is_unique:
        raise ValueError('Non-unique index in counts table, look into this.')
    return stns, cnts


def calc_wkday_period_volume(
        cnts: pd.DataFrame, column: str, years: int | List[int], 
        start_time: time, end_time: time
    ) -> pd.Series:
    """ Calculate period traffic volume.

    Args:
        cnts:  pd.DataFrame
            Counts table
        columns: str
            Vehicle type for which to calculate total
        years: int or List[int]
            keep counts occuring in these years
        start_time: datetime.time
            Start time of interval (inclusive)
        end_time: datetime.time
            End time of interval (exclusive)

    Returns:
        pd.Series
            Total count of specified type over the period. A value is
            only returned if there is a count over all time intervals
            within the period.
    """
    cnts = filter_counts_by_years(cnts, years)
    cnts = filter_counts_in_time_interval(cnts, start_time, end_time)
    s = cnts[column]
    df = s.unstack(level=[en_traffic.TIME_START, en_traffic.TIME_END])
    df = df.dropna()
    volume = df.sum(axis=1)
    # It's possible that there are counts on more than one day, in this
    # case we'll just take the average volume
    return volume.groupby(level=en_traffic.STN_INDEX_COLS).mean()

def calc_wkday_pkhr_volume(
        cnts: pd.DataFrame, column: str, years: int | List[int], 
        start_time: time, end_time: time
    ) -> pd.Series:
    """ Calculate peak-hour traffic volume within the specified period.

    Args:
        cnts:  pd.DataFrame
            Counts table
        columns: str
            Vehicle type for which to calculate total
        years: int or List[int]
            keep counts occuring in these years
        start_time: datetime.time
            Start time of interval (inclusive)
        end_time: datetime.time
            End time of interval (exclusive)

    Returns:
        pd.Series
            Peak-hour count of specified type over the period. A value is
            only returned if there is a count over all time intervals
            within the period.
    """
    cnts = filter_counts_by_years(cnts, years)
    cnts = filter_counts_in_time_interval(cnts, start_time, end_time)
    s = cnts[column]
    u = s.unstack(level=[en_traffic.TIME_START, en_traffic.TIME_END])
    # For now, at least, only compute if all time intervals are present
    u = u.dropna()
    interval_durations = (u.columns.get_level_values(1) 
                          - u.columns.get_level_values(0)).seconds // 60.0
    if not interval_durations.nunique() == 1:
        raise ValueError("calc_wkday_pkhr_volume requires all time intervals "
                         "to have the same duration.")
    period_duration = (end_time.hour - start_time.hour) * 60 \
        + end_time.minute - start_time.minute
    n_intervals = ceil(period_duration / interval_durations[0])
    n_intervals_perhr = ceil(60.0 / interval_durations[0])
    hrly_counts = []
    for i in range(0, n_intervals - n_intervals_perhr + 1):
        hrly_counts.append(u.iloc[:, i:i+4].sum(axis=1))    
    df = pd.concat(hrly_counts, axis=1)
    volume = df.max(axis=1)

    # It's possible that there are counts on more than one day, in this
    # case we'll just take the average volume
    return volume.groupby(level=en_traffic.STN_INDEX_COLS).mean()




def filter_counts_by_years(
        cnts: pd.DataFrame, years: int | List[int]
    ) -> pd.DataFrame:
    """ Return counts within a set of years.

    Args:
        cnts:  pd.DataFrame
            Counts table
        years: int or List[int]
            keep counts occuring in these years
    Returns:
        pd.DataFrame
            Filtered counts, occurred within specified years.

    """
    if isinstance(years, Hashable):
        years = [years]
    year = cnts.index.get_level_values(en_traffic.DATE).year
    fltr = year.isin(years)
    return cnts.loc[fltr].copy()

def filter_weekday_counts(cnts: pd.DataFrame) -> pd.DataFrame:
    """ 
    Return a copy of the counts removing non-cordon-count counts 
    that occur on a weekend.

    Args:
        cnts: pd.DataFrame
            Counts table
    Returns:
        pd.DataFrame
            Counts table with weekend counts removed

    """
    fltr_cc = cnts.index.get_level_values(
        en_traffic.SOURCE).isin(en_cc.AGENCY.values())
    # Note that Monday is a 0 in the day_of_week property
    fltr_iswkday = cnts.index.get_level_values(
        en_traffic.DATE).day_of_week.isin([0, 1, 2, 3, 4])  
    return cnts.loc[fltr_cc | fltr_iswkday].copy()

def filter_counts_in_time_interval(
            cnts: pd.DataFrame, start_time: time, end_time: time
        ) -> pd.DataFrame:
    """ 
    Return a copy of the counts only keeping counts in the specified interval.

    Args:
        cnts: pd.DataFrame
            Counts table
        start_time: datetime.time
            Start time of interval (inclusive)
        end_time: datetime.time
            End time of interval (exclusive)
    Returns:
        pd.DataFrame
            Counts table only keeping counts where the count start time is
            between the input start_time (inclusive) and end_time (exclusive).

    """
    # Convert start and end times to numpy.datetime64, as that's what pandas uses
    start_time64 = np.datetime64(datetime(
        1900, 1, 1, start_time.hour, start_time.minute, start_time.second))
    end_time64 = np.datetime64(datetime(
        1900, 1, 1, end_time.hour, end_time.minute, end_time.second))
    mask_sttime = cnts.index.get_level_values(
        en_traffic.TIME_START) >= start_time64
    mask_endtime = cnts.index.get_level_values(
        en_traffic.TIME_START) < end_time64
    return cnts.loc[mask_sttime & mask_endtime].copy()