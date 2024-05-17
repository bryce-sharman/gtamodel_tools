import numpy as np
import pandas as pd

import tmg_tdm_tools.enums as tmgmpp_enums


HHLD_ID_COL = "household_id"
HHLD_HOMEZONE_COL = "home_zone"
HHLD_WEIGHT_COL = "weight"
HHLD_DWELLINGTYPE_COL = "dwelling_type"
HHLD_NUMPERSONS_COL = "persons"
HHLD_NUMVEHICLES_COL = "vehicles"
HHLD_INCOMECLASS_COL = "income_class"

PERS_HHLDID_COL = "household_id"
PERS_PERSID_COL = "person_id"
PERS_AGE_COL = "age"
PERS_SEX_COL = "sex"
PERS_DRVLIC_COL = "licence"
PERS_TRPASS_COL = "transit_pass"
PERS_EMPSTAT_COL = "employment_status"
PERS_OCCUP_COL = "occupation"
PERS_FREEPARKING_COL = "free_parking"
PERS_STDSTAT_COL = "student_status"
PERS_WORKZONE_COL = "employment_zone"
PERS_SCHOOLZONE_COL = "school_zone"
PERS_WEIGHT_COL = "weight"
PERSONS_INDEX_COLS = [PERS_HHLDID_COL, PERS_PERSID_COL]

HOUSEHOLD_DTYPES = {
    HHLD_ID_COL: tmgmpp_enums.ID_ATTR_TYPE,
    HHLD_HOMEZONE_COL: tmgmpp_enums.ZONE_ATTR_TYPE,
    HHLD_WEIGHT_COL: tmgmpp_enums. WEIGHT_ATTR_TYPE,
    HHLD_DWELLINGTYPE_COL: pd.CategoricalDtype(categories=[1, 2, 3, 9], ordered=False),
    HHLD_NUMPERSONS_COL: np.uint8,
    HHLD_NUMVEHICLES_COL: np.uint8,
    HHLD_INCOMECLASS_COL: pd.CategoricalDtype(categories=[1, 2, 3, 4, 5, 6, 7], ordered=False)
}

PERSONS_DTYPES = {
    PERS_HHLDID_COL: tmgmpp_enums. ID_ATTR_TYPE,
    PERS_PERSID_COL: tmgmpp_enums. ID_ATTR_TYPE,
    PERS_AGE_COL: np.uint8,
    PERS_SEX_COL: pd.CategoricalDtype(categories=['F', 'M', '9'], ordered=False),
    PERS_DRVLIC_COL: pd.CategoricalDtype(categories=['Y', 'N', '9'], ordered=False),
    PERS_TRPASS_COL: pd.CategoricalDtype(categories=['C', 'G', 'M','N', 'O', 'P', '9'], ordered=False),
    PERS_EMPSTAT_COL: pd.CategoricalDtype(categories=['O', 'P', 'F', 'J', 'H'], ordered=False),
    PERS_OCCUP_COL: pd.CategoricalDtype(categories=['O', 'S', 'P', 'G', 'M'], ordered=False),
    PERS_FREEPARKING_COL: pd.CategoricalDtype(categories=['N', 'O', 'Y', '9'], ordered=False),
    PERS_STDSTAT_COL: pd.CategoricalDtype(categories=['O', 'S', 'P', '9'], ordered=False),
    PERS_WORKZONE_COL: tmgmpp_enums.ZONE_ATTR_TYPE,
    PERS_SCHOOLZONE_COL: tmgmpp_enums.ZONE_ATTR_TYPE,
    PERS_WEIGHT_COL: tmgmpp_enums.WEIGHT_ATTR_TYPE
}