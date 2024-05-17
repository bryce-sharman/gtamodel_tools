""" Microsim data structure for GTAModelv4.0. 

# GTAv4.0 used an older microsim naming convention, here's the map to the current nameing convention
"""
import tmg_tdm_tools.enums.synthetic_population as enums_sp

# Mapping values from input columns used in the model version to internal keys, which reflect current naming convention
HOUSEHOLDATTRS_MAPPING = {
    "HouseholdID": enums_sp.HHLD_ID_COL,
    "Zone": enums_sp.HHLD_HOMEZONE_COL,
    "ExpansionFactor": enums_sp.HHLD_WEIGHT_COL,
    "DwellingType": enums_sp.HHLD_DWELLINGTYPE_COL,
    "NumberOfPersons": enums_sp.HHLD_NUMPERSONS_COL,
    "NumberOfVehicles": enums_sp.HHLD_NUMVEHICLES_COL,
    "Income": enums_sp.HHLD_INCOMECLASS_COL
}

PERSONSATTRS_MAPPING = {
    "HouseholdID": enums_sp.PERS_HHLDID_COL,
    "PersonNumber": enums_sp.PERS_PERSID_COL,
    "Age": enums_sp.PERS_AGE_COL,
    "Sex": enums_sp.PERS_SEX_COL,
    "License": enums_sp.PERS_DRVLIC_COL,
    "TransitPass": enums_sp.PERS_TRPASS_COL,
    "EmploymentStatus": enums_sp.PERS_EMPSTAT_COL,
    "Occupation": enums_sp.PERS_OCCUP_COL,
    "FreeParking": enums_sp.PERS_FREEPARKING_COL,
    "StudentStatus": enums_sp.PERS_STDSTAT_COL,
    "EmploymentZone": enums_sp.PERS_WORKZONE_COL,
    "SchoolZone": enums_sp.PERS_SCHOOLZONE_COL,
    "ExpansionFactor": enums_sp.PERS_WEIGHT_COL
}


