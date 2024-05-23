import numpy as np
import pandas as pd

import tmg_tdm_tools.enums as enums


# Min and max ages for each segmentation range, of the form (min, max] (min is exclusive, max is inclusive)
IPU_AGE_SEGMENTS = {
    "(-Inf,4]": 'child',
    "(4,9]": 'child',
    "(9,14]": 'child',
    "(14,17]": 'child',
    "(17,19]": 'adult',
    "(19,24]": 'adult',
    "(24,29]": 'adult',
    "(29,34]": 'adult',
    "(34,39]": 'adult',
    "(39,44]": 'adult',
    "(44,54]": 'adult',
    "(54,64]": 'adult',
    "(64,79]": 'senior',
    "(79, Inf]": 'senior'
}

#region input file definition
# Input directory
FN_ZS = 'ZoneSystem.csv'
FN_PDMAP = 'PD_map.csv'
DN_SEEDDATA = 'SeedData'
FN_PDGROUPS = 'PDGroups.csv'
FN_SEEDS = 'SeedPopulation.csv'
FN_SCEN_DISTANCES = 'Distances.csv'
FN_SCEN_HHLD_CNTRLS = 'HouseholdControls.csv'
FN_SCEN_PERS_CNTRLS = 'PersonControls.csv'
FN_SCEN_STATIONS = 'Stations.csv'
FN_SCEN_TIMES = 'TravelTimes.csv'
FN_SCEN_ZNATTRS = 'Zone Attributes.csv'
#endregion

#region Inputs Directory
# PD Map fields
PDMAP_FROM = 'PD2_FROM'
PDMAP_TO = 'PD2_TO'
PDMAP_DTYPES = {
    PDMAP_FROM: np.float32,   # accepts float PDs
    PDMAP_TO: np.float32,   # accepts float PDs
}

# Zone System file fields
ZS_ZONEID = 'TAZ_NO'
ZS_X = 'x'
ZS_Y = 'y'
ZS_AREA = 'area'
ZS_WATERFACTOR = 'water-factor'
ZS_PD = 'PD2'
ZS_DTYPES = {
    ZS_ZONEID: enums.ZONE_ATTR_TYPE,
    ZS_X: np.float32,
    ZS_Y: np.float32,
    ZS_AREA: np.float32,
    ZS_WATERFACTOR: np.float32,
    ZS_PD: np.float32   # accepts float PDs   
}

# Seed file fields
SD_HHLD_ID = "HouseholdNumber"
SD_PERS_ID = "PersonNumber"
SD_HHLD_SIZE = "HouseholdSize"
SD_HHLD_HHLDTYPE = "HouseholdType"
SD_HHLD_HOMEPD = "PD"
SD_HHLD_DWELLINGTYPE = "DwellingType"
SD_HHLD_EXPFACTOR = "ExpansionFactor"
SD_PERS_SEX = "Sex"
SD_PERS_AGE = "Age"
SD_DTYPES = {
    SD_HHLD_ID: enums.ID_ATTR_TYPE,
    SD_PERS_ID: enums.ID_ATTR_TYPE,
    SD_HHLD_SIZE: np.uint8,
    SD_HHLD_HHLDTYPE: np.uint8,
    SD_HHLD_HOMEPD: np.float32,   # accepts float PDs
    SD_HHLD_DWELLINGTYPE: pd.CategoricalDtype(categories=[1, 2], ordered=False),
    SD_HHLD_EXPFACTOR: np.float32, 
    SD_PERS_SEX: pd.CategoricalDtype(categories=['F', 'M', '9'], ordered=False),
    SD_PERS_AGE: np.uint8,
}

# Planning districts groups file fields
PDGR_INDEX = "PD"
PDGR_PDGROUP = "PDGroup"
PDGR_DTYPES = {
    PDGR_INDEX: np.float32,
    PDGR_PDGROUP: np.uint8,   # I think that keeping this an integer is okay, at least for now.
}
#endregion

