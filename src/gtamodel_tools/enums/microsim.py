# MicroSim Enums for GTAModel v4.0

from enum import Enum, IntEnum, StrEnum
import numpy as np
import pandas as pd


HHLD_ID = 'household_id'
PERS_ID = 'person_id'   
TRIP_ID = 'trip_id'
TRIPMODE_ID = 'mode'
WEIGHT = 'weight'
STATION = 'station'
DIRECTION = 'direction'
PASS_ID = 'passenger_id'
PASSTRIP_ID = 'passenger_trip_id'
class MSDtypes(Enum):
    ZONE = np.dtype('u2')       # 16-bit, range between 0 and 65,635
    WEIGHT = np.dtype('f4')     # 32-bit
    SHORTUINT = np.dtype('u1')  # 8-bit, range between 0 and 255
    RECORD = np.dtype('u4')     # 32-bit, range between 0 and ~4.3 billion
    BOOL = np.dtype('?') 
    TIME = np.dtype('f2')       # It's minutes after midnight, doesn't need
                                # to be very precise
#region Table definitions
class HhldFields(StrEnum):
    HHLD_ID = HHLD_ID
    HOME_ZONE = 'home_zone'
    WEIGHT = WEIGHT
    N_PERSONS = 'persons'
    DWELLING_TYPE = 'dwelling_type'
    N_VEHICLES = 'vehicles'
    INCOME_CAT = 'income_class'
class PersFields(StrEnum):
    HHLD_ID = HHLD_ID
    PERS_ID = PERS_ID
    AGE = 'age'
    GENDER = 'sex'
    HAS_LICENSE = 'license'
    HAS_TRPASS = 'transit_pass'
    EMP_STATUS = 'employment_status'
    OCCUPATION = 'occupation'
    FREE_PARKING = 'free_parking'
    STD_STATUS = 'student_status'
    WORK_ZONE = 'work_zone'
    SCHOOL_ZONE = 'school_zone' 
    WEIGHT = WEIGHT
    TELECOMMUTER = 'telecommuter'

class TripFields(StrEnum):
    HHLD_ID = HHLD_ID
    PERS_ID = PERS_ID
    TRIP_ID = TRIP_ID
    O_ACTIVITY = 'o_act'
    O_ZONE = 'o_zone'
    D_ACTIVITY = 'd_act'
    D_ZONE = 'd_zone'
    WEIGHT = WEIGHT

class TripModesFields(StrEnum):
    HHLD_ID = HHLD_ID
    PERS_ID = PERS_ID
    TRIP_ID = TRIP_ID
    TRIPMODE_ID = TRIPMODE_ID
    O_DEPART = 'o_depart'
    D_ARRIVE = 'd_arrive'
    WEIGHT = WEIGHT
class TripStnsFields(StrEnum):
    HHLD_ID = HHLD_ID
    PERS_ID = PERS_ID
    TRIP_ID = TRIP_ID
    STATION = STATION
    DIRECTION = DIRECTION
    WEIGHT = WEIGHT
    TRIPMODE_ID = TRIPMODE_ID

class FacPassFields(StrEnum):
    HHLD_ID = HHLD_ID
    PASS_ID = PASS_ID
    PASSTRIP_ID = PASSTRIP_ID
    DRIVER_ID = 'driver_id'
    DRIVERTRIP_ID = 'driver_trip_id'
    WEIGHT = WEIGHT
#endregion
# region Field Categories
class HhldDwellingType(IntEnum):
    GROUND = 1
    APARTMENT = 2
    TOWNHOUSE = 3
    UNDEFINED = 9
class PersGender(StrEnum):
    MALE = 'M'
    FEMALE = 'F'

class PersEmpStatus(StrEnum):
    UPW_FT = 'F'
    UPW_PT = 'P'
    WAH_FT = 'H'
    WAH_PT = 'J'
    NOTEMPLOYED = 'O'

class PersOccup(StrEnum):
    GENERAL = 'G'
    MANUFACTURING = 'M'
    PROFESSIONAL = 'P'
    SERVICE = 'S'
    NOT_EMPLOYED = 'O'    

class PersStudentStatus(StrEnum):
    FT = 'S'
    PT = 'P'
    NOTSTUDENT = 'O'
class TripActivity(StrEnum):
    PRIMARY_WORK = "PrimaryWork"  # The main work activity episode going to the assigned work location for the individual
    SECONDARY_WORK = "SecondaryWork"  # A work activity episode not going to the primary work location
    WORK_BASED_BUSINESS = "WorkBasedBusiness"  # A work location not going to the main work location, such as a business meeting
    SCHOOL = "School"  # A school activity episode
    MARKET = "Market"  # A market activity episode
    JOINT_MARKET = "JointMarket"  # A market activity episode that is part of a joint tour
    INDIVIDUAL_OTHER = "IndividualOther"  # An activity episode that is not work, school, or market
    JOINT_OTHER = "JointOther"  # An activity episode that is not work, school, or market and is part of a joint tour
    HOME = "Home"  # The home activity episode
    RETURN_FROM_WORK = "ReturnFromWork"  # A purposeful return home activity episode from work, such as lunch

class TripMode(StrEnum):
    AUTO = "Auto"
    RIDESHARE = "RideShare"
    VEHICLE_FOR_HIRE = "VFH"
    PASSENGER = "Passenger"
    CARPOOL = "Carpool"
    WALK_ACCESS_TRANSIT = "WAT"
    DRIVE_ACCESS_TRANSIT = "DAT"
    PASSENGER_ACCESS_TRANSIT = "PAT"
    PASSENGER_EGRESS_TRANSIT = "PET"
    WALK = "Walk"
    BIKE = "Bicycle"
    SCHOOLBUS = "Schoolbus"

class TransitDirection(StrEnum):
    AUTO_TO_TRANSIT = "auto2transit"
    TRANSIT_TO_AUTO = "transit2auto"

class AgeCategories(StrEnum):
    AGE  = 'age'
    STATCAN_5 = 'statcan_5'
    FIVE_YR_INCREMENTS = '5yr_increments'
    GTA_MODEL = 'gtamodel'
    GTA_MODEL_3 = 'gtamodel_3'
