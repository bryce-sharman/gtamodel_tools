""" Enumerations for City of Toronto Turning Movement counts. 

Toronto Turning Movement Count fields:
    - _id: Unique row identifier for Open Data database
        Not used.
    - count_id:	Unique identifier for each Turning Movement Count. 
        Unique for location and date of count. 
    - count_date: Date the count was conducted. 
        For Turning Movement Counts, studies are conducted on one day only.
        Not used.
    - location_name: Human-readable name where count was conducted
    - longitude: Longitude GPS coordinate
    - latitude: Latitude GPS coordinate
    - centreline_type: Intersection node or Midblock segment. 
        - if 1: is Midblock segment; cross-reference centreline_id with 
        CENTRELINE_ID in the Toronto Centreline dataset 
        (https://open.toronto.ca/dataset/toronto-centreline-tcl/).
        - if 2: is Intersection node; cross-reference centreline_id with 
        INTERSECTION_ID in the Intersection File dataset.
        (https://open.toronto.ca/dataset/intersection-file-city-of-toronto/). 
    - centreline_id: Unique location identifier that corresponds to the Toronto 
        Centreline or Intersection File datasets. 
    - px: If there is a traffic control signal at the location, this is the 
        unique identifier for the signal. Join to Traffic Signals Tabular 
        (https://open.toronto.ca/dataset/traffic-signals-tabular/).
        Not used.
    - start_time: Start time of the 15-minute interval
    - end_time: End time of the 15-minute interval
    - volume columns by:
        - approach: [n, s, e, w]
        - vehicle class [cars, truck, bus, peds, bike], 
        - movement [r, t, l] for cars, bus and truck only; bike and peds only 
          have total volume by approach with no turning movement breakdown.

"""
from numpy import dtype as npdtype

SOURCE = 'TTMC'
AXIS_OFFSET = 17  # degrees
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DATE_FORMAT = '%m/%d/%Y'

ID_CN = 'count_id'  
LOCNAME_CN = 'location_name'
LON_CN = 'longitude'
LAT_CN = 'latitude'
CNTTYPE_CN = 'centreline_type'
CNTRLNID_CN = 'centreline_id'
STTIME_CN = 'start_time'
ENDTIME_CN = 'end_time'
DTYPES = {
    ID_CN: npdtype('u4'),         # 32-bit unsigned int
    LOCNAME_CN: npdtype('U'),     # Unicode string
    LON_CN: npdtype('f8'),        # 64-bit (double-precision) float
    LAT_CN: npdtype('f8'),        # 64-bit (double-precision) float
    CNTTYPE_CN: npdtype('u1'), # This is 1 or 2, so uint8 is sufficient
    CNTRLNID_CN: npdtype('u4'),   # 32-bit unsigned int
    STTIME_CN: npdtype('U'),      # 
    ENDTIME_CN: npdtype('U'),     # 
}

APPROACHES = ['n', 's', 'e', 'w']
VEHICLE_MODES = ['cars', 'truck', 'bus']
ACTIVE_MODES = ['peds', 'bike']
MOVEMENTS = ['r', 't', 'l']  # for cars, trucks, buses only
MOVEMENT_CNS = []
for a in APPROACHES:
    for v in VEHICLE_MODES:
        for m in MOVEMENTS:
            col_name = f'{a}_appr_{v}_{m}'
            DTYPES[col_name] = npdtype('f4') 
            MOVEMENT_CNS.append(col_name)
    for v in ACTIVE_MODES:
        col_name = f'{a}_appr_{v}'
        DTYPES[col_name] = npdtype('f4')
        MOVEMENT_CNS.append(col_name)

TYPE_CENTERLINE = 1
TYPE_INTERSECTION = 2

# Intersection centreline_id to leg centreline_id mapping file
INTSC_CN = 'intersection_centreline_id'
LEG_CNTRLN_CN = 'leg_centreline_id'
LEG_DIR_CN = 'leg'
LEG_STNAME_CN = 'street_name'
INTSC_MAPPING_DTYPES = {
    INTSC_CN: npdtype('u4'),
    LEG_CNTRLN_CN: npdtype('u4'),
    LEG_DIR_CN: npdtype('U'),
    LEG_STNAME_CN: npdtype('U')
}
INTSC_CENTRNLN_CNS = [INTSC_CN, LEG_CNTRLN_CN, LEG_DIR_CN]

OUT_DIR_DICT = {
    'north': 'NB',
    'south': 'SB',
    'east': 'EB',
    'west': 'WB'
}
IN_DIR_DICT = {
    'north': 'SB',
    'south': 'NB',
    'east': 'WB',
    'west': 'EB'
}