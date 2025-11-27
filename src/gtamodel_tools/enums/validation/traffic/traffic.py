from copy import deepcopy
from numpy import dtype as npdtype
from numpy import datetime64 as npdatetime64
from shapely.geometry import LineString

OPPOSITE_DIR = {
    'NB': 'SB',
    'EB': 'WB',
    'SB': 'NB',
    'WB': 'EB'
}
CRS = 'EPSG:4326'

#region common columns and dtypes
SOURCE_CN = 'source'
STNID_CN = 'station_id'
DIR_CN = 'direction'
STN_INDEX_COLS = [SOURCE_CN, STNID_CN, DIR_CN]

COMMON_DTYPES = {
    SOURCE_CN: npdtype('S4'),         # 32-bit unsigned int, 0 to ~4.3 billion
    STNID_CN: npdtype('S10'),     
    DIR_CN: npdtype  
}
#endregion

#region Stations file column names and dtypes
STN_DESC_CN = 'description'
STN_LAT_CN = 'latitude'
STN_LON_CN = 'longitude'
STN_GEOM_CN = 'geometry'
STN_FIELDS = [
    SOURCE_CN, STNID_CN, DIR_CN, STN_DESC_CN, 
    STN_LAT_CN, STN_LON_CN, STN_GEOM_CN
]
STN_DTYPES = deepcopy(COMMON_DTYPES)
STN_DTYPES[STN_DESC_CN] = npdtype('U')
STN_DTYPES[STN_LAT_CN] = npdtype('f8')
STN_DTYPES[STN_LON_CN] = npdtype('f8')
STN_DTYPES[STN_GEOM_CN] = LineString
STN_INDEX_CNS = [SOURCE_CN, STNID_CN, DIR_CN]
#endregion

#region Counts file column names
DATE_CN = 'date'
VTOT_AMPKHR_CN = 'vtotal_ampkhr'
VTOT_AMPKPD_CN = 'vtotal_ampkper'
VTOT_PMPKHR_CN = 'vtotal_pmpkhr'
VTOT_PMPKPD_CN = 'vtotal_pmpkper'
VTOT_WKDAY_CN = 'vtotal_weekday'
VTOT_WKEND_CN = 'vtotal_weekend'
VCAR_AMPKHR_CN = 'vcars_ampkhr'
VCAR_AMPKPD_CN = 'vcars_ampkper'
VCAR_PMPKHR_CN = 'vcars_pmpkhr'
VCAR_PMPKPD_CN = 'vcars_pmpkper'
VCAR_WKDAY_CN = 'vcars_weekday'
VCAR_WKEND_CN = 'vcars_weekend'
VBUS_AMPKHR_CN = 'vbuses_ampkhr'
VBUS_AMPKPD_CN = 'vbuses_ampkper'
VBUS_PMPKHR_CN = 'vbuses_pmpkhr'
VBUS_PMPKPD_CN = 'vbuses_pmpkper'
VBUS_WKDAY_CN = 'vbuses_weekday'
VBUS_WKEND_CN = 'vbuses_weekend'
VTRK_AMPKHR_CN = 'vtrucks_ampkhr'
VTRK_AMPKPD_CN = 'vtrucks_ampkper'
VTRK_PMPKHR_CN = 'vtrucks_pmpkhr'
VTRK_PMPKPD_CN = 'vtrucks_pmpkper'
VTRK_WKDAY_CN = 'vtrucks_weekday'
VTRK_WKEND_CN = 'vtrucks_weekend'
VHVY_AMPKHR_CN = 'vheavy_ampkhr'
VHVY_AMPKPD_CN = 'vheavy_ampkper'
VHVY_PMPKHR_CN = 'vheavy_pmpkhr'
VHVY_PMPKPD_CN = 'vheavy_pmpkper'
VHVY_WKDAY_CN = 'vheavy_weekday'
VHVY_WKEND_CN = 'vheavy_weekend'
CNT_INDEX_COLS = [SOURCE_CN, STNID_CN, DIR_CN, DATE_CN]
COUNT_FIELDS = [
    VTOT_AMPKHR_CN, VTOT_AMPKPD_CN, VTOT_PMPKHR_CN, VTOT_PMPKPD_CN, 
    VTOT_WKDAY_CN, VTOT_WKEND_CN, VCAR_AMPKHR_CN, VCAR_AMPKPD_CN, 
    VCAR_PMPKHR_CN, VCAR_PMPKPD_CN, VCAR_WKDAY_CN, VCAR_WKEND_CN, 
    VBUS_AMPKHR_CN, VBUS_AMPKPD_CN, VBUS_PMPKHR_CN, VBUS_PMPKPD_CN, 
    VBUS_WKDAY_CN, VBUS_WKEND_CN, VTRK_AMPKHR_CN, VTRK_AMPKPD_CN, 
    VTRK_PMPKHR_CN, VTRK_PMPKPD_CN, VTRK_WKDAY_CN, VTRK_WKEND_CN,
    VHVY_AMPKHR_CN, VHVY_AMPKPD_CN, VHVY_PMPKHR_CN, VHVY_PMPKPD_CN, 
    VHVY_WKDAY_CN, VHVY_WKEND_CN
]

# Note that all counts must be floats to accommodate NaNs
CNT_DTYPES = deepcopy(COMMON_DTYPES)
CNT_DTYPES[DATE_CN] = npdatetime64
CNT_DTYPES[VTOT_AMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VTOT_AMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VTOT_PMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VTOT_PMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VTOT_WKDAY_CN] = npdtype('f4')
CNT_DTYPES[VTOT_WKEND_CN] = npdtype('f4')
CNT_DTYPES[VCAR_AMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VCAR_AMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VCAR_PMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VCAR_PMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VCAR_WKDAY_CN] = npdtype('f4')
CNT_DTYPES[VCAR_WKEND_CN] = npdtype('f4')
CNT_DTYPES[VBUS_AMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VBUS_AMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VBUS_PMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VBUS_PMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VBUS_WKDAY_CN] = npdtype('f4')
CNT_DTYPES[VBUS_WKEND_CN] = npdtype('f4')
CNT_DTYPES[VTRK_AMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VTRK_AMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VTRK_PMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VTRK_PMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VTRK_WKDAY_CN] = npdtype('f4')
CNT_DTYPES[VTRK_WKEND_CN] = npdtype('f4')
CNT_DTYPES[VHVY_AMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VHVY_AMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VHVY_PMPKHR_CN] = npdtype('f4')
CNT_DTYPES[VHVY_PMPKPD_CN] = npdtype('f4')
CNT_DTYPES[VHVY_WKDAY_CN] = npdtype('f4')
CNT_DTYPES[VHVY_WKEND_CN] = npdtype('f4')
