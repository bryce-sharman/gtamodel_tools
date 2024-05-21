""" Module containing the SyntheticPopulation class.

Reads and summarizes on synthetic population produced by population
synthethis tools intended as inputs to the travel demand model.

"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Type

from tmg_tdm_tools import ModelVersion
import tmg_tdm_tools.common.data as data
import tmg_tdm_tools.common.spatial_aggregator as sa
import tmg_tdm_tools.enums as tmgmpp_enums
import tmg_tdm_tools.enums.synthetic_population as enums_sp
import tmg_tdm_tools.enums.synthetic_population.gtamodelv4_0 as spenum_gtamv4_0
import tmg_tdm_tools.enums.synthetic_population.gtamodelv4_1_2 as spenum_gtamv4_1_2


class SyntheticPopulation():
    """ Class to read, store and summarize model synthetic population data. 
    
    Attributes:
        households: pandas.DataFrame containing synthetic households data
        persons: pandas.DataFrame containing synthetic persons data
    
    
    """
    def  __init__(
            self, 
            model_version: ModelVersion, 
            households_fp: str | Path, 
            persons_fp: str | Path
        ):
        """ Initialize SyntheticPopulation class. 

        Args:
            model_version: Travel demand model version for which this 
                synthetic population input is intended.
            households_fp: Filepath to synthetic households file
            persons_fp: Filepath to synthetic persons file
        """
        self._read_synthetic_households(model_version, households_fp)
        self._read_synthetic_persons(model_version, persons_fp)


    def _read_synthetic_households(
            self, 
            model_version: ModelVersion, 
            households_fp: str | Path
        ) -> None:
        """ Reads synethetic households file, saving to households attribute. 

        Args:
            model_version: Travel demand model version for which this 
                synthetic population input is intended.
            households_fp: Filepath to synthetic households file
        """
        if model_version == ModelVersion.GTAModelv4_0:
            modelversion_enum = spenum_gtamv4_0
        elif model_version == ModelVersion.GTAModelv4_1_2:
            modelversion_enum = spenum_gtamv4_1_2

        df = pd.read_csv(households_fp)
        if modelversion_enum.HOUSEHOLDATTRS_MAPPING is not None:
            df = df.rename(modelversion_enum.HOUSEHOLDATTRS_MAPPING, axis=1)

        # Set the dtypes
        for key, dtype in enums_sp.HOUSEHOLD_DTYPES.items():
            df[key] = df[key].astype(dtype)
        self._households = df.set_index(enums_sp.HHLD_ID_COL) 


    def _read_synthetic_persons(
            self, 
            model_version: ModelVersion, 
            persons_fp: str | Path
        ) -> None:
        """ Reads synethetic persons file, saving to persons attribute. 

        Args:
            model_version: Travel demand model version for which this 
                synthetic population input is intended.
            persons_fp: Filepath to synthetic persons file
        """
        if model_version == ModelVersion.GTAModelv4_0:
            modelversion_enum = spenum_gtamv4_0
        elif model_version == ModelVersion.GTAModelv4_1_2:
            modelversion_enum = spenum_gtamv4_1_2

        df = pd.read_csv(persons_fp)
        if modelversion_enum.PERSONSATTRS_MAPPING is not None:
           df = df.rename(modelversion_enum.PERSONSATTRS_MAPPING, axis=1)

        # Set the dtypes
        for key, dtype in enums_sp.PERSONS_DTYPES.items():
            df[key] = df[key].astype(dtype)
        self._persons = df.set_index(enums_sp.PERSONS_INDEX_COLS)


    def summarize_households(
            self,
            weight_expr: str = enums_sp.HHLD_WEIGHT_COL,
            home_sa: Optional[Type[sa.SpatialAggregator]] = None,
            crosstabs: str | List[str] | None = None,
            crosstab_segments: Dict | List[Dict] | None = None,
            hhld_fltr_expr: Optional[str] = None,
        ) -> pd.Series:
        """Spatially aggregates synthetic households, allowing optional filters.
        
        Args:
            home_sa: Spatial aggregation on home zone. 
                If None, then summaries will be reported at the home zone level.
            weight_expr: Value to be aggregated. This is an expression that 
                will be evaluatated using pandas .eval.
            crosstabs: column or list of columns to be used to used create 
                cross-tabulations tables
            crosstab_segments = dictionary, or list of dictionaries, that define 
                crosstab segmentation
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.

        Returns:
            pandas.DataFrame with the summary data.

        """
        hhlds_df = data.apply_dataframe_filter(self._households, hhld_fltr_expr)
        return sa.summarize_table_with_spatial_aggregation(
            hhlds_df, weight_expr, enums_sp.HHLD_HOMEZONE_COL, home_sa, 
            crosstabs, crosstab_segments
        )


    def summarize_persons(
            self,
            weight_expr: str = enums_sp.PERS_WEIGHT_COL,
            home_sa: Type[sa.SpatialAggregator] | None | False = False,
            work_sa: Type[sa.SpatialAggregator] | None | False = False,
            school_sa: Type[sa.SpatialAggregator] | None | False = False,
            crosstabs: str | List[str] | None = None,
            crosstab_segments: Dict | List[Dict] | None = None,
            hhld_fltr_expr: Optional[str] = None,
            pers_fltr_expr: Optional[str] = None,
        ) -> pd.DataFrame:
        """ Spatially aggregates synthetic persons, allowing optional filters.

        Even though there are only a population and household file and it is 
        possible to perform a single merge on these file, this method uses the 
        same approach as is anticipated for the microsim data. 
        
        This involves performing independent filters of the households and 
        persons file before merging data together, if this is required. The 
        purpose to do this is to save memory from the merged data, which 
        admittedly is not a major problem in this case, but is expected to
        become one for the microsim data.
        
        Args:
            home_sa: Spatial aggregation on home zone. 
                If None, then summaries will be reported at the home zone level.
                If False, then summaries will not be computed on home zone.
            weight_expr: Value to be aggregated. This is an expression that 
                will be evaluatated using pandas .eval.
            work_sa: Spatial aggregation on work zone. 
                If None, then summaries will be reported at the work zone level.
                If False, then summaries will not be computed on work zone.
                Only one of work_sa and school_sa can be other than None.
            school_sa: Spatial aggregation on school zone.  
                If None, then summaries will be reported at the school zone.
                If False, then summaries will not be computed on school zone.
                Only one of work_sa and school_sa can be a value other than None.
            crosstabs: column or list of columns to be used to used create 
                cross-tabulations tables
            crosstab_segments = dictionary, or list of dictionaries, that 
                define crosstab segmentation
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
            pers_fltr_expr: filter expression, will be used by pandas.eval to 
                filter persons data using their attributes. If None then no 
                filter is applied using persons attributes.
                
        Returns:
            pandas.DataFrame with the summary data.
            
        """
        # Any aggregation definition that is not explicitly False 
        # (i.e. None or sa.SpatialAggregator) will be created
        aggr_home = False if home_sa is False else True
        aggr_work = False if work_sa is False else True
        aggr_school = False if school_sa is False else True
        if aggr_home + aggr_work + aggr_school < 1:
            raise ValueError(
                "At least one spatial aggregation must be defined."
            )

        # Check if any of the crosstab columns are household attributes, 
        # need to merge persons with households in this case.
        has_hhld_crosstab_col=False
        if crosstabs:
            for ct in list(crosstabs):
                if ct in enums_sp.HHLDS_ATTRS:
                    has_hhld_crosstab_col=True
                    break

        pers_df = data.apply_dataframe_filter(self._persons, pers_fltr_expr)
        if home_sa or hhld_fltr_expr or has_hhld_crosstab_col:
            # Merge the filtered home and persons tables
            # Dropping the households weight as we won't use that for a persons  
            # summary and name conflicts with persons weight
            hhlds_df = data.apply_dataframe_filter(
                self._households, hhld_fltr_expr)
            hhlds_df = hhlds_df.drop(enums_sp.HHLD_WEIGHT_COL, axis=1)
            pers_df = pers_df.merge(
                hhlds_df, how="inner", on=enums_sp.HHLD_ID_COL)

        return sa.summarize_table_with_spatial_aggregation(
            df=pers_df, 
            values=weight_expr, 
            zones=[enums_sp.HHLD_HOMEZONE_COL, 
                   enums_sp.PERS_WORKZONE_COL, 
                   enums_sp.PERS_SCHOOLZONE_COL
                ],
            spatial_aggregations=[home_sa, work_sa, school_sa], 
            crosstabs=crosstabs, 
            crosstab_segments=crosstab_segments
        )

    @property
    def households(self):
        return self._households
    
    @property
    def persons(self):
        return self._persons
