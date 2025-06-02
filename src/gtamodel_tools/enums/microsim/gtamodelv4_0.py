# MicroSim Enums for GTAModel v4.0

import numpy as np
import pandas as pd


TIME_PERIOD_DEFINITIONS = {
    'ON': {
        'start': 0.0,     # 00:00
        'end': 360.0      # 06:00
    },
    'AM': {
        'start': 360.0,   # 06:00
        'end': 540.0      # 09:00
    },
    'MD': {
        'start': 540.0,   # 09:00
        'end': 900.0      # 15:00
    },
    'PM': {
        'start': 900.0,   # 15:00
        'end':  1140.0    # 19:00
    },
    'EV': {
        'start': 1140.0,  # 19:00,
        'end': 1440.0     # 24:00,
    }
}

N_TRIPMODE_SAMPLES = 100


ZONE_DTYPE = np.dtype('u2')       # 16-bit, range between 0 and 65,635
WEIGHT_DTYPE = np.dtype('f4')     # 32-bit
SHORTUINT_DTYPE = np.dtype('u1')  # 8-bit, range between 0 and 255
RECORD_DTYPE = np.dtype('u4')     # 32-bit, range between 0 and ~4.3 billion
BOOL_DTYPE = np.dtype('?') 
TIME_DTYPE = np.dtype('f2')       # It's minutes after midnight, doesn't need
                                  # to be very precise

SEX_DTYPE = pd.CategoricalDtype(
    categories=['M', 'F'],
    ordered=False
)
EMP_OR_STUDENT_STATUS_DTYPE = pd.CategoricalDtype(
    categories=['F', 'O', 'P'],
    ordered=False
)
OCCUPATION_STATUS_DTYPE = pd.CategoricalDtype(
    categories=['P', 'G', 'O', 'S', 'M'],
    ordered=False
)

ACTIVTY_DTYPE = pd.CategoricalDtype(
    categories=[
        'Home', 'PrimaryWork', 'School', 'WorkBasedBusiness',
        'IndividualOther', 'JointOther', 'SecondaryWork', 'JointMarket',
        'Market'
    ],
    ordered=False
)

MODE_DTYPE = pd.CategoricalDtype(
    categories=[
        'Walk', 'WAT', 'Auto', 'Carpool', 'Schoolbus', 'RideShare', 'Passenger',
        'Bicycle', 'DAT'
    ],
    ordered=False
)

TRIPDIR_DTYPE = pd.CategoricalDtype(
    categories=['auto2transit' or 'transit2auto'],
    ordered=False
)


MICROSIM_DIR = 'MicroSim Results'

FILENAMES = {
    'households': 'Households.csv.gz',
    'persons': 'Persons.csv.gz',
    'trips': 'Trips.csv.gz',
    'trip_modes': 'Trip_Modes.csv.gz',
    'trip_stations': 'Trip_Stations.csv.gz',
    'facilitate_passenger': 'Facilitate_Passenger.csv.gz'
}

HHLD_COLS = {
    'id': 'household_id',
    'home_zone': 'home_zone',
    'weight': 'weight',
    'n_persons': 'persons',
    'dtype': 'dwelling_type',
    'n_vehicles': 'vehicles',
    'income_class': 'income_class',
}
HHLD_DTYPES = {
    HHLD_COLS['id']: RECORD_DTYPE,
    HHLD_COLS['home_zone']: ZONE_DTYPE,   
    HHLD_COLS['weight']: WEIGHT_DTYPE,
    HHLD_COLS['n_persons']: SHORTUINT_DTYPE,
    HHLD_COLS['dtype']: SHORTUINT_DTYPE,
    HHLD_COLS['n_vehicles']: SHORTUINT_DTYPE,
    HHLD_COLS['income_class']: SHORTUINT_DTYPE,
}
HHLD_INDEX_COLS = HHLD_COLS['id']

PERS_COLS = {
    'hhld_id': 'household_id',
    'pers_id': 'person_id',
    'age': 'age',
    'sex': 'sex',
    'has_drvs_lic': 'license',
    'has_trns_pass': 'transit_pass',
    'emp_status': 'employment_status',
    'occup': 'occupation',
    'has_free_parking': 'free_parking',
    'std_status': 'student_status',
    'work_zone': 'work_zone',
    'school_zone': 'school_zone',
    'weight': 'weight',

}
PERS_DTYPES = {
    PERS_COLS['hhld_id']: RECORD_DTYPE,
    PERS_COLS['pers_id']: SHORTUINT_DTYPE,
    PERS_COLS['age']: SHORTUINT_DTYPE,
    PERS_COLS['sex']: SEX_DTYPE,
    PERS_COLS['has_drvs_lic']: BOOL_DTYPE,
    PERS_COLS['has_trns_pass']: BOOL_DTYPE,
    PERS_COLS['emp_status']: EMP_OR_STUDENT_STATUS_DTYPE,
    PERS_COLS['occup']: OCCUPATION_STATUS_DTYPE,
    PERS_COLS['has_free_parking']: BOOL_DTYPE,
    PERS_COLS['std_status']: EMP_OR_STUDENT_STATUS_DTYPE,
    PERS_COLS['work_zone']: ZONE_DTYPE,
    PERS_COLS['school_zone']: ZONE_DTYPE,
    PERS_COLS['weight']: WEIGHT_DTYPE
}
PERS_INDEX_COLS =[PERS_COLS['hhld_id'], PERS_COLS['pers_id']]

