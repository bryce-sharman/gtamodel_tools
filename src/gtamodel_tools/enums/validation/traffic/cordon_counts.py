import gtamodel_tools.enums.validation.traffic.traffic as en_traffic

AGENCY = {
    'Durham': 'CCDR',
    'Halton': 'CCHL',
    'Hamilton': 'CCHM',
    'Peel': 'CCPL',
    'Toronto': 'CCTO',
    'York': 'CCYK'
}

CCSTNS_ID_COL = 'Id'
CCSTNS_DIR_COL = 'DIR'
CCSTNS_DESC_COL = 'STN_DESC'
CCSTNS_X_COL = 'x-coord'
CCSTNS_Y_COL = 'y-coord'
CCSTNS_GEOM_COL = 'geometry'
CCSTNS_CRS = 'EPSG:26917'

CC_CNT_STN_COL = 'Station'
CC_CNT_DIR_COL = 'Direction'
CC_SRTTIME_COL = 'StartTime'
CC_ENDTIME_COL = 'EndTime'

TOTAL_COL = 'tot_veh1'
# FHWA 1-3 -- includes light trucks
PASS_CAR_COLS = [
    'auto_atr1', 'auto1', 'auto2',   'auto3', 'auto4',  'cab1', 'cab2',  'cab3', 
    'cab4',  'truck_l1', 'truck_l_11', 'truck_l_21', 'truck_l_22', 'truck_l_31',
    'truck_l_33', 'truck_l_41', 'truck_l_44'
]
# Trucks
STRAIGHT_TRK_COLS = ['truck_a1', 'truck_h1', 'truck_m1']
SINGLETRAILER_TRK_COLS = ['htt1', 'truck_h_t1', 'truck_tr1']
MULTITRAILER_TRK_COLS = ['truck_mtr1']

# Transit
TRANS_VEH_COLS = [
    'bram_bus1', 'bus1', 'go_bus1', 'miss_bus1', 'mun_bus1',  'oth_bus1', 
    'reg_bus1',  'st_car1', 'subway1',  'ttc_bus1',  'viva_bus1', 'york_bus1',  
    'bus_atr1'
]
# LOCALTRANS_OCC_COLS = [
#     'bram_bus_oc1', 'bus_oc1', 'go_bus_oc1', 'miss_bus_oc1', 'mun_bus_oc1',  
#     'oth_bus_oc1', 'st_car_oc1', 'subway_oc1', 'ttc_bus_oc1',  'viva_bus_oc1',  
#     'viva_oc1', 'york_bus_oc1'
# ]

AXIS_OFFSET = 17
MAX_MATCH_DISTANCE = 75  # metres

RENAME_STN_COLS = {
    CCSTNS_ID_COL: en_traffic.STN_ID, 
    CCSTNS_DIR_COL: en_traffic.DIR,
    CCSTNS_DESC_COL: en_traffic.DESC, 
    CCSTNS_GEOM_COL: en_traffic.GEOM
}

RENAME_COUNT_COLS = {
    CC_CNT_STN_COL: en_traffic.STN_ID,
    CC_CNT_DIR_COL: en_traffic.DIR,
    CC_SRTTIME_COL: en_traffic.TIME_START,
    CC_ENDTIME_COL: en_traffic.TIME_END
}