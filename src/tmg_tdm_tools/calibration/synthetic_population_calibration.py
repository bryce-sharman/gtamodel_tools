""" Analysis modules to assist validation of synthetic population data. 

The functions in this module are meant to be the primary access point by which 
to summarize synthetic populations. 

"""
import pandas as pd
from typing import Dict, Optional, Type, Union

import tmg_tdm_tools.synthetic_population.synthetic_population as sp
import tmg_tdm_tools.common.spatial_aggregator as sa
import tmg_tdm_tools.enums.synthetic_population as enums_sp


#region Households
def summarize_total_households(
        synth_pop: sp.SyntheticPopulation, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes total number of households by region.

    Args:
        synth_pop: Synthetic population
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    df = synth_pop.summarize_households(home_sa=home_sa)
    df.name = "total_households"
    return df


def summarize_hhld_hhldsize_distn(
        synth_pop: sp.SyntheticPopulation, 
        hhldsize_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of households by number of people, by region, using user-defined mapping. 
    
    Args:
        synth_pop: Synthetic population
        hhldsize_mapping: Categorization definition for the number of people in the household
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    df =  synth_pop.summarize_households(
        home_sa=home_sa, 
        crosstabs=enums_sp.HHLD_NUMPERSONS_COL, 
        crosstab_segments=hhldsize_mapping
        )
    df.name = "households_by_hhldsize"
    return df

def summarize_hhld_numvehicles_distn(
        synth_pop: sp.SyntheticPopulation, 
        nvehs_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of vehicles owned by household, by region, using user-defined mapping. 
    
    Args:
        synth_pop: Synthetic population
        nvehs_mapping: Categorization definition for the number of  vehicles owned by the household
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    df = synth_pop.summarize_households(
        home_sa=home_sa, 
        crosstabs=enums_sp.HHLD_NUMVEHICLES_COL, 
        crosstab_segments=nvehs_mapping
        )
    df.name = "households_by_nvehs"
    return df

def summarize_total_vehicles(
        synth_pop: sp.SyntheticPopulation, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes total number of vehicles owned by households living in a region
    
    Args:
        synth_pop: Synthetic population
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    df = synth_pop.summarize_households(
        home_sa=home_sa, 
        weight_expr = f"{enums_sp.HHLD_WEIGHT_COL} * {enums_sp.HHLD_NUMVEHICLES_COL}"
        )
    df.name = "total_vehicles"
    return df

def summarize_hhld_dwellingtype_distn(
        synth_pop: sp.SyntheticPopulation, 
        dwellingtype_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None
        ) -> pd.DataFrame:
    """ Summarizes household dwelling type, by region, using user-defined mapping. 
    
    Args:
        synth_pop: Synthetic population
        dwellingtype_mapping: Categorization definition for the household dwelling type
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    df = synth_pop.summarize_households(
        home_sa=home_sa, 
        crosstabs=enums_sp.HHLD_DWELLINGTYPE_COL, 
        crosstab_segments=dwellingtype_mapping
    )
    df.name = "households_by_dwellingtype"
    return df

def summarize_hhld_crosstab_hhldsize_dwellingtype(
        synth_pop: sp.SyntheticPopulation, 
        hhldsize_mapping: Union[Dict, pd.Series, None] = None, 
        dwellingtype_mapping: Union[Dict, pd.Series, None] = None,
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of households by both household size (number of people) and dwelling type. 
    
    Args:
        synth_pop: Synthetic population
        hhldsize_mapping: Categorization definition for the number of people in the household
        dwellingtype_mapping: Categorization definition for the household dwelling type
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_households(
        home_sa=home_sa, crosstabs=[enums_sp.HHLD_NUMPERSONS_COL, enums_sp.HHLD_DWELLINGTYPE_COL], 
        crosstab_segments=[hhldsize_mapping, dwellingtype_mapping])

def summarize_hhld_crosstab_dwellingtype_nvehs(
        synth_pop: sp.SyntheticPopulation, 
        dwellingtype_mapping: Union[Dict, pd.Series, None] = None, 
        nvehs_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of households by both household size (number of people) and dwelling type. 
    
    Args:
        synth_pop: Synthetic population
        dwellingtype_mapping: Categorization definition for the household dwelling type
        nvehs_mapping: Categorization definition for the number of  vehicles owned by the household
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_households(
        home_sa=home_sa, crosstabs=[enums_sp.HHLD_DWELLINGTYPE_COL, enums_sp.HHLD_NUMVEHICLES_COL], 
        crosstab_segments=[dwellingtype_mapping, nvehs_mapping])


def summarize_hhld_crosstab_hhldsize_nvehs(
        synth_pop: sp.SyntheticPopulation, 
        hhldsize_mapping: Union[Dict, pd.Series, None] = None, 
        nvehs_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of households by both household size (number of people) and dwelling type. 
    
    Args:
        synth_pop: Synthetic population
        hhldsize_mapping: Categorization definition for the number of people in the household
        nvehs_mapping: Categorization definition for the number of  vehicles owned by the household
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_households(
        home_sa=home_sa, crosstabs=[enums_sp.HHLD_DWELLINGTYPE_COL, enums_sp.HHLD_NUMVEHICLES_COL], 
        crosstab_segments=[hhldsize_mapping, nvehs_mapping])

#endregion

#region persons
def summarize_total_persons(
        synth_pop: sp.SyntheticPopulation, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by their place of residence (POR).

    Args:
        synth_pop: Synthetic population
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(home_sa=home_sa)



def summarize_pers_gender_distn(
        synth_pop: sp.SyntheticPopulation, 
        gender_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by gender by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        gender_mapping: Categorization definition for gender.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_SEX_COL, crosstab_segments=gender_mapping)

def summarize_pers_age_distn(
        synth_pop: sp.SyntheticPopulation, 
        age_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by age by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        age_mapping: Categorization definition for age.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_AGE_COL, crosstab_segments=age_mapping)

def summarize_pers_drvlic_distn(
        synth_pop: sp.SyntheticPopulation, 
        drvlic_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by driver's licence by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        drvlic_mapping: Categorization definition for driver's licence.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_DRVLIC_COL, crosstab_segments=drvlic_mapping)


def summarize_pers_trnspass_distn(
        synth_pop: sp.SyntheticPopulation, 
        trnspass_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by transit pass by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        trnspass_mapping: Categorization definition for transit pass.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_TRPASS_COL, crosstab_segments=trnspass_mapping)


def summarize_pers_empstat_distn(
        synth_pop: sp.SyntheticPopulation, 
        empstat_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by employment status by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        empstat_mapping: Categorization definition for employment status.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_TRPASS_COL, crosstab_segments=empstat_mapping)


def summarize_pers_occup_distn(
        synth_pop: sp.SyntheticPopulation, 
        occup_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by occupation by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        occup_mapping: Categorization definition for occupation.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_OCCUP_COL, crosstab_segments=occup_mapping)


def summarize_pers_stdstat_distn(
        synth_pop: sp.SyntheticPopulation, 
        stdstat_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes number of persons by student status by place of residence (POR). 
    
    Args:
        synth_pop: Synthetic population
        stdstat_mapping: Categorization definition for employment status.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, crosstabs=enums_sp.PERS_STDSTAT_COL, crosstab_segments=stdstat_mapping)


def summarize_pers_crosstab_gender_drvlic(
        synth_pop: sp.SyntheticPopulation, 
        gender_mapping: Union[Dict, pd.Series, None] = None, 
        drvlic_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of persons by both gender and driver's licence. 
    
    Args:
        synth_pop: Synthetic population
        gender_mapping: Categorization definition for gender.
        drvlic_mapping: Categorization definition for driver's licence.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame
    
    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, 
        crosstabs=[enums_sp.PERS_SEX_COL, enums_sp.PERS_DRVLIC_COL], 
        crosstab_segments=[gender_mapping, drvlic_mapping]
    )

def summarize_pers_crosstab_age_drvlic(
        synth_pop: sp.SyntheticPopulation, 
        age_mapping: Union[Dict, pd.Series, None] = None, 
        drvlic_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of persons by both gender and driver's licence. 
    
    Args:
        synth_pop: Synthetic population
        age_mapping: Categorization definition for age.
        drvlic_mapping: Categorization definition for driver's licence.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame
    
    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, 
        crosstabs=[enums_sp.PERS_AGE_COL, enums_sp.PERS_DRVLIC_COL], 
        crosstab_segments=[age_mapping, drvlic_mapping]
    )

def summarize_pers_crosstab_empstat_occup(
        synth_pop: sp.SyntheticPopulation, 
        empstat_mapping: Union[Dict, pd.Series, None] = None, 
        occup_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of persons by both gender and driver's licence. 
    
    Args:
        synth_pop: Synthetic population
        empstat_mapping: Categorization definition for employment status.
        occup_mapping: Categorization definition for occupation.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame
    
    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, 
        crosstabs=[enums_sp.PERS_EMPSTAT_COL, enums_sp.PERS_OCCUP_COL], 
        crosstab_segments=[empstat_mapping, occup_mapping]
    )

def summarize_pers_crosstab_age_empstat(
        synth_pop: sp.SyntheticPopulation, 
        age_mapping: Union[Dict, pd.Series, None] = None, 
        empstat_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of persons by both gender and driver's licence. 
    
    Args:
        synth_pop: Synthetic population
        age_mapping: Categorization definition for age.
        empstat_mapping: Categorization definition for employment status.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame
    
    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, 
        crosstabs=[enums_sp.PERS_AGE_COL, enums_sp.PERS_EMPSTAT_COL], 
        crosstab_segments=[age_mapping, empstat_mapping]
    )

def summarize_pers_crosstab_age_occup(
        synth_pop: sp.SyntheticPopulation, 
        age_mapping: Union[Dict, pd.Series, None] = None, 
        occup_mapping: Union[Dict, pd.Series, None] = None, 
        home_sa: Optional[Type[sa.SpatialAggregator]]=None,
        ) -> pd.DataFrame:
    """ Summarizes cross-tabulation of persons by both gender and driver's licence. 
    
    Args:
        synth_pop: Synthetic population
        age_mapping: Categorization definition for age.
        occup_mapping: Categorization definition for occupation.
        home_sa: Spatial aggregation for home zone. If None then is output at the TAZ level.

    Returns:
        pd.DataFrame: Summary pandas DataFrame
    
    """
    return synth_pop.summarize_persons(
        home_sa=home_sa, 
        crosstabs=[enums_sp.PERS_AGE_COL, enums_sp.PERS_OCCUP_COL], 
        crosstab_segments=[age_mapping, occup_mapping]
    )

#endregion
