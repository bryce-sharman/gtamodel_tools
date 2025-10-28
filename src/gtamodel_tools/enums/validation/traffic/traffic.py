import numpy as np

SOURCE = 'source'
STN_ID = 'station_id'
DIR = 'direction'
DESC = 'description'
LAT = 'latitude'
LON = 'longitude'
GEOM = 'geometry'

DATE = 'date'
TIME_START = 'time_start'
TIME_END = 'time_end'
COUNT_ID = 'count_id'
CNT_CAR = 'vol_passenger'
CNT_BUS = 'vol_buses'
CNT_STRAIGHTTRK = 'vol_straighttruck'
CNT_1TRAILERTRK = 'vol_singletrailer'
CNT_MULTITRAILERTRK = 'vol_multitrailer'
CNT_TRUCK = 'vol_truck'
CNT_HEAVY = 'vol_heavy'
CNT_TOTAL = 'vol_total'

STN_FIELDS = [SOURCE, STN_ID, DIR, DESC, LAT, LON, GEOM]
STN_INDEX_COLS = [SOURCE, STN_ID, DIR]

CNT_FIELDS_BASE = [SOURCE, STN_ID, DIR, DATE, TIME_START, TIME_END]
CNT_FIELDS_VOLONLY = CNT_FIELDS_BASE + [CNT_TOTAL]
CNT_FIELDS_CLASSIFIED = CNT_FIELDS_BASE + [
    CNT_CAR, CNT_BUS, CNT_STRAIGHTTRK, CNT_1TRAILERTRK, CNT_MULTITRAILERTRK,
    CNT_TRUCK, CNT_HEAVY, CNT_TOTAL
]


OPPOSITE_DIR = {
    'NB': 'SB',
    'EB': 'WB',
    'SB': 'NB',
    'WB': 'EB'
}

CRS = 'EPSG:4326'


STN_DTYPES = {
    SOURCE: str,
    STN_ID: str,
    DIR: str,
    DESC: str,
    LAT: np.float64,
    LON: np.float64,
}

CNT_DTYPES = {
    SOURCE: str,
    COUNT_ID: str,
    STN_ID : str,
    DIR: str,
    CNT_CAR: np.int64,
    CNT_BUS: np.int64,
    CNT_STRAIGHTTRK: np.int64,
    CNT_1TRAILERTRK: np.int64,
    CNT_MULTITRAILERTRK: np.int64,
    CNT_TRUCK: np.int64,
    CNT_HEAVY: np.int64,
    CNT_TOTAL: np.int64,
}
