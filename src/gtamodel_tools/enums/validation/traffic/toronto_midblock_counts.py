""" Enumerations for City of Toronto Midblock counts. """

from copy import deepcopy
from datetime import date, datetime
from enum import StrEnum
from numpy import dtype as npdtype
from pandas import CategoricalDtype as pdCategoricalDtype
import gtamodel_tools.enums.validation.traffic.traffic as en_traffic

SOURCE = 'TMBK'
WORKING_CRS = "EPSG:2952"
AXIS_OFFSET = 17  # degrees

#region Columns consistent across all Toronto Midblock count data files
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
    STTIME_CN: npdtype('U'),      # numpy datetime64
    ENDTIME_CN: npdtype('U'),     # numpy datetime64
    DIR_CN: npdtype('U')         # One of NB, SB, EW, WB
}
#endregion

#region Columns specific to raw volume data files
VOL_CN = 'volume_15min'
VONLY_DTYPES = deepcopy(COMMON_DTYPES)
VONLY_DTYPES[VOL_CN] = npdtype('f4')  
#endregion

#region Columns specific to classification and volume raw data files
VOLFHWA1_CN = 'vol_fwha1_motorbike'
VOLFHWA2_CN = 'vol_fwha2_cars'
VOLFHWA3_CN = 'vol_fwha3_pickups'
VOLFHWA4_CN = 'vol_fwha4_buses'
VOLFHWA5_CN = 'vol_fwha5'
VOLFHWA6_CN = 'vol_fwha6'
VOLFHWA7_CN = 'vol_fwha7'
VOLFHWA8_CN = 'vol_fwha8'
VOLFHWA9_CN = 'vol_fwha9'
VOLFHWA10_CN = 'vol_fwha10'
VOLFHWA11_CN = 'vol_fwha11'
VOLFHWA12_CN = 'vol_fwha12'
VOLFHWA13_CN = 'vol_fwha13'
CAR_VEHCLASS_COLS = [VOLFHWA1_CN, VOLFHWA2_CN, VOLFHWA3_CN]
BUS_VEHCLASS_COLS = [VOLFHWA4_CN]
TRUCK_VEHCLASS_COLS = [
    VOLFHWA5_CN, VOLFHWA6_CN, VOLFHWA7_CN, VOLFHWA8_CN, VOLFHWA9_CN,
    VOLFHWA10_CN, VOLFHWA11_CN, VOLFHWA12_CN, VOLFHWA13_CN
]
ALL_VEHCLASS_COLS = CAR_VEHCLASS_COLS + BUS_VEHCLASS_COLS + TRUCK_VEHCLASS_COLS
HVY_VEHCLASS_COLS = BUS_VEHCLASS_COLS + TRUCK_VEHCLASS_COLS

VEHCLASS_DTYPES = deepcopy(COMMON_DTYPES)
VEHCLASS_DTYPES[VOLFHWA1_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA2_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA3_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA4_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA5_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA6_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA7_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA8_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA9_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA10_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA11_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA12_CN] = npdtype('f4')
VEHCLASS_DTYPES[VOLFHWA13_CN] = npdtype('f4')
#endregion

#region Columns specific to speed and volume raw data files
VOL0119_CN = 'vol_1_19kph'
VOL2025_CN = 'vol_20_25kph'
VOL2630_CN = 'vol_26_30kph'
VOL3135_CN = 'vol_31_35kph'
VOL3640_CN = 'vol_36_40kph'
VOL4145_CN = 'vol_41_45kph'
VOL4650_CN = 'vol_46_50kph'
VOL5155_CN = 'vol_51_55kph'
VOL5660_CN = 'vol_56_60kph'
VOL6165_CN = 'vol_61_65kph'
VOL6670_CN = 'vol_66_70kph'
VOL7175_CN = 'vol_71_75kph'
VOL7680_CN = 'vol_76_80kph'
VOL81PL_CN = 'vol_81_160kph'
SPDCLS_COLS = [
    VOL0119_CN, VOL2025_CN, VOL2630_CN, VOL3135_CN, VOL3640_CN, VOL4145_CN,
    VOL4650_CN, VOL5155_CN, VOL5660_CN, VOL6165_CN, VOL6670_CN, VOL7175_CN,
    VOL7680_CN, VOL81PL_CN
]
SPDCLS_DTYPES = deepcopy(COMMON_DTYPES)
SPDCLS_DTYPES[VOL0119_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL2025_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL2630_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL3135_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL3640_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL4145_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL4650_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL5155_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL5660_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL6165_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL6670_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL7175_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL7680_CN] = npdtype('f4')
SPDCLS_DTYPES[VOL81PL_CN] = npdtype('f4')
#endregion

#region Imputed / derived columns
#  DIR_CN = 'direction'
GEOM_CN = 'geometry'
#endregion
