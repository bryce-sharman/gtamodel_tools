from importlib.resources import files
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from typing import Dict, List, Optional, Tuple, Type

from gtamodel_tools.config import Config
import gtamodel_tools.common.data as data
import gtamodel_tools.common.spatial_aggregator as sa
import gtamodel_tools.enums.microsim as ems
from gtamodel_tools.matrix.matrix import Matrix


class MicroSim():
    """ Class to store and summarize MicroSimulation results.

    Args:
        config: gtamodel_tools.config.Config
            Stored post-processsing configuration.

    """
#region Init and File Reading
    def __init__(self, config: Config) -> None:
        
        # The following attributes are defined directly in the config file
        self.microsim_subdir = config.microsim_subdir
        self.microsim_filepaths = config.microsim_filepaths
        self.time_periods = config.time_periods
        self.zone_range_defs = config.zone_ranges
        self.microsim_tripmode_nsamples = config.microsim_tripmode_nsamples
        self.microsim_rename_columns = config.microsim_rename_columns

        # Test subdirectory holding MicroSim results
        if not config.microsim_subdir.is_dir():
            raise FileExistsError(
                f'Directory not found: {config.microsim_subdir}')
        
        # MicroSim results files, within the microsim directory
        self.microsim_filepaths = {}
        # add full path to microsim results files and test file existence
        for ms_fn, ms_name in config.microsim_filepaths.items():
           self.microsim_filepaths[ms_fn] = self.microsim_subdir / ms_name

    def read_microsim_files(self):
        print('Reading households file')
        self.households = self.read_households()
        print('Reading persons file')
        self.persons = self.read_persons()
        print('Reading trips file')
        self.trips = self.read_trips()
        print('Reading trip modes file')
        self.tripmodes = self.read_tripmodes()
        print('Reading trip stations file')
        self.tripstations = self.read_trip_stations()
        print('Reading facilitate passenger file')
        self.facilitate_passenger = self.read_facilitate_passenger()

    def read_households(self) -> pd.DataFrame:
        """ Read MicroSim households file, saving to the instance. """
        dwellingtype_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.HhldDwellingType])
        standard_dtypes = {
            ems.HhldFields.HHLD_ID.value: ems.MSDtypes.RECORD.value,
            ems.HhldFields.HOME_ZONE.value: ems.MSDtypes.ZONE.value,
            ems.HhldFields.WEIGHT.value: ems.MSDtypes.WEIGHT.value,
            ems.HhldFields.N_PERSONS.value: ems.MSDtypes.SHORTUINT.value,
            ems.HhldFields.DWELLING_TYPE.value: dwellingtype_dtype,
            ems.HhldFields.N_VEHICLES.value: ems.MSDtypes.SHORTUINT.value,
            ems.HhldFields.INCOME_CAT.value: ems.MSDtypes.SHORTUINT.value
        }
        standard_index_cols = [ems.HhldFields.HHLD_ID.value]
        df = self._read_microsim_file(
            'households', standard_dtypes, standard_index_cols)
        return df

    def read_persons(self) -> pd.DataFrame:
        gender_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.PersGender])
        empstatus_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.PersEmpStatus])
        occup_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.PersOccup])
        stdstatus_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.PersStudentStatus])
        standard_dtypes = {
            ems.PersFields.HHLD_ID.value: ems.MSDtypes.RECORD.value,
            ems.PersFields.PERS_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.PersFields.AGE.value: ems.MSDtypes.SHORTUINT.value,
            ems.PersFields.GENDER.value: gender_dtype,
            ems.PersFields.HAS_LICENSE.value: ems.MSDtypes.BOOL.value,
            ems.PersFields.HAS_TRPASS.value: ems.MSDtypes.BOOL.value,
            ems.PersFields.EMP_STATUS.value: empstatus_dtype,
            ems.PersFields.OCCUPATION.value: occup_dtype,
            ems.PersFields.FREE_PARKING.value: ems.MSDtypes.BOOL.value,
            ems.PersFields.STD_STATUS.value: stdstatus_dtype,
            ems.PersFields.WORK_ZONE.value: ems.MSDtypes.ZONE.value,
            ems.PersFields.SCHOOL_ZONE.value: ems.MSDtypes.ZONE.value,
            ems.PersFields.WEIGHT.value: ems.MSDtypes.WEIGHT.value,
            ems.PersFields.TELECOMMUTER: ems.MSDtypes.SHORTUINT.value,
        }
        standard_index_cols = [
            ems.PersFields.HHLD_ID.value, ems.PersFields.PERS_ID.value]
        df = self._read_microsim_file(
            'persons', standard_dtypes, standard_index_cols)
        return df

    def read_trips(self) -> pd.DataFrame:
        activity_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.TripActivity])
        standard_dtypes = {
            ems.TripFields.HHLD_ID.value: ems.MSDtypes.RECORD.value,
            ems.TripFields.PERS_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.TripFields.TRIP_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.TripFields.O_ACTIVITY.value: activity_dtype,
            ems.TripFields.O_ZONE.value: ems.MSDtypes.ZONE.value,
            ems.TripFields.D_ACTIVITY.value: activity_dtype,
            ems.TripFields.D_ZONE.value: ems.MSDtypes.ZONE.value,
            ems.TripFields.WEIGHT.value: ems.MSDtypes.WEIGHT.value,
        }
        standard_index_cols = [
            ems.TripFields.HHLD_ID.value, ems.TripFields.PERS_ID.value, 
            ems.TripFields.TRIP_ID.value
        ]
        df = self._read_microsim_file(
            'trips', standard_dtypes, standard_index_cols)
        return df
    
    def read_tripmodes(self) -> pd.DataFrame:
        mode_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.TripMode])
        standard_dtypes = {
            ems.TripModesFields.HHLD_ID.value: ems.MSDtypes.RECORD.value,
            ems.TripModesFields.PERS_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.TripModesFields.TRIP_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.TripModesFields.TRIPMODE_ID.value: mode_dtype,
            ems.TripModesFields.O_DEPART.value: ems.MSDtypes.TIME.value,
            ems.TripModesFields.D_ARRIVE.value: ems.MSDtypes.TIME.value,
            ems.TripModesFields.WEIGHT.value: ems.MSDtypes.WEIGHT.value,
        }
        standard_index_cols = [
            ems.TripModesFields.HHLD_ID.value, 
            ems.TripModesFields.PERS_ID.value, 
            ems.TripModesFields.TRIP_ID.value,
            ems.TripModesFields.TRIPMODE_ID.value,   
        ]
        df = self._read_microsim_file(
            'trip_modes', standard_dtypes, standard_index_cols)
        return df

    def read_trip_stations(self) -> pd.DataFrame:
        trdir_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.TransitDirection])
        modes_dtype = pd.CategoricalDtype(
                categories=[c.value for c in ems.TripMode])
        standard_dtypes = {
            ems.TripStnsFields.HHLD_ID.value: ems.MSDtypes.RECORD.value,
            ems.TripStnsFields.PERS_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.TripStnsFields.TRIP_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.TripStnsFields.STATION.value: ems.MSDtypes.ZONE.value,
            ems.TripStnsFields.DIRECTION.value: trdir_dtype,
            ems.TripStnsFields.WEIGHT.value: ems.MSDtypes.WEIGHT.value,
            ems.TripStnsFields.TRIPMODE_ID.value: modes_dtype,
        }
        standard_index_cols = [
            ems.TripStnsFields.HHLD_ID.value, 
            ems.TripStnsFields.PERS_ID.value, 
            ems.TripStnsFields.TRIP_ID.value,
            ems.TripStnsFields.STATION.value, 
            ems.TripStnsFields.DIRECTION.value
        ]
        df = self._read_microsim_file(
            'trip_stations', standard_dtypes, standard_index_cols)
        return df

    def read_facilitate_passenger(self) -> pd.DataFrame:
        standard_dtypes = {
            ems.FacPassFields.HHLD_ID.value: ems.MSDtypes.RECORD.value,
            ems.FacPassFields.PASS_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.FacPassFields.PASSTRIP_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.FacPassFields.DRIVER_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.FacPassFields.DRIVERTRIP_ID.value: ems.MSDtypes.SHORTUINT.value,
            ems.FacPassFields.WEIGHT.value: ems.MSDtypes.WEIGHT.value,

        }
        standard_index_cols = [
            ems.FacPassFields.HHLD_ID.value, 
            ems.FacPassFields.PASS_ID.value, 
            ems.FacPassFields.PASSTRIP_ID.value,
        ]
        df = self._read_microsim_file(
            'facilitate_passenger', standard_dtypes, standard_index_cols)
        return df
