# MicroSim Enums for GTAModel v4.0

import numpy as np
import pandas as pd


ZONE_DTYPE = np.dtype('u2')       # 16-bit, range between 0 and 65,635
WEIGHT_DTYPE = np.dtype('f4')     # 32-bit
SHORTUINT_DTYPE = np.dtype('u1')  # 8-bit, range between 0 and 255
RECORD_DTYPE = np.dtype('u4')     # 32-bit, range between 0 and ~4.3 billion
BOOL_DTYPE = np.dtype('?') 
TIME_DTYPE = np.dtype('f2')       # It's minutes after midnight, doesn't need
                                  # to be very precise

SEX_DTYPE = pd.CategoricalDtype(categories=['M', 'F'])
EMP_OR_STUDENT_STATUS_DTYPE = pd.CategoricalDtype(categories=['F', 'O', 'P'])
OCCUPATION_STATUS_DTYPE = pd.CategoricalDtype(
    categories=['P', 'G', 'O', 'S', 'M']
)
ACTIVTY_DTYPE = pd.CategoricalDtype(
    categories=[
        'Home', 'PrimaryWork', 'School', 'WorkBasedBusiness', 'Market'
        'IndividualOther', 'JointOther', 'SecondaryWork', 'JointMarket'
        ]
)
MODE_DTYPE = pd.CategoricalDtype(
    categories=[
        'Walk', 'WAT', 'Auto', 'Carpool', 'Schoolbus', 'RideShare', 'Passenger',
        'Bicycle', 'DAT'
    ]
)
TRIPDIR_DTYPE = pd.CategoricalDtype(
    categories=['auto2transit' or 'transit2auto']
)

# I will column used in an index here so that it can ber
# referenced without hard coding.
WEIGHT = 'weight'
HHLD = 'household_id'
HOME_ZONE = 'home_zone'
N_PERSONS = 'persons'
DWELLING_TYPE = 'dwelling_type'
N_VEHICLES = 'vehicles'
INCOME_CAT = 'income_class'

# Person columns
PERSON = 'person_id'
AGE = 'age'
GENDER = 'sex'
WORK_ZONE = 'work_zone'
SCHOOL_ZONE = 'school_zone' 
EMP_STATUS = 'employment_status'
OCCUPATION = 'occupation'
HAS_LICENSE = 'license'

# Trip and trip modes columns
TRIP = 'trip_id'
MODE = 'mode'
OZONE_COL = 'o_zone'
DZONE_COL = 'd_zone'
O_DEPART = 'o_depart'
D_ARRIVE = 'd_arrive'
O_ACTIVITY = 'o_act'
D_ACTIVITY = 'd_act'
DEPTIME_COL = 'o_depart'
ARRTIME_COL = 'd_arrive'

# Trip station columns
STATION = 'station'
DIRECTION = 'direction'
PASS = 'passenger_id'
PASSTRIP = 'passenger_trip_id'

# The following are the column names in GTAModel v4.1/v4.2, which are 
# considered as the current standard. Provision is made in the 
# config file to rename these columns, such as for v4.0 standard.
HHLD_DTYPES = {
    HHLD: RECORD_DTYPE,
    HOME_ZONE: ZONE_DTYPE,   
    WEIGHT: WEIGHT_DTYPE,
    N_PERSONS: SHORTUINT_DTYPE,
    DWELLING_TYPE: SHORTUINT_DTYPE,
    N_VEHICLES: SHORTUINT_DTYPE,
    INCOME_CAT: SHORTUINT_DTYPE,
}
HHLD_INDEX_COLS = [HHLD]

PERS_DTYPES = {
    HHLD: RECORD_DTYPE,
    PERSON: SHORTUINT_DTYPE,
    AGE: SHORTUINT_DTYPE,
    GENDER: SEX_DTYPE,
    HAS_LICENSE: BOOL_DTYPE,
    'transit_pass': BOOL_DTYPE,
    EMP_STATUS: EMP_OR_STUDENT_STATUS_DTYPE,
    OCCUPATION: OCCUPATION_STATUS_DTYPE,
    'free_parking': BOOL_DTYPE,
    'student_status': EMP_OR_STUDENT_STATUS_DTYPE,
    WORK_ZONE: ZONE_DTYPE,
    SCHOOL_ZONE: ZONE_DTYPE,
    WEIGHT: WEIGHT_DTYPE,
    'telecommuter': SHORTUINT_DTYPE   # XTMF 1.13+ (optional)
}
PERS_INDEX_COLS =[HHLD, PERSON]

TRIP_DTYPES = {
    HHLD: RECORD_DTYPE,
    PERSON: SHORTUINT_DTYPE,
    TRIP: SHORTUINT_DTYPE,
    O_ACTIVITY: ACTIVTY_DTYPE,
    OZONE_COL: ZONE_DTYPE,
    D_ACTIVITY: ACTIVTY_DTYPE,
    DZONE_COL: ZONE_DTYPE,
    WEIGHT: WEIGHT_DTYPE,
    'JointTourRep': SHORTUINT_DTYPE,
    'JointTourRepTripId': SHORTUINT_DTYPE
}
TRIP_INDEX_COLS = [HHLD, PERSON, TRIP]

TRIPMODE_DTYPES = {
    HHLD: RECORD_DTYPE,
    PERSON: SHORTUINT_DTYPE,
    TRIP: SHORTUINT_DTYPE,
    MODE: MODE_DTYPE,
    O_DEPART: TIME_DTYPE,
    D_ARRIVE: TIME_DTYPE,
    WEIGHT: WEIGHT_DTYPE
}
TRIPMODE_INDEX_COLS = [HHLD, PERSON, TRIP, MODE]

TRIPSTN_DTYPES= {
    HHLD: RECORD_DTYPE,
    PERSON: SHORTUINT_DTYPE,
    TRIP: SHORTUINT_DTYPE,
    STATION: ZONE_DTYPE,
    DIRECTION: TRIPDIR_DTYPE,
    WEIGHT: WEIGHT_DTYPE,
    MODE: MODE_DTYPE    # xtmf 1.8+
}
TRIPSTN_INDEX_COLS = [HHLD, PERSON, TRIP, STATION, DIRECTION]

FACPAC_DTYPES = {
    HHLD: RECORD_DTYPE,
    PASS: SHORTUINT_DTYPE,
    PASSTRIP: SHORTUINT_DTYPE,
    'driver_id': SHORTUINT_DTYPE,
    'driver_trip_id': SHORTUINT_DTYPE,
    WEIGHT: WEIGHT_DTYPE
}
FACPAC_INDEX_COLS = [HHLD, PASS, PASSTRIP]
