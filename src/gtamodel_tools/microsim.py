import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Type

from gtamodel_tools.config import Config
import gtamodel_tools.common.data as data
import gtamodel_tools.common.spatial_aggregator as sa
import gtamodel_tools.enums.microsim as me

class MicroSim():
    """ Class to store and summarize MicroSimulation results.

    Args:
        config: gtamodel_tools.config.Config
            Stored post-processsing configuration.

    """

    def __init__(self, config: Config) -> None:
        
        # The following attributes are defined directly in the config file
        self.microsim_subdir = config.microsim_subdir
        self.microsim_filepaths = config.microsim_filepaths
        self.time_periods = config.time_periods
        self.zone_range_defs = config.zone_ranges
        self.microsim_tripmode_nsamples = config.microsim_tripmode_nsamples
        self.microsim_rename_columns = config.microsim_rename_columns

        self.households = None
        self.persons = None
        self.trips = None
        self.tripmodes = None
        self.tripstations = None
        self.facilitate_passenger = None

    def read_microsim_results(self) -> None:
        """ Read all MicroSim results files, saving to the instance. """
        self.read_microsim_hhlds()
        self.read_microsim_persons()
        self.read_microsim_trips()
        self.read_microsim_tripmodes()
        self.read_microsim_tripstations()
        self.read_facilitate_passenger()

    def read_microsim_hhlds(self) -> None:
        """ Read MicroSim households file, saving to the instance. """
        self.households = self._read_microsim_file(
            'households', me.HHLD_DTYPES, me.HHLD_INDEX_COLS)
        
    def read_microsim_persons(self) -> None:
        """ Read MicroSim persons file, saving to the instance. """
        self.persons = self._read_microsim_file(
            'persons', me.PERS_DTYPES, me.PERS_INDEX_COLS)

    def read_microsim_trips(self) -> None:
        """ Read MicroSim trips file, saving to the instance. """
        self.trips = self._read_microsim_file(
            'trips', me.TRIP_DTYPES, me.TRIP_INDEX_COLS)

    def read_microsim_tripmodes(self) -> None:
        """ Read MicroSim trip-modes file, saving to the instance. """
        self.tripmodes = self._read_microsim_file(
            'trip_modes', me.TRIPMODE_DTYPES, me.TRIPMODE_INDEX_COLS)
        
    def read_microsim_tripstations(self) -> None:
        """ Read MicroSim trip-stations file, saving to the instance. """
        self.tripstations = self._read_microsim_file(
            'trip_stations', me.TRIPSTN_DTYPES, me.TRIPSTN_INDEX_COLS)

    def read_facilitate_passenger(self) -> None:
        """ Read MicroSim facilitate passenger file, saving to the instance. """
        self.facilitate_passenger = self._read_microsim_file(
            'facilitate_passenger', me.FACPAC_DTYPES, me.FACPAC_INDEX_COLS)

