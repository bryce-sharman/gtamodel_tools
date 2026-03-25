""" Enumerations for City of Toronto Midblock counts. """

from numpy import dtype as npdtype

SOURCE = 'TMBK'
AXIS_OFFSET = 17  # degrees
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

ID_CN = 'count_id'  
LOCNAME_CN = 'location_name'
LON_CN = 'longitude'
LAT_CN = 'latitude'
CNTRLNID_CN = 'centreline_id'
STTIME_CN = 'time_start'
ENDTIME_CN = 'time_end'
DIR_CN = 'direction'
COMMON_DTYPES = {
    ID_CN: npdtype('u4'),         # 32-bit unsigned int, 0 to ~4.3 billion
    LOCNAME_CN: npdtype('U'),     # Unicode string
    LON_CN: npdtype('f8'),        # 64-bit (double-precision) float
    LAT_CN: npdtype('f8'),        # 64-bit (double-precision) float
    CNTRLNID_CN: npdtype('u4'),   # 32-bit unsigned int, 0 to ~4.3 billion
    STTIME_CN: npdtype('U'),      # Unicode string, will parse to datetime later
    ENDTIME_CN: npdtype('U'),     # Unicode string, will parse to datetime later
    DIR_CN: npdtype('U')         # One of NB, SB, EW, WB
}

VOLUME_TOTONLY_CNS = ['volume_15min']

VOLUME_SPDCLS_CNS = [
    'vol_1_19kph', 'vol_20_25kph', 'vol_26_30kph', 'vol_31_35kph', 
    'vol_36_40kph', 'vol_41_45kph', 'vol_46_50kph', 'vol_51_55kph',
    'vol_56_60kph', 'vol_61_65kph', 'vol_66_70kph', 'vol_71_75kph',
    'vol_76_80kph', 'vol_81_160kph'
]

VOLUME_FHWA_CNS = [
    'vol_fwha1_motorbike', 'vol_fwha2_cars', 'vol_fwha3_pickups', 
    'vol_fwha4_buses', 'vol_fwha5', 'vol_fwha6', 'vol_fwha7', 'vol_fwha8',
    'vol_fwha9' 'vol_fwha10' 'vol_fwha11' 'vol_fwha12' 'vol_fwha13'
]

CAR_CLASS_CNS = ['vol_fwha1_motorbike', 'vol_fwha2_cars', 'vol_fwha3_pickups']
BUS_CLASS_CNS = ['vol_fwha4_buses']
TRUCK_CLASS_CNS = [
    'vol_fwha5', 'vol_fwha6', 'vol_fwha7', 'vol_fwha8', 'vol_fwha9', 
    'vol_fwha10', 'vol_fwha11', 'vol_fwha12', 'vol_fwha13'
]
ALL_CLASS_CNS = CAR_CLASS_CNS + BUS_CLASS_CNS + TRUCK_CLASS_CNS