#endregion

#region read-file helper methods

    def _read_microsim_file(
            self, 
            input_file_key: str, 
            standard_dtypes: dict, 
            standard_index_cols: list,
    ) -> pd.DataFrame:
        """ 
        Read a MicroSim file allowing for name mapping, which can occur
        between different versions of GTAModelv4. 
        """
        dtypes = standard_dtypes.copy()
        index_cols = standard_index_cols.copy()

        # Update dtypes and index cols if specified in config file
        is_mapping_defined = self._test_if_mapping_defined(input_file_key)
        if is_mapping_defined:
            dtypes, index_cols = self._adjust_mapping_and_index_cols(
                input_file_key, dtypes, index_cols)
        filepath = self.microsim_filepaths[input_file_key]
        df = pd.read_csv(filepath, dtype=dtypes)
        # If new names are set in the config file, change to standard names
        if is_mapping_defined:
            inverse_mapping = self._invert_column_name_mapping(input_file_key)
            df = df.rename(inverse_mapping, axis=1)
        return df.set_index(standard_index_cols)

    def _test_if_mapping_defined(self, input_file:str) -> bool:
        """ Test if a mapping is defined for the input file. """
        if isinstance(self.microsim_rename_columns, dict) and \
                input_file in self.microsim_rename_columns:
            return True
        return False

    def _adjust_mapping_and_index_cols(
            self, input_file: str, dtypes: dict, index_cols: list
        ) -> tuple[dict, list]:
        """ Adjust the column mapping and index columns for a given input file. """

        for file_fieldname, std_fieldname in \
                self.microsim_rename_columns[input_file].items():
            if file_fieldname in dtypes:
                dtypes[std_fieldname] = dtypes[file_fieldname]
                del dtypes[file_fieldname]
            if file_fieldname in index_cols:
                index_cols.remove(file_fieldname)
                index_cols.append(std_fieldname)
        return dtypes, index_cols

    def _invert_column_name_mapping(self, input_file):
        # Invert the rename mapping
        new_mapping = {}
        for file_fieldname, std_fieldname in \
                self.microsim_rename_columns[input_file].items():
            new_mapping[std_fieldname] = file_fieldname
        return new_mapping