#region Scenario Directory
HHLDCNTRLS_PD = 'PD'
HHLDCNTRLS_DWELLINGTYPE = 'DwellingType'
HHLDCNTRLS_HHLDTYPE = 'HouseholdType'
HHLDCNTRLS_FREQ = 'Frequency'
HHLDCNTRLS_DTYPES = {
    HHLDCNTRLS_PD: np.float32,   # accepts float PDs  
    HHLDCNTRLS_DWELLINGTYPE: pd.CategoricalDtype(categories=[1, 2], ordered=False),
    HHLDCNTRLS_HHLDTYPE: np.uint8,
    HHLDCNTRLS_FREQ: np.float32
}
PERSCNTRLS_PD = 'PD'
PERSCNTRLS_DWELLINGTYPE = 'DwellingType'
PERSCNTRLS_SEX = 'Sex'
PERSCENTRS_AGEGROUP = 'AgeGroup'
PERSCNTRLS_FREQ = 'Frequency'
PERSCNTRLS_DTYPES = {
    PERSCNTRLS_PD: np.float32,   # accepts float PDs  
    PERSCNTRLS_DWELLINGTYPE: pd.CategoricalDtype(categories=[1, 2], ordered=False),
    PERSCNTRLS_SEX: pd.CategoricalDtype(categories=['F', 'M', '9'], ordered=False),
    PERSCENTRS_AGEGROUP: pd.CategoricalDtype(categories=IPU_AGE_SEGMENTS.keys(), ordered=False),
    PERSCNTRLS_FREQ: np.float32
}

# Zone attributes file fields
ZA_ZONEID = 'taz'
ZA_POP = 'population'
# ZA_HHLDS = 'total_hh'       # does not appear to be used, confirm this!
ZA_EMP_NAICS_11 = 'naics_11'
ZA_EMP_NAICS_21 = 'naics_21'
ZA_EMP_NAICS_22 = 'naics_22'
ZA_EMP_NAICS_23 = 'naics_23'
ZA_EMP_NAICS_31_33 = 'naics_31_33'
ZA_EMP_NAICS_41 = 'naics_41'
ZA_EMP_NAICS_44_45 = 'naics_44_45'
ZA_EMP_NAICS_48_49 = 'naics_48_49'
ZA_EMP_NAICS_51 = 'naics_51'
ZA_EMP_NAICS_52 = 'naics_52'
ZA_EMP_NAICS_53 = 'naics_53'
ZA_EMP_NAICS_54 = 'naics_54'
ZA_EMP_NAICS_55 = 'naics_55'
ZA_EMP_NAICS_56 = 'naics_56'
ZA_EMP_NAICS_61 = 'naics_61'
ZA_EMP_NAICS_62 = 'naics_62'
ZA_EMP_NAICS_71 = 'naics_71'
ZA_EMP_NAICS_72 = 'naics_72'
ZA_EMP_NAICS_81 = 'naics_81'
ZA_EMP_NAICS_91 = 'naics_91'
ZA_PRK_COST = 'parking_cost'
ZA_EMP_COLS = [ZA_EMP_NAICS_11, ZA_EMP_NAICS_21, ZA_EMP_NAICS_22, ZA_EMP_NAICS_23, ZA_EMP_NAICS_31_33, ZA_EMP_NAICS_41,
               ZA_EMP_NAICS_44_45, ZA_EMP_NAICS_48_49, ZA_EMP_NAICS_51, ZA_EMP_NAICS_52, ZA_EMP_NAICS_53, ZA_EMP_NAICS_54,
               ZA_EMP_NAICS_55, ZA_EMP_NAICS_56, ZA_EMP_NAICS_61, ZA_EMP_NAICS_62, ZA_EMP_NAICS_71, ZA_EMP_NAICS_72,
               ZA_EMP_NAICS_81, ZA_EMP_NAICS_91]
ZA_DTYPES = {
    ZA_ZONEID: enums.ZONE_ATTR_TYPE,
    ZA_POP: np.float32,
    ZA_EMP_NAICS_11: np.float32,
    ZA_EMP_NAICS_21: np.float32,
    ZA_EMP_NAICS_22: np.float32,
    ZA_EMP_NAICS_23: np.float32,
    ZA_EMP_NAICS_31_33: np.float32,
    ZA_EMP_NAICS_41: np.float32,
    ZA_EMP_NAICS_44_45: np.float32,
    ZA_EMP_NAICS_48_49: np.float32,
    ZA_EMP_NAICS_51: np.float32,
    ZA_EMP_NAICS_52: np.float32,
    ZA_EMP_NAICS_53: np.float32,
    ZA_EMP_NAICS_54: np.float32,
    ZA_EMP_NAICS_55: np.float32,
    ZA_EMP_NAICS_56: np.float32,
    ZA_EMP_NAICS_61: np.float32,
    ZA_EMP_NAICS_62: np.float32,
    ZA_EMP_NAICS_71: np.float32,
    ZA_EMP_NAICS_72: np.float32,
    ZA_EMP_NAICS_81: np.float32,
    ZA_EMP_NAICS_91: np.float32,
    ZA_PRK_COST: np.float32,
}

#endregion