#region read-file helper methods

    def _read_microsim_file(
            self, 
            input_file: str, 
            standard_dtypes: dict, 
            standard_index_cols: list,
    ) -> pd.DataFrame:
        """ Read a MicroSim file, returning a DataFrame. """
        dtypes = standard_dtypes.copy()
        index_cols = standard_index_cols.copy()

        # Update dtypes and index cols if specified in config file
        is_mapping_defined = self._test_if_mapping_defined(input_file)
        if is_mapping_defined:
            dtypes, index_cols = self._adjust_mapping_and_index_cols(
                input_file, dtypes, index_cols)
        df = pd.read_csv(
            self.microsim_filepaths[input_file], dtype=dtypes)
        # If new names are set in the config file, change to standard names
        if is_mapping_defined:
            inverse_mapping = self._invert_column_name_mapping(input_file)
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
    def summarize_households_custom(
            self,
            home_sa: Type[sa.SpatialAggregator],
            weight_expr: str = me.WEIGHT,
            crosstabs: str | List[str] | None = None,
            crosstab_segments: Dict | List[Dict] | None = None,
            hhld_fltr_expr: Optional[str] = None,
        ) -> pd.Series:
        """ 
        Create a custom spatially aggregation of synthetic households, allowing 
        optional filters.
        
        Args:
            home_sa: Spatial aggregation on home zone. 
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
            hhlds_df, weight_expr, me.HOME_ZONE, home_sa, 
            crosstabs, crosstab_segments
        )

    def summarize_persons(
            self,
            home_sa: Type[sa.SpatialAggregator] | False = False,
            work_sa: Type[sa.SpatialAggregator] | False = False,
            school_sa: Type[sa.SpatialAggregator] | False = False,
            weight_expr: str = me.WEIGHT,
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
        if crosstabs:
            for ct in list(crosstabs):
                if ct in me.HHLD_DTYPES.keys():
                    has_hhld_crosstab_col=True
                    break

        pers_df = data.apply_dataframe_filter(self.persons, pers_fltr_expr)
        if home_sa or home_sa==None or hhld_fltr_expr or has_hhld_crosstab_col:
            # Merge the filtered home and persons tables
            # Dropping the households weight as we won't use that for a persons  
            # summary and name conflicts with persons weight
            hhlds_df = data.apply_dataframe_filter(
                self.households, hhld_fltr_expr)
            hhlds_df = hhlds_df.drop(me.WEIGHT, axis=1)
            pers_df = pers_df.merge(
                hhlds_df, how="inner", on=me.HHLD)
        return sa.summarize_table_with_spatial_aggregation(
            df=pers_df, 
            values=weight_expr, 
            geom_id=[me.HOME_ZONE, me.WORK_ZONE, me.SCHOOL_ZONE],
            spatial_aggregations=[home_sa, work_sa, school_sa], 
            crosstabs=crosstabs, 
            crosstab_segments=crosstab_segments
        )


    def summarize_trips_by_mode(
            self,
            origin_sa: Type[sa.SpatialAggregator],
            destination_sa: Type[sa.SpatialAggregator],
            time_period: Optional[str]=None,
            households_filter_expr: Optional[str]=None,
            persons_filter_expr: Optional[str]=None,
            trips_filter_expr: Optional[str]=None,
            tripmodes_filter_expr: Optional[str]=None
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
        suffixes = ['_tm', '_t']
        trips = data.apply_dataframe_filter(
            self.trips.reset_index(), trips_filter_expr)
        tripmodes = data.apply_dataframe_filter(
            self.tripmodes.reset_index(), tripmodes_filter_expr)
        trips_with_modes = tripmodes.reset_index().merge(
            trips, 
            how='inner',
            left_on=[me.HHLD, me.PERSON, me.TRIP],
            right_on=[me.HHLD, me.PERSON, me.TRIP],
            suffixes=suffixes
        )

        # If a households or persons filter is applied, filter table and merge  
        # into tripmodes table.
        if isinstance(households_filter_expr, str):
            households_df = data.apply_dataframe_filter(
                self.households, households_filter_expr)
            fltr = trips_with_modes[me.HHLD].isin(households_df.index)
            trips_with_modes = trips_with_modes.loc[fltr]
        if isinstance(persons_filter_expr, str):
            persons_df = data.apply_dataframe_filter(
                self.persons, persons_filter_expr).reset_index()
            fltr = (trips_with_modes[me.HHLD].isin(persons_df[me.HHLD])) & (
                    trips_with_modes[me.PERSON].isin(persons_df[me.PERSON]))
            trips_with_modes = trips_with_modes.loc[fltr]

        # Calculate the total weight, and produce summary
        final_weight_col = 'FINALWEIGHT'
        trips_with_modes[final_weight_col] = \
            trips_with_modes[me.WEIGHT + suffixes[0]] \
            * trips_with_modes[me.WEIGHT + suffixes[1]]
        s = sa.summarize_table_with_spatial_aggregation(
            df=trips_with_modes, 
            values=final_weight_col, 
            geom_id=[me.OZONE_COL, me.DZONE_COL],
            spatial_aggregations=[origin_sa, destination_sa], 
            crosstabs=me.MODE
        )[final_weight_col] / self.microsim_tripmode_nsamples
        
        if origin_sa is not None:
            origin_name = origin_sa.name + '_o'
        else:
            origin_name = me.OZONE_COL
        if destination_sa is not None:
            destination_name = destination_sa.name + '_d' 
        else:
            destination_name = me.DZONE_COL
        s.index.names = [origin_name, destination_name, me.MODE]
        return s
    
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
        suffixes = ['_tm', '_t']
        trips = data.apply_dataframe_filter(
            self.trips.reset_index(), trips_filter_expr)
        tripmodes = data.apply_dataframe_filter(
            self.tripmodes.reset_index(), tripmodes_filter_expr)
        tripmodes = tripmodes.merge(
            trips[[me.HHLD, me.PERSON, me.TRIP, me.WEIGHT]], 
            how='inner',
            left_on=[me.HHLD, me.PERSON, me.TRIP],
            right_on=[me.HHLD, me.PERSON, me.TRIP],
            suffixes=suffixes
        )
        if isinstance(households_filter_expr, str):
            households_df = data.apply_dataframe_filter(
                self.households, households_filter_expr)
            fltr = tripmodes[me.HHLD].isin(households_df.index)
            tripmodes = tripmodes.loc[fltr]
        if isinstance(persons_filter_expr, str):
            persons_df = data.apply_dataframe_filter(
                self.persons, persons_filter_expr).reset_index()
            fltr = (tripmodes[me.HHLD].isin(persons_df[me.HHLD])) & (
                    tripmodes[me.PERSON].isin(persons_df[me.PERSON]))
            tripmodes = tripmodes.loc[fltr]

        # Check for trips occurring on either the previous or next day, and
        # move them to the current day.
        nmin_per_day = float(24 * 60)
        fltr_prevday = tripmodes[me.O_DEPART] < 0
        tripmodes.loc[fltr_prevday, me.O_DEPART] = tripmodes.loc[
            fltr_prevday, me.O_DEPART] + nmin_per_day
        fltr_nextday = tripmodes[me.O_DEPART] >= nmin_per_day
        tripmodes.loc[fltr_nextday, me.O_DEPART] = \
            tripmodes.loc[fltr_nextday, me.O_DEPART] - nmin_per_day

        # Calculate the total weight, and produce summary
        final_weight_col = 'FINALWEIGHT'
        tripmodes[final_weight_col] = \
            tripmodes[me.WEIGHT + suffixes[0]] \
            * tripmodes[me.WEIGHT + suffixes[1]]  
        tripmodes['DEP_INTERVAL'] = tripmodes[
            me.O_DEPART].floordiv(time_interval).astype(np.uint32)
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
        period_fltr_expr = \
            f"{me.DEPTIME_COL} >= {start_time} and {me.DEPTIME_COL} < {end_time}"
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