""" Enumerations for City of Toronto Midblock counts. """

import gtamodel_tools.enums.validation.traffic.traffic as en_traffic

SOURCE = 'TMBK'

INDEX_COL = 'id'
STNID_COL = 'count_id'
STNDESC_COL = 'location_name'
LON_COL = 'longitude'
LAT_COL = 'latitude'
SHPID_COL = 'centreline_id'
STTIME_COL = 'time_start'
ENDTIME_COL = 'time_end'
DIR_COL = 'direction'
GEOM_COL = 'geometry'

# Midblock Class Count Columns
FHWA01_COL = 'vol_fwha1_motorbike'
FHWA02_COL = 'vol_fwha2_cars'
FHWA03_COL = 'vol_fwha3_pickups'
FHWA04_COL = 'vol_fwha4_buses'
FHWA05_COL = 'vol_fwha5'
FHWA06_COL = 'vol_fwha6'
FHWA07_COL = 'vol_fwha7'
FHWA08_COL = 'vol_fwha8'
FHWA09_COL = 'vol_fwha9'
FHWA10_COL = 'vol_fwha10'
FHWA11_COL = 'vol_fwha11'
FHWA12_COL = 'vol_fwha12'
FHWA13_COL = 'vol_fwha13'
FHWA_COLS = [
    FHWA01_COL, FHWA02_COL, FHWA03_COL, FHWA04_COL, FHWA05_COL, FHWA06_COL, 
    FHWA07_COL, FHWA08_COL, FHWA09_COL, FHWA10_COL, FHWA11_COL, FHWA12_COL, 
    FHWA13_COL
]


# Volume data
TOTAL_COL = 'volume_15min'			

WORKING_CRS = "EPSG:2952"

AXIS_OFFSET = 17  # degrees

RENAME_STNS = {
    STNID_COL: en_traffic.STN_ID, 
    DIR_COL: en_traffic.DIR,
    STNDESC_COL: en_traffic.DESC, 
    LAT_COL: en_traffic.LAT, 
    LON_COL: en_traffic.LON,
    GEOM_COL: en_traffic.GEOM
}

RENAME_CNTS_BASE = {
    INDEX_COL: en_traffic.COUNT_ID,
    STNID_COL: en_traffic.STN_ID,
    DIR_COL: en_traffic.DIR,
    STTIME_COL: en_traffic.TIME_START,
    ENDTIME_COL: en_traffic.TIME_END,

}
RENAME_CNTS_VOLONLY = RENAME_CNTS_BASE.copy()
RENAME_CNTS_VOLONLY[TOTAL_COL] = en_traffic.CNT_TOTAL