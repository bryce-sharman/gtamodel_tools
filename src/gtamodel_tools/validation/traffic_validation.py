import geopandas as gpd
from os import PathLike
from pathlib import Path
import pandas as pd
from typing import Tuple

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


    cnts = pd.read_csv(
        counts_fp, 
        dtype=en_traffic.CNT_DTYPES, 
        index_col=en_traffic.CNT_FIELDS_BASE,
        parse_dates=[en_traffic.TIME_START, en_traffic.TIME_END])
    return stns, cnts