TRIP_COLS = {
    'hhld_id': 'household_id',
    'pers_id': 'person_id',
    'trip_id': 'trip_id',
    'oact': 'o_act',
    'ozone': 'o_zone',
    'dact': 'd_act',
    'dzone': 'd_zone',
    'weight': 'weight'
}
TRIP_DTYPES = {
    TRIP_COLS['hhld_id']: RECORD_DTYPE,
    TRIP_COLS['pers_id']: SHORTUINT_DTYPE,
    TRIP_COLS['trip_id']: SHORTUINT_DTYPE,
    TRIP_COLS['oact']: ACTIVTY_DTYPE,
    TRIP_COLS['ozone']: ZONE_DTYPE,
    TRIP_COLS['dact']: ACTIVTY_DTYPE,
    TRIP_COLS['dzone']: ZONE_DTYPE,
    TRIP_COLS['weight']: WEIGHT_DTYPE
}
TRIP_INDEX_COLS = [
    TRIP_COLS['hhld_id'], TRIP_COLS['pers_id'], TRIP_COLS['trip_id']]

TRIPMODE_COLS = {
    'hhld_id': 'household_id',
    'pers_id': 'person_id',
    'trip_id': 'trip_id',
    'mode': 'mode',
    'dep_time': 'o_depart',
    'arr_time': 'd_arrive',
    'weight': 'weight'
    
}
TRIPMODE_DTYPES = {
    TRIPMODE_COLS['hhld_id']: RECORD_DTYPE,
    TRIPMODE_COLS['pers_id']: SHORTUINT_DTYPE,
    TRIPMODE_COLS['trip_id']: SHORTUINT_DTYPE,
    TRIPMODE_COLS['mode']: MODE_DTYPE,
    TRIPMODE_COLS['dep_time']: TIME_DTYPE,
    TRIPMODE_COLS['arr_time']: TIME_DTYPE,
    TRIPMODE_COLS['weight']: WEIGHT_DTYPE
}
TRIPMODE_INDEX_COLS = [TRIPMODE_COLS['hhld_id'], TRIPMODE_COLS['pers_id'], 
                       TRIPMODE_COLS['trip_id'], TRIPMODE_COLS['mode']]

TRIPSTN_COLS = {
    'hhld_id': 'household_id',
    'pers_id': 'person_id',
    'trip_id': 'trip_id',
    'station': 'station',
    'direction': 'direction',
    'weight': 'weight',
    'mode': 'mode'
}
TRIPSTN_DTYPES= {
    TRIPSTN_COLS['hhld_id']: RECORD_DTYPE,
    TRIPSTN_COLS['pers_id']: SHORTUINT_DTYPE,
    TRIPSTN_COLS['trip_id']: SHORTUINT_DTYPE,
    TRIPSTN_COLS['station']: ZONE_DTYPE,
    TRIPSTN_COLS['direction']: TRIPDIR_DTYPE,
    TRIPSTN_COLS['weight']: WEIGHT_DTYPE,
    TRIPSTN_COLS['mode']: MODE_DTYPE
}
TRIPSTN_INDEX_COLS = [
    TRIPSTN_COLS['hhld_id'], TRIPSTN_COLS['pers_id'], TRIPSTN_COLS['trip_id'], 
    TRIPSTN_COLS['station'], TRIPSTN_COLS['direction']
]

FACPAC_COLS = {
    'hhld_id': 'household_id',
    'pass_id': 'passenger_id',
    'pass_trip_id': 'passenger_trip_id',
    'driver_id': 'driver_id',
    'driver_trip_id': 'driver_trip_id',
    'weight': 'weight'
}
FACPAC_DTYPES = {
    FACPAC_COLS['hhld_id']: RECORD_DTYPE,
    FACPAC_COLS['pass_id']: SHORTUINT_DTYPE,
    FACPAC_COLS['pass_trip_id']: SHORTUINT_DTYPE,
    FACPAC_COLS['driver_id']: SHORTUINT_DTYPE,
    FACPAC_COLS['driver_trip_id']: SHORTUINT_DTYPE,
    FACPAC_COLS['weight']: WEIGHT_DTYPE
}
FACPAC_INDEX_COLS = [
    FACPAC_COLS['hhld_id'], FACPAC_COLS['pass_id'], FACPAC_COLS['pass_trip_id']]
