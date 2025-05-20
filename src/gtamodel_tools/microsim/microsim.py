from os import PathLike
import pandas as pd
from pathlib import Path
from typing import Optional, Type

from gtamodel_tools import ModelVersion
import gtamodel_tools.common.data as data
import gtamodel_tools.common.spatial_aggregator as sa


class MicroSim():
    """ Class to store and summarize MicroSimulation results.

    Args:
        model_output_dir: os.PathLike
            Root directory of the model output.
        model_version: gtamodel_tools.ModelVersion
            GTA model version.

    Attributes:



    Methods:



    """
    def __init__(
            self, model_output_dir: PathLike, model_version: ModelVersion):
        self._model_output_dir = Path(model_output_dir)
        self._model_version = model_version
        self._set_gtamodel_enums()      
        self._read_ms_results()


    def _set_gtamodel_enums(self) -> None:
        if self._model_version == ModelVersion.GTAModelv4_0:
            import gtamodel_tools.enums.microsim.gtamodelv4_0 as me
        elif self._model_version == ModelVersion.GTAModelv4_1:
            raise NotImplementedError(
                "Microsim results not yet implemented for GTAModelv4.1")
            import gtamodel_tools.enums.microsim.gtamodelv4_1 as me
        elif self._model_version == ModelVersion.GTAModelv4_2:
            raise NotImplementedError(
                "Microsim results not yet implemented for GTAModelv4.2")
            import gtamodel_tools.enums.microsim.gtamodelv4_2 as me
        else:
            raise ValueError("Invalid 'model_version'.")

        self._time_period_definitions = me.TIME_PERIOD_DEFINITIONS
        self._n_tripmode_samples = me.N_TRIPMODE_SAMPLES

        self._microsim_dir = self._model_output_dir / me.MICROSIM_DIR

        self._hhlds_fn = self._microsim_dir / me.FILENAMES['households']
        self._hhld_cols = me.HHLD_COLS
        self._hhld_dtypes = me.HHLD_DTYPES
        self._hhld_index_cols = me.HHLD_INDEX_COLS

        self._pers_fn = self._microsim_dir / me.FILENAMES['persons']
        self._pers_cols = me.PERS_COLS
        self._pers_dtypes = me.PERS_DTYPES
        self._pers_index_cols = me.PERS_INDEX_COLS

        self._trip_fn = self._microsim_dir / me.FILENAMES['trips']
        self._trip_cols = me.TRIP_COLS
        self._trip_dtypes = me.TRIP_DTYPES
        self._trip_index_cols = me.TRIP_INDEX_COLS

        self._tripmodes_fn = self._microsim_dir / me.FILENAMES['trip_modes']
        self._tripmodes_cols = me.TRIPMODE_COLS
        self._tripmode_dtypes = me.TRIPMODE_DTYPES
        self._tripmode_index_cols = me.TRIPMODE_INDEX_COLS

        self.tripstations_fn = \
            self._microsim_dir / me.FILENAMES['trip_stations']
        self._tripsnt_cols = me.TRIPSTN_COLS
        self._tripstn_dtypes = me.TRIPSTN_DTYPES
        self._tripstn_index_cols = me.TRIPSTN_INDEX_COLS

        self.facpass_fn = \
            self._microsim_dir / me.FILENAMES['facilitate_passenger']
        self._facpac_cols = me.FACPAC_COLS
        self._facpac_dtypes = me.FACPAC_DTYPES
        self._facpac_index_cols = me.FACPAC_INDEX_COLS


    def _read_ms_results(self) -> None:
        """ Read all MicroSim results files, saving to the instance. """
        self._households = pd.read_csv(
            self._hhlds_fn, 
            dtype=self._hhld_dtypes, 
            index_col=self._hhld_index_cols
        )
        self._persons = pd.read_csv(
            self._pers_fn, 
            dtype=self._pers_dtypes, 
            index_col=self._pers_index_cols
        )
        self._trips = pd.read_csv(
            self._trip_fn,
            dtype=self._trip_dtypes, 
            index_col=self._trip_index_cols)

        self._tripmodes = pd.read_csv(
            self._tripmodes_fn, 
            dtype=self._tripmode_dtypes, 
            index_col=self._tripmode_index_cols
        )
        self._tripstations = pd.read_csv(
            self.tripstations_fn, 
            dtype=self._tripstn_dtypes, 
            index_col=self._tripstn_index_cols
        )
        self._facilitatepassengers = pd.read_csv(
            self.facpass_fn, 
            dtype=self._facpac_dtypes, 
            index_col=self._facpac_index_cols
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
            if time_period not in self._time_period_definitions.keys():
                raise AttributeError(
                    "Invalid time period. If defined, must be one of: "
                    f"{list(self._time_period_definitions.keys())}")
            tripmodes_filter_expr = self._apply_timeperiod_filter(
                time_period, tripmodes_filter_expr)

        # We always have to merge trips and tripmodes
        trips = data.apply_dataframe_filter(
            self._trips, trips_filter_expr)
        tripmodes = data.apply_dataframe_filter(
            self._tripmodes, tripmodes_filter_expr)
        trips_with_modes = tripmodes.reset_index().merge(
            trips, 
            how='inner',
            left_on=[
                self._tripmodes_cols['hhld_id'], 
                self._tripmodes_cols['pers_id'], 
                self._tripmodes_cols['trip_id']
            ],
            right_index=True
        )

        # If a households or persons filter is applied, filter table and merge  
        # into tripmodes table.
        if isinstance(households_filter_expr, str):
            households_df = data.apply_dataframe_filter(
                self._households, households_filter_expr)
            fltr = trips_with_modes[
                self._tripmodes_cols['hhld_id']].isin(households_df.index)
            trips_with_modes = trips_with_modes.loc[fltr]
        if isinstance(persons_filter_expr, str):
            persons_df = data.apply_dataframe_filter(
                self._persons, persons_filter_expr).reset_index()
            fltr = (trips_with_modes[self._tripmodes_cols['hhld_id']].isin(
                        persons_df[self._pers_cols['hhld_id']])) & (
                    trips_with_modes[self._tripmodes_cols['pers_id']].isin(
                        persons_df[self._pers_cols['pers_id']]))
            trips_with_modes = trips_with_modes.loc[fltr]
        
        # Calculate the total weight, and produce summary
        final_weight_col = 'FINALWEIGHT'
        if self._trip_cols['weight'] == self._tripmodes_cols['weight']:
            weight_col = self._tripmodes_cols['weight']
            trips_with_modes[final_weight_col] = \
                trips_with_modes[weight_col + '_x'] \
                * trips_with_modes[weight_col + '_y']
        else:
            trips_with_modes[final_weight_col] = \
                trips_with_modes[self._trip_cols['weight']] \
                * trips_with_modes[self._tripmodes_cols['weight']]
        s = sa.summarize_table_with_spatial_aggregation(
            df=trips_with_modes, 
            values=final_weight_col, 
            geom_id=[self._trip_cols['ozone'], self._trip_cols['dzone']],
            spatial_aggregations=[origin_sa, destination_sa], 
        ).squeeze() / self._n_tripmode_samples
        s.index.names = [origin_sa.name, destination_sa.name]
        return s

    def _apply_timeperiod_filter(
            self, time_period: str, tripmodes_filter_expr: str | None) -> str:
        """ 
        Either create new or modify existing tripmodes filter to filter trips
        by time period.
        """
        start_time = self._time_period_definitions[time_period]['start']
        end_time = self._time_period_definitions[time_period]['end']
        period_fltr_expr = f"o_depart >= {start_time} and o_depart < {end_time}"
        if not isinstance(tripmodes_filter_expr, str):
            return period_fltr_expr
        else:
            return f'({tripmodes_filter_expr}) and ({period_fltr_expr})'

#endregion
