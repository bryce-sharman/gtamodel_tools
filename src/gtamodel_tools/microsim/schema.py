"""
Module for panderas schemas. 

These have not been included so far to the high runtimes.

"""
from __future__ import annotations



import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.typing.pandas import Category, Index, Series

import gtamodel_tools.enums.microsim as ems

MAX_NPERSONS = 98
MAX_NVEHICLES = 98
MAX_INCOME_CAT = 7
MAX_AGE = 99
MAX_ZONE = 9999

dwellingtype_dtype = pd.CategoricalDtype(
categories=[c.value for c in ems.HhldDwellingType])
gender_dtype = pd.CategoricalDtype(
        categories=[c.value for c in ems.PersGender])
empstatus_dtype = pd.CategoricalDtype(
        categories=[c.value for c in ems.PersEmpStatus])
occup_dtype = pd.CategoricalDtype(
        categories=[c.value for c in ems.PersOccup])
stdstatus_dtype = pd.CategoricalDtype(
        categories=[c.value for c in ems.PersStudentStatus])


HHLD_SCHEMA = pa.DataFrameSchema({
        ems.HhldFields.HOME_ZONE.value: pa.Column(
            dtype=ems.MSDtypes.ZONE.value,
            checks=[pa.Check.ge(1), pa.Check.le(MAX_ZONE)], 
            description="The zone of residence"
        ),
        ems.HhldFields.WEIGHT.value: pa.Column(
            dtype=ems.MSDtypes.WEIGHT.value,
            checks=[pa.Check.ge(0)],
            description="The household's expansion factor to scale " \
                        "the agent to the global population"
        ),
        ems.HhldFields.N_PERSONS.value: pa.Column(
            dtype=ems.MSDtypes.SHORTUINT.value,
            checks=[pa.Check.ge(1), pa.Check.le(MAX_NPERSONS)],
            description=\
                "The number of people living within the household"
        ),
        ems.HhldFields.DWELLING_TYPE.value: pa.Column(
            dtype=dwellingtype_dtype,
            description=\
                "The dwelling/structure type the household lives in."
        ),
        ems.HhldFields.N_VEHICLES.value: pa.Column(
            dtype=ems.MSDtypes.SHORTUINT.value,
            checks=[pa.Check.ge(0), pa.Check.le(MAX_NVEHICLES)],
            description="The number of vehicles assigned by the " \
                        "auto ownership model."
        ),
        ems.HhldFields.INCOME_CAT.value: pa.Column(
            dtype=ems.MSDtypes.SHORTUINT.value,
            checks=[pa.Check.ge(1), pa.Check.le(MAX_INCOME_CAT)],
            description="The income class according to TTS2016 that " \
                        "the household belongs to."
        )
    },
    index= pa.Index(
        dtype=ems.MSDtypes.RECORD.value,
        checks=[pa.Check.ge(1)],
        unique=True,
        name = ems.HhldFields.HHLD_ID.value,
        description='The unique identifier for the household'
    )
)

PERSONS_SCHEMA = pa.DataFrameSchema({
            ems.PersFields.AGE.value: pa.Column(
                dtype=ems.MSDtypes.SHORTUINT.value,
                checks=[pa.Check.ge(0), pa.Check.lt(MAX_AGE)], 
                description= \
                    "The person's age (in single years). Max of 98. "
                    "99 is unknown."
            ),
            ems.PersFields.GENDER.value: pa.Column(
                dtype=gender_dtype,
                description="The person's gender"
            ),
            ems.PersFields.HAS_LICENSE.value: pa.Column(
                dtype=ems.MSDtypes.BOOL.value,
                description="A flag to indicate if the person holds a " \
                            "driver's license"
            ),
            ems.PersFields.HAS_TRPASS.value: pa.Column(
                dtype=ems.MSDtypes.BOOL.value,
                description="A flag to indicate if the person holds a " \
                            "transit pass. (Unused)"
            ),
            ems.PersFields.EMP_STATUS.value: pa.Column(
                dtype=gender_dtype,
                description="The person's work status"
            ),
            ems.PersFields.OCCUPATION.value: pa.Column(
                dtype=gender_dtype,
                description="The person's occupation category"
            ),
            ems.PersFields.FREE_PARKING.value: pa.Column(
                dtype=ems.MSDtypes.BOOL.value,
                description="A flag to indicate if the person has " \
                            "access to free parking at work (unused)."
            ),
            ems.PersFields.STD_STATUS.value: pa.Column(
                dtype=stdstatus_dtype,
                description="The person's student status"
            ),
            ems.PersFields.WORK_ZONE.value: pa.Column(
                dtype=ems.MSDtypes.ZONE.value,
                checks=[pa.Check.ge(0), pa.Check.le(MAX_ZONE)], 
                description="Work zone. If 0 they have not been assigned "
                            "a work zone"
            ),
            ems.PersFields.SCHOOL_ZONE.value: pa.Column(
                dtype=ems.MSDtypes.ZONE.value,
                checks=[pa.Check.ge(0), pa.Check.le(MAX_ZONE)], 
                description="School zone. If 0 they have not been assigned "
                            "a school zone"
            ),
            ems.PersFields.WEIGHT.value: pa.Column(
                dtype=ems.MSDtypes.WEIGHT.value,
                checks=[pa.Check.ge(0)],
                description="The person's expansion factor to scale " \
                            "the agent to the global population"
            ),
            ems.PersFields.TELECOMMUTER.value: pa.Column(
                dtype=ems.MSDtypes.BOOL.value,
                coerce=True,
                required=False,
                description="Flag to indicate if the person decided to " \
                            "telecommute on the day of simulation. " \
                            "(XTMF 1.13+)"
            ),
        },
        index= pa.MultiIndex([
                pa.Index(
                    dtype=ems.MSDtypes.RECORD.value,
                    checks=[pa.Check.ge(1)],
                    unique=True,
                    name=ems.PersFields.HHLD_ID.value,
                    description='The unique identifier for the household'
                ),
                pa.Index(
                    dtype=ems.MSDtypes.SHORTUINT.value,
                    checks=[pa.Check.ge(1), pa.Check.le(MAX_NPERSONS)],
                    name=ems.PersFields.PERS_ID.value,
                    description='The unique identifier for the household'
                ),
            ]
        )
    )
