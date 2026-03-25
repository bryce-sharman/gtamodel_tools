"""
This file contains enums that are used across multiple modules.

"""

TIME_PERIODS = ['AM', 'MD', 'PM', 'EV', 'ON']
TIME_PERIOD_HR_RANGES = {
    'AM': list(range(6, 9)),   # 06:00 to 08:59
    'MD': list(range(9, 15)),  # 09:00 to 14:59
    'PM': list(range(15, 19)),  # 15:00 to 18:59
    'EV': list(range(19, 24)),  # 19:00 to 23:59
    'ON': list(range(0, 6))     # 00:00 to 5:59
}
    
TIME_PERIOD_NHOURS = {}
for tp, hrs_in_tp in TIME_PERIOD_HR_RANGES.items():
    TIME_PERIOD_NHOURS[tp] = len(hrs_in_tp)

TIME_PERIOD_HR_MAPPING = {
    hr: tp for tp, hrs in TIME_PERIOD_HR_RANGES.items() for hr in hrs}




DIRECTIONS = ['NB', 'EB', 'SB', 'WB']
OPPOSITE_DIR = {
    'NB': 'SB',
    'EB': 'WB',
    'SB': 'NB',
    'WB': 'EB'
}
GPD_GEOM_COL = 'geometry'
N_HRS_PER_DAY = 24
COT_CRS = 'EPSG:2952'
WGS_CRS = 'EPSG:4326'