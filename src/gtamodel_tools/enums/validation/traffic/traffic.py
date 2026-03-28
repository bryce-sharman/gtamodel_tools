""" 
Enumerations describing file structure of preprocessed traffic count data.

"""
from copy import deepcopy
from numpy import dtype as npdtype
from numpy import datetime64 as npdatetime64
from shapely.geometry import LineString

from gtamodel_tools.enums.common import TIME_PERIODS as TPS


SOURCE_CN = 'source'
STNID_CN = 'station_id'
DIR_CN = 'direction'
STN_INDEX_COLS = [SOURCE_CN, STNID_CN, DIR_CN]

COMMON_DTYPES = {
    SOURCE_CN: npdtype('S4'),         # 32-bit unsigned int, 0 to ~4.3 billion
    STNID_CN: npdtype('S10'),     
    DIR_CN: npdtype  
}

STN_DESC_CN = 'description'
STN_LAT_CN = 'latitude'
STN_LON_CN = 'longitude'
STN_GEOM_CN = 'geometry'
STN_FIELDS = [
    SOURCE_CN, STNID_CN, DIR_CN, STN_LAT_CN, STN_LON_CN, 
    STN_DESC_CN, STN_GEOM_CN
]
STN_DTYPES = deepcopy(COMMON_DTYPES)
STN_DTYPES[STN_DESC_CN] = npdtype('U')
STN_DTYPES[STN_LAT_CN] = npdtype('f8')
STN_DTYPES[STN_LON_CN] = npdtype('f8')
STN_DTYPES[STN_GEOM_CN] = LineString
STN_INDEX_CNS = [SOURCE_CN, STNID_CN, DIR_CN]

DATE_CN = 'date'
V_CNS = {}
for vehclass in ['TOT', 'CAR', 'BUS', 'TRK']:
    for tp in TPS:
        V_CNS[f'{vehclass}_PER_{tp}'] = f'v{vehclass.lower()}_{tp.lower()}per'
        V_CNS[f'{vehclass}_PKHR_{tp}'] = f'v{vehclass.lower()}_{tp.lower()}pkhr'
    V_CNS[f'{vehclass}_WKDAY'] = f'v{vehclass.lower()}_weekday'
    V_CNS[f'{vehclass}_WKEND'] = f'v{vehclass.lower()}_weekend'

CNT_INDEX_COLS = [SOURCE_CN, STNID_CN, DIR_CN, DATE_CN]