#endregion


#region Summarize methods
    def summarize_hhld_totals(
            self, 
            home_sa: Type[sa.SpatialAggregator] | None,
            *,
            hhld_fltr_expr: Optional[str] = None
        ) -> pd.DataFrame:
        """ 
        Summarize the total number of households, number of people and 
        average household size. 
        
        Args:
            home_sa: Spatial aggregation on home zone. If None, then will
                output at the zone level.
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
        Returns:
            pandas.DataFrame with the summary data.
        """
        homezone_col = ems.HhldFields.HOME_ZONE.value
        npersons_col = ems.HhldFields.N_PERSONS.value
        hhlds_df = data.apply_dataframe_filter(self.households, hhld_fltr_expr)
        n_hhlds = sa.summarize_table_with_spatial_aggregation(
            hhlds_df, "1", homezone_col, home_sa)
        n_hhlds.columns = ['NHhlds']
        n_persons = sa.summarize_table_with_spatial_aggregation(
            hhlds_df, f'{npersons_col}', homezone_col, home_sa)
        n_persons.columns = ['NPersons']  
        df = pd.concat([n_hhlds, n_persons], axis=1)
        df['AvhHhldSize'] = df['NPersons'] / df['NHhlds']
        return df

    def summarize_hhlds_by_income_cat(
            self, 
            home_sa: Type[sa.SpatialAggregator] | None,
            *,
            hhld_fltr_expr: Optional[str] = None
        ) -> pd.DataFrame:
        """ 
        Summarize the total number of households by income category. 
        
        Args:
            home_sa: Spatial aggregation on home zone. If None, then will
                output at the zone level.
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
        Returns:
            pandas.DataFrame with the summary data.
        """
        homezone_col = ems.HhldFields.HOME_ZONE.value
        incomecat_col = ems.HhldFields.INCOME_CAT.value
        hhlds_df = data.apply_dataframe_filter(self.households, hhld_fltr_expr)
        min_inc_cls = hhlds_df[incomecat_col].min()
        max_inc_cls = hhlds_df[incomecat_col].max()
        ct_segs = sa.create_integer_crosstab_segment_dict(
            min_inc_cls, max_inc_cls, max_inc_cls, 'IncomeCat_', '')
        df = sa.summarize_table_with_spatial_aggregation(
            hhlds_df, "1", homezone_col, home_sa,
            crosstabs=incomecat_col, crosstab_segments=ct_segs
            )
        return pd.DataFrame(df)

    def summarize_hhlds_by_npersons(
            self, 
            home_sa: Type[sa.SpatialAggregator] | None,
            *,
            hhld_fltr_expr: Optional[str] = None,
            combine_above: int=98
        ) -> pd.DataFrame:
        """ 
        Summarize the total number of households by number of persons.
        
        Args:
            home_sa: Spatial aggregation on home zone. If None, then will
                output at the zone level.
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
            combine_above: int
                Group all families with more than this number of persons
                into a single column
        Returns:
            pandas.DataFrame with the summary data.
        """
        homezone_col = ems.HhldFields.HOME_ZONE.value
        npersons_col = ems.HhldFields.N_PERSONS.value
        hhlds_df = data.apply_dataframe_filter(self.households, hhld_fltr_expr)
        max_npersons = hhlds_df[npersons_col].max()
        ct_segs = sa.create_integer_crosstab_segment_dict(
            1, combine_above, max_npersons, 'NPersons_', '')
        df = sa.summarize_table_with_spatial_aggregation(
            hhlds_df, "1", homezone_col, home_sa,
            crosstabs=npersons_col, crosstab_segments=ct_segs
            )
        return pd.DataFrame(df)

    def summarize_hhlds_by_nvehicles(
            self,
            home_sa: type[sa.SpatialAggregator] | None,
            *,
            hhld_fltr_expr: Optional[str] = None,
            combine_above: int=98
        ) -> pd.DataFrame:
        """ 
        Summarize the total number of households by number of vehicles owned. 
        Also include the total number of vehicles.
        
        Args:
            home_sa: Spatial aggregation on home zone. If None, then will
                output at the zone level.
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
            combine_above: int
                Group all families with more than this number of vehicles
                into a single column
        Returns:
            pandas.DataFrame with the summary data.
        """
        homezone_col = ems.HhldFields.HOME_ZONE.value
        nvehs_col = ems.HhldFields.N_VEHICLES.value
        hhlds_df = data.apply_dataframe_filter(self.households, hhld_fltr_expr)
        max_nvehs = hhlds_df[nvehs_col].max()

        ct_segs = sa.create_integer_crosstab_segment_dict(
            0, combine_above, max_nvehs, 'NVehicles_', '')
        hlds_by_nvehs = sa.summarize_table_with_spatial_aggregation(
            hhlds_df, "1", homezone_col, home_sa,
            crosstabs=nvehs_col, crosstab_segments=ct_segs
            )
        total_vhs = sa.summarize_table_with_spatial_aggregation(
            hhlds_df, ems.HhldFields.N_VEHICLES, homezone_col, home_sa)
        df = pd.concat([hlds_by_nvehs, total_vhs], axis=1)

        return pd.DataFrame(df)

    def summarize_households_custom(
            self,
            home_sa: Type[sa.SpatialAggregator] | None,
            weight_expr: str = ems.WEIGHT,
            *,
            crosstabs: str | List[str] | None = None,
            crosstab_segments: Dict | List[Dict] | None = None,
            hhld_fltr_expr: Optional[str] = None,
        ) -> pd.DataFrame | pd.Series:
        """ 
        Create a custom spatially aggregation of synthetic households, allowing 
        optional filters.
        
        Args:
            home_sa: Spatial aggregation on home zone. If None, then will
                output at the zone level.
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
        hhlds_df = data.apply_dataframe_filter(self.households, hhld_fltr_expr)
        return sa.summarize_table_with_spatial_aggregation(
            hhlds_df, weight_expr, ems.HhldFields.HOME_ZONE.value, home_sa, 
            crosstabs, crosstab_segments
        )

    def summarize_person_totals(
            self,
            aggregate_at: str,
            pers_sa: Type[sa.SpatialAggregator] | None,
            *,
            hhld_fltr_expr: Optional[str] = None,
            pers_fltr_expr: Optional[str] = None,
        ) -> pd.DataFrame | pd.Series:
        """ Spatially aggregates number of synthetic persons.

        Args:
            aggregate_at: str
                Aggregation location. Must be one of:
                    'por': place of residence
                    'pow': place of work
                    'pos': place of school
            pers_sa: Spatial aggregation.  
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
            pers_fltr_expr: filter expression, will be used by pandas.eval to 
                filter persons data using their attributes. If None then no 
                filter is applied using persons attributes.
        Returns:
            pandas.DataFrame with the summary data.
        """
        merge_hhlds=False
        if aggregate_at == 'por':
            zone_col = ems.HhldFields.HOME_ZONE.value
            merge_hhlds=True
        elif aggregate_at == 'pow':
            zone_col = ems.PersFields.WORK_ZONE.value
        elif aggregate_at == 'pos':
            zone_col = ems.PersFields.SCHOOL_ZONE.value
        else:
            raise ValueError("aggregate_at must be one of 'por', 'pow', 'pos'")
        if hhld_fltr_expr is not None:
            merge_hhlds=True
            
        pers_df = data.apply_dataframe_filter(self.persons, pers_fltr_expr)
        if merge_hhlds:
            hhlds_df = data.apply_dataframe_filter(
                self.households, hhld_fltr_expr)
            hhlds_df = hhlds_df.drop(ems.WEIGHT, axis=1)
            pers_df = pers_df.merge(hhlds_df, how="inner", on=ems.HHLD_ID)
        pt = sa.summarize_table_with_spatial_aggregation(
            pers_df, '1', zone_col, pers_sa)
        pt.columns=[f'n_persons_{aggregate_at}']
        return pt

    def summarize_persons_by_agecat(
            self,
            aggregate_at: str,
            pers_sa: Type[sa.SpatialAggregator] | None,
            age_categories: str,
            *,
            hhld_fltr_expr: Optional[str] = None,
            pers_fltr_expr: Optional[str] = None,
        ) -> pd.DataFrame | pd.Series:
        """ Spatially aggregates synthetic persons, by age category.

        Args:
            aggregate_at: str
                Aggregation location. Must be one of:
                    'por': place of residence
                    'pow': place of work
                    'pos': place of school
            pers_sa: Spatial aggregation.  
            age_categories: str
                One of
                - 'statcan_5': [0-17, 18-34, 35-44, 45-64, 65+]
                - '5yr_increments': [0-4, 5-9, ..., 95-99, 100+]
                - 'gtamodel': [0-4, 5-9, 10-14, 15-16, 17-19, 20-24, 25-29,
                    30-34, 35-39, 40-44, 45-54, 55-64, 65-79, 80+]
                - 'gtamodel_3': [0-17, 18-64, 65+]
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
            pers_fltr_expr: filter expression, will be used by pandas.eval to 
                filter persons data using their attributes. If None then no 
                filter is applied using persons attributes.
        Returns:
            pandas.DataFrame with the summary data.
        """
        allowable_age_cats = [ac.value for ac in ems.AgeCategories]
        allowable_age_cats.remove(ems.AgeCategories.AGE.value)
        if age_categories not in allowable_age_cats:
            raise ValueError(
                f"age_categories must be one of {allowable_age_cats}")
        
        merge_hhlds=False
        if aggregate_at == 'por':
            zone_col = ems.HhldFields.HOME_ZONE.value
            merge_hhlds=True
        elif aggregate_at == 'pow':
            zone_col = ems.PersFields.WORK_ZONE.value
        elif aggregate_at == 'pos':
            zone_col = ems.PersFields.SCHOOL_ZONE.value
        else:
            raise ValueError("aggregate_at must be one of 'por', 'pow', 'pos'")
        if hhld_fltr_expr is not None:
            merge_hhlds=True
        agecats_df = pd.read_csv(
            files('gtamodel_tools.enums').joinpath('age_categories.csv'),
            index_col='age'
        )

        pers_df = data.apply_dataframe_filter(self.persons, pers_fltr_expr)
        if merge_hhlds:
            hhlds_df = data.apply_dataframe_filter(
                self.households, hhld_fltr_expr)
            hhlds_df = hhlds_df.drop(ems.WEIGHT, axis=1)
            pers_df = pers_df.merge(hhlds_df, how="inner", on=ems.HHLD_ID)
        pers_df['age_cat'] = pers_df[ems.PersFields.AGE.value].map(
            agecats_df[age_categories])

        ct_segs = {}
        for unique in pers_df['age_cat'].unique():
            ct_segs[unique] = f'age_{unique}_{aggregate_at}'
        pt = sa.summarize_table_with_spatial_aggregation(
            pers_df, '1', zone_col, pers_sa, crosstabs='age_cat', crosstab_segments=ct_segs)
        return pt

    def summarize_persons_by_empstatus_and_occup(
            self,
            aggregate_at: str,
            pers_sa: Type[sa.SpatialAggregator] | None,
            *,
            hhld_fltr_expr: Optional[str] = None,
            pers_fltr_expr: Optional[str] = None,
        ) -> pd.DataFrame | pd.Series:
        """ Spatially aggregates synthetic persons, by age category.

        Args:
            aggregate_at: str
                Aggregation location. Must be one of:
                    'por': place of residence
                    'pow': place of work
                    'pos': place of school
            pers_sa: Spatial aggregation.  
            hhld_fltr_expr: filter expression, will be used by pandas.eval to 
                filter household data using their attributes. If None then no 
                filter is applied using household attributes.
            pers_fltr_expr: filter expression, will be used by pandas.eval to 
                filter persons data using their attributes. If None then no 
                filter is applied using persons attributes.
        Returns:
            pandas.DataFrame with the summary data.
        """        
        merge_hhlds=False
        if aggregate_at == 'por':
            zone_col = ems.HhldFields.HOME_ZONE.value
            merge_hhlds=True
        elif aggregate_at == 'pow':
            zone_col = ems.PersFields.WORK_ZONE.value
        elif aggregate_at == 'pos':
            zone_col = ems.PersFields.SCHOOL_ZONE.value
        else:
            raise ValueError("aggregate_at must be one of 'por', 'pow', 'pos'")
        if hhld_fltr_expr is not None:
            merge_hhlds=True

        pers_df = data.apply_dataframe_filter(self.persons, pers_fltr_expr)
        if merge_hhlds:
            hhlds_df = data.apply_dataframe_filter(
                self.households, hhld_fltr_expr)
            hhlds_df = hhlds_df.drop(ems.WEIGHT, axis=1)
            pers_df = pers_df.merge(hhlds_df, how="inner", on=ems.HHLD_ID)
        pers_df['comb_emp_status'] = pers_df[
            'employment_status'].str.cat(pers_df['occupation'], sep='_')

        unique_comb = pers_df['comb_emp_status'].unique()
        ct_segs = {}
        for uc in unique_comb:
            ct_segs[uc] = f'empst_{uc}_{aggregate_at}'
        pt = sa.summarize_table_with_spatial_aggregation(
            pers_df, '1', zone_col, pers_sa, 'comb_emp_status', ct_segs)
        return pt

    def summarize_persons_custom(
            self,
            home_sa: Type[sa.SpatialAggregator] | bool = False,
            work_sa: Type[sa.SpatialAggregator] | bool = False,
            school_sa: Type[sa.SpatialAggregator] | bool = False,
            weight_expr: str = ems.WEIGHT,
            *,
            crosstabs: str | List[str] | None = None,
            crosstab_segments: Dict | List[Dict] | None = None,
            hhld_fltr_expr: Optional[str] = None,
            pers_fltr_expr: Optional[str] = None,
        ) -> pd.DataFrame | pd.Series:
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
                If False, then summaries will not be computed on home zone.
            work_sa: Spatial aggregation on work zone. 
                If False, then summaries will not be computed on work zone.
                Only one of work_sa and school_sa can be other than None.
            school_sa: Spatial aggregation on school zone.  
                If False, then summaries will not be computed on school zone.
                Only one of work_sa and school_sa can be a value other than None.
            weight_expr: Value to be aggregated. This is an expression that 
                will be evaluatated using pandas .eval.
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
        hhld_fields = [c.name for c in ems.HhldFields]
        if crosstabs:
            for ct in list(crosstabs):
                if ct in hhld_fields:
                    has_hhld_crosstab_col=True
                    break

        pers_df = data.apply_dataframe_filter(self.persons, pers_fltr_expr)
        if home_sa or home_sa==None or hhld_fltr_expr or has_hhld_crosstab_col:
            # Merge the filtered home and persons tables
            # Dropping the households weight as we won't use that for a persons  
            # summary and name conflicts with persons weight
            hhlds_df = data.apply_dataframe_filter(
                self.households, hhld_fltr_expr)
            hhlds_df = hhlds_df.drop(ems.WEIGHT, axis=1)
            pers_df = pers_df.merge(
                hhlds_df, how="inner", on=ems.HHLD_ID)
        return sa.summarize_table_with_spatial_aggregation(
            df=pers_df, 
            values=weight_expr, 
            geom_id=[ems.HhldFields.HOME_ZONE.value, 
                     ems.PersFields.WORK_ZONE.value, 
                     ems.PersFields.SCHOOL_ZONE.value],
            spatial_aggregations=[home_sa, work_sa, school_sa], 
            crosstabs=crosstabs, 
            crosstab_segments=crosstab_segments
        )

    def calculate_trip_tlfd(
            self,
            matrix: Matrix,
            time_period: str | None=None,
            bins=10,
            *,
            households_filter_expr: str | None=None,
            persons_filter_expr: str | None=None,
            trips_filter_expr: str | None=None,
            tripmodes_filter_expr: str | None=None
            ) -> Tuple[NDArray[np.uint64], NDArray[np.float64]]:
        """ Spatially aggregates trips by mode, allowing optional filters. 
    
            Args:
            time_period: str or None:
                Optional filter for time period. If defined (is not None)
                then must be one of ['AM', 'MD', 'PM', 'EE', 'LE']
            matrix: Matrix
                Skim matrix used to compute distances
            bins: Histogram bins,
                Histogram bins, passed into numpy.histogram
                Default is 10.
            households_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            persons_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            trips_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            tripmodes_filter_expr: str or None
                Optional filter expression on trip_modes table. If defined
                this is applies attribute filter using pandas.eval. Note that
                the 'time_period' argument is the preferred way of 
                identifying trips by default GTAModel time periods.
    
            Returns:
                ntrips: numpy.ndarray.uint64
                    Number of trips in each bin. See numpy.histogram for more
                    details.
                bin_edges: numpy.ndarray.float64
                    Bin edges for the histogram. See numpy.histogram for more
                    details. Note that bin_edges will contain one more element 
                    than ntrips.

        """
        final_weight_col = 'FINALWEIGHT'
        if time_period is not None:
            if time_period not in self.time_periods:
                raise AttributeError(
                    "Invalid time period. If defined, must be one of: "
                    f"{list(self.time_periods.keys())}")
            tripmodes_filter_expr = self._add_timeperiod_to_tripmodes_filter(
                time_period, tripmodes_filter_expr)
        trips = data.apply_dataframe_filter(
            self.trips.reset_index(), trips_filter_expr)
        if tripmodes_filter_expr:
            suffixes = '_tm', '_t'
            tripmodes = data.apply_dataframe_filter(
                self.tripmodes.reset_index(), tripmodes_filter_expr)
            trips_with_modes = tripmodes.reset_index().merge(
                trips, 
                how='inner',
                on=[ems.HHLD_ID, ems.PERS_ID, ems.TRIP_ID],
                suffixes=suffixes
            )
            trips_with_modes[final_weight_col] = \
                trips_with_modes[ems.WEIGHT + suffixes[0]] \
                * trips_with_modes[ems.WEIGHT + suffixes[1]]
            tripweights = trips_with_modes.groupby(
                [ems.HHLD_ID, ems.PERS_ID, ems.TRIP_ID]
            )[[final_weight_col]].sum().divide(
                self.microsim_tripmode_nsamples)
            trips = trips.merge(
                tripweights, 
                left_on=[ems.HHLD_ID, ems.PERS_ID, ems.TRIP_ID], 
                right_index=True
            )
            trips[ems.WEIGHT] = trips[final_weight_col]
            trips = trips.drop(final_weight_col, axis=1)

        # If a households or persons filter is applied, filter table and merge  
        # into tripmodes table.
        if isinstance(households_filter_expr, str):
            households_df = data.apply_dataframe_filter(
                self.households, households_filter_expr)
            fltr = trips[ems.HHLD_ID].isin(households_df.index)
            trips = trips.loc[fltr]
        if isinstance(persons_filter_expr, str):
            persons_df = data.apply_dataframe_filter(
                self.persons, persons_filter_expr).reset_index()
            fltr = (
                trips[ems.HHLD_ID].isin(persons_df[ems.HHLD_ID])) & (
                trips[ems.PERS_ID].isin(persons_df[ems.PERS_ID]))
            trips = trips.loc[fltr]
        # Merge in matrix skim and calculate histogram
        trips = trips.merge(
            matrix.tall, 
            left_on=[ems.TripFields.O_ZONE.value, ems.TripFields.D_ZONE.value],
            right_index=True
        )
        ntrips, bin_edges = np.histogram(trips[matrix.name], bins=bins)
        return ntrips, bin_edges

    def summarize_trips_by_mode(
            self,
            origin_sa: type[sa.SpatialAggregator],
            destination_sa: type[sa.SpatialAggregator],
            time_period: str | None=None,
            households_filter_expr: str | None=None,
            persons_filter_expr: str | None=None,
            trips_filter_expr: str | None=None,
            tripmodes_filter_expr: str | None=None
            ) -> pd.DataFrame:
        """ Spatially aggregates trips by mode, allowing optional filters. 
    
            Args:
            origin_sa: subclass of 
                    gtamodel_tools.common.spatial_aggregator.SpatialAggregator
                Spatial aggregation for trip origins
            destination_sa: subclass of 
                    gtamodel_tools.common.spatial_aggregator.SpatialAggregator
                Spatial aggregation for trip destinations
            time_period: str or None:
                Optional filter for time period. If defined (is not None)
                then must be one of ['AM', 'MD', 'PM', 'EE', 'LE']
            households_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            persons_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            trips_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            tripmodes_filter_expr: str or None
                Optional filter expression on trip_modes table. If defined
                this is applies attribute filter using pandas.eval. Note that
                the 'time_period' argument is the preferred way of 
                identifying trips by default GTAModel time periods.
    
            Notes:
                In order to save memory, the MicroSim class does not merge   
                all data together into a single DataTable. This method applies 
                independent filters of the households, persons and trips 
                tables. 

        """
        if time_period is not None:
            if time_period not in self.time_periods:
                raise AttributeError(
                    "Invalid time period. If defined, must be one of: "
                    f"{list(self.time_periods.keys())}")
            tripmodes_filter_expr = self._add_timeperiod_to_tripmodes_filter(
                time_period, tripmodes_filter_expr)

        # We always have to merge trips and tripmodes as we need the trip
        # origins and destinations from the trips table, and the departure
        # time, which is from the tripmodes table.
        suffixes = '_tm', '_t'
        trips = data.apply_dataframe_filter(
            self.trips.reset_index(), trips_filter_expr)
        tripmodes = data.apply_dataframe_filter(
            self.tripmodes.reset_index(), tripmodes_filter_expr)
        trips_with_modes = tripmodes.reset_index().merge(
            trips, 
            how='inner',
            on=[ems.HHLD_ID, ems.PERS_ID, ems.TRIP_ID],
            suffixes=suffixes
        )

        # If a households or persons filter is applied, filter table and merge  
        # into tripmodes table.
        if isinstance(households_filter_expr, str):
            households_df = data.apply_dataframe_filter(
                self.households, households_filter_expr)
            fltr = trips_with_modes[ems.HHLD_ID].isin(households_df.index)
            trips_with_modes = trips_with_modes.loc[fltr]

        if isinstance(persons_filter_expr, str):
            persons_df = data.apply_dataframe_filter(
                self.persons, persons_filter_expr).reset_index()
            fltr = (
                trips_with_modes[ems.HHLD_ID].isin(persons_df[ems.HHLD_ID])) & (
                trips_with_modes[ems.PERS_ID].isin(persons_df[ems.PERS_ID]))
            trips_with_modes = trips_with_modes.loc[fltr]

        # Calculate the total weight, and produce summary
        final_weight_col = 'FINALWEIGHT'
        trips_with_modes[final_weight_col] = \
            trips_with_modes[ems.WEIGHT + suffixes[0]] \
            * trips_with_modes[ems.WEIGHT + suffixes[1]]

        ozone_col = ems.TripFields.O_ZONE.value
        dzone_col = ems.TripFields.D_ZONE.value
        df = sa.summarize_table_with_spatial_aggregation(
            df=trips_with_modes, 
            values=final_weight_col, 
            geom_id=[ozone_col, dzone_col],
            spatial_aggregations=[origin_sa, destination_sa], 
            crosstabs=ems.TRIPMODE_ID
        )
        df = df / self.microsim_tripmode_nsamples
        if origin_sa is not None:
            origin_name = str(origin_sa.name) + '_o'
        else:
            origin_name = ems.TripFields.O_ZONE.value
        if destination_sa is not None:
            destination_name = str(destination_sa.name) + '_d' 
        else:
            destination_name = ems.TripFields.D_ZONE.value
        df.index.names = [origin_name, destination_name]
        return df
    
    def calculate_trip_departure_time_profiles(
            self,
            time_interval: int,
            households_filter_expr: Optional[str]=None,
            persons_filter_expr: Optional[str]=None,
            trips_filter_expr: Optional[str]=None,
            tripmodes_filter_expr: Optional[str]=None
            ) -> pd.DataFrame:
        """ Spatially aggregates trips by mode, allowing optional filters. 

            Args:
            time_interval: int
                length of time interval in minutes. 
            households_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            persons_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            trips_filter_expr: str or None
                Optional filter expression on households table. If defined
                this is applies attribute filter using pandas.eval.
            tripmodes_filter_expr: str or None
                Optional filter expression on trip_modes table. If defined
                this is applies attribute filter using pandas.eval. Note that
                the 'time_period' argument is the preferred way of 
                identifying trips by default GTAModel time periods.

        """
        # Always need to merge trips into trip modes in order to calculate
        # the final trip weight.
        suffixes = '_tm', '_t'
        deptime_col = ems.TripModesFields.O_DEPART.value
        trips = data.apply_dataframe_filter(
            self.trips.reset_index(), trips_filter_expr)
        tripmodes = data.apply_dataframe_filter(
            self.tripmodes.reset_index(), tripmodes_filter_expr)
        tripmodes = tripmodes.merge(
            trips[[ems.HHLD_ID, ems.PERS_ID, ems.TRIP_ID, ems.WEIGHT]], 
            how='inner',
            on=[ems.HHLD_ID, ems.PERS_ID, ems.TRIP_ID],
            suffixes=suffixes
        )
        if isinstance(households_filter_expr, str):
            households_df = data.apply_dataframe_filter(
                self.households, households_filter_expr)
            fltr = tripmodes[ems.HHLD_ID].isin(households_df.index)
            tripmodes = tripmodes.loc[fltr]
        if isinstance(persons_filter_expr, str):
            persons_df = data.apply_dataframe_filter(
                self.persons, persons_filter_expr).reset_index()
            fltr = (tripmodes[ems.HHLD_ID].isin(persons_df[ems.HHLD_ID])) & (
                    tripmodes[ems.PERS_ID].isin(persons_df[ems.PERS_ID]))
            tripmodes = tripmodes.loc[fltr]

        # Check for trips occurring on either the previous or next day, and
        # move them to the current day.
        nmin_per_day = float(24 * 60)
        fltr_prevday = tripmodes[deptime_col] < 0
        tripmodes.loc[fltr_prevday, deptime_col] = tripmodes.loc[
            fltr_prevday, deptime_col] + nmin_per_day
        fltr_nextday = tripmodes[deptime_col] >= nmin_per_day
        tripmodes.loc[fltr_nextday, deptime_col] = \
            tripmodes.loc[fltr_nextday, deptime_col] - nmin_per_day

        # Calculate the total weight, and produce summary

        final_weight_col = 'FINALWEIGHT'
        tripmodes[final_weight_col] = \
            tripmodes[ems.WEIGHT + suffixes[0]] \
            * tripmodes[ems.WEIGHT + suffixes[1]]  
        tripmodes['DEP_INTERVAL'] = tripmodes[
            deptime_col].floordiv(time_interval).astype(np.uint32)
        trips_by_interval = tripmodes.groupby('DEP_INTERVAL')[
            'FINALWEIGHT'].sum() / self.microsim_tripmode_nsamples
        time_intvl_labels = _create_timeinterval_index(time_interval)
        trips_by_interval.index =  time_intvl_labels         
            
        return trips_by_interval

    def _add_timeperiod_to_tripmodes_filter(
            self, time_period: str, tripmodes_filter_expr: str | None) -> str:
        """ 
        Either create new or modify existing tripmodes filter to filter trips
        by time period.
        """
        start_time = self.time_periods[time_period]['start_time']
        end_time = self.time_periods[time_period]['end_time']
        # remember: start time is inclusive, end time is exclusive
        deptime_col = ems.TripModesFields.O_DEPART.value

        period_fltr_expr = \
            f"{deptime_col} >= {start_time} and {deptime_col} < {end_time}"
        if not isinstance(tripmodes_filter_expr, str):
            return period_fltr_expr
        else:
            return f'({tripmodes_filter_expr}) and ({period_fltr_expr})'

#endregion

def _convert_to_hour_min(t):
    """ Convert time that is input as minutes after midnight to hh:mm. """
    hours = t // 60
    minutes = t - 60 * hours
    return f'{hours:02d}:{minutes:02d}'

def _create_timeinterval_index(time_interval):
    """ Create time interval labels (e.g. 06:20-06:40) for each time interval. """
    nmin_per_day = 24 * 60
    ti = []
    for i in range(nmin_per_day // time_interval):
        lower = _convert_to_hour_min(i * time_interval)
        upper = _convert_to_hour_min((i + 1) * time_interval)
        time = f'{lower}-{upper}'
        ti.append(time)
    return pd.Index(ti)

