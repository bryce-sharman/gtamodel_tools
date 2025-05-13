""" """
from os import PathLike
import pandas as pd
from pathlib import Path


from gtamodel_tools import ModelVersion



class MicroSim():
    """ Class to store microsim data.

    It is expected that this class is instantiated from microsim_io.read_microsim.

    Parameters
    ----------
    fp: pathlib.Path or str
        Filepath to directory containing the microsim data.

    Attributes
    ----------
    households: pandas.DataFrame
    persons: pandas.DataFrame
    trips: pandas.DataFrame
    trip_modes: pandas.DataFrame
    trip_stations: pandas.DataFrame
    facilitate_passenger: pandas.DataFrame


    Methods
    -------




    summarize_households (values_field, attribute_filter, spatial_aggregation)
    summarize_persons (activity_field, values_field, attribute_filter, spatial_aggregation)
    summarize_persons_od (activity_field, values_field, attribute_filter, orig_spatial_aggregation, dest_spatial_aggregation)
    summarize_trips (activity_field, values_field, attribute_filter, orig_spatial_aggregation, dest_spatial_aggregation)
    summarize_trip_modesplits (activity_field, values_field, attribute_filter, orig_spatial_aggregation, dest_spatial_aggregation)

    """
    def __init__(
            self, model_output_dir: PathLike, model_version: ModelVersion):
        """ Initializes MicroSim results
        
        Args:
            model_output_dir: os.PathLike
                Root directory of the model output.
            model_version: gtamodel_tools.ModelVersion
                GTA model version.

        """
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
