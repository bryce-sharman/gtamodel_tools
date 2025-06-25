""" 
Module to store all inputs entered from the configuration file.
"""
import geopandas as gpd
from os import PathLike
import pandas as pd
from pathlib import Path
from yaml import safe_load

class Config(object):
    """ Class to store configuration file inputs.

    Also performs basic input validation such as testing such as file existence.

    Parameters:
        model_outputs_dir: PathLike
        config_fp: PathLike
            Path to configuration file

    """

    def __init__(
            self, 
            model_outputs_dir: PathLike, 
            config_fp: PathLike
        ) -> None:
        self.model_outputs_dir = Path(model_outputs_dir)
        if not self.model_outputs_dir.is_dir():
            raise FileExistsError(
                f'Directory not found: {self.model_outputs_dir}')

        config_fp = Path(config_fp)
        with open(config_fp, 'r') as f:
            c = safe_load(f)
        
        # Set and test directory holding network results
        self.networks_subdir = \
            self.model_outputs_dir / c['network_subdirectory']
        if not self.networks_subdir.is_dir():
            raise FileExistsError(
                f'Directory not found: {self.networks_subdir}')
        
        # Test subdirectory holding MicroSim results
        self.microsim_subdir = \
            self.model_outputs_dir / c['microsim_subdirectory']
        if not self.microsim_subdir.is_dir():
            raise FileExistsError(
                f'Directory not found: {self.microsim_subdir}')
        
        # MicroSim results files, within the microsim directory
        self.microsim_filepaths = c['microsim_filenames']
        # add full path to microsim results files and test file existence
        for ms_fn, ms_name in self.microsim_filepaths.items():
           self.microsim_filepaths[ms_fn] = self.microsim_subdir / ms_name
           if not self.microsim_filepaths[ms_fn].is_file():
              raise FileExistsError('File not found: {results_fp}')
           
        # Time period definitions
        # Start and end times are in minutes after midnight
        # Start times are inclusive; end times are exclusive
        self.time_periods = c['time_period_definitions']

        # coordinate reference system underlying network coordinates
        self.network_crs = c['network_crs']
        # angle between true-north and local north (degrees counter-clockwise)
        # used for interpretation of validation count data.
        self.grid_offset = c['grid_offset']
        self.automode_id = c['automode_id']

        # the following inputs are not hard-coded in Emme, hence include
        # here in the config file. Other attributes, such as lanes,
        # are fixed in Emme and hence are not needed here.
        self.link_freeflow_speed_col = c['link_freeflow_speed_col']
        self.link_lane_capacity_col = c['link_lane_capacity_col']

        # Optional configuration file inputs
        self.link_classification_defs = c.get('link_classification_defs')
        self.screenlines_fp = c.get('screenlines_fp')
        self.zone_ranges = c.get('zone_ranges')
        self.node_ranges = c.get('node_ranges')
        self.transit_operator_regexprs = c.get('transit_opererator_regexprs')
        self.line_profile_definitions = c.get('line_profile_definitions')

        self.station_name_filepath = c.get('station_name_filepath')
        if self.station_name_filepath is not None:
            self.station_name_filepath = Path(self.station_name_filepath)

        self.traffic_countposts = c.get('traffic_countposts')
        if self.traffic_countposts is not None:
            cp_df = pd.DataFrame.from_dict(self.traffic_countposts, orient='index')
            geom = gpd.points_from_xy(cp_df['longitude'], cp_df['latitude'])
            self.traffic_countposts = gpd.GeoDataFrame(
                index=cp_df.index, geometry=geom, crs='EPSG:4326')

        self.transit_countposts = c.get('transit_countposts')
        if self.transit_countposts is not None:
            cp_df = pd.DataFrame.from_dict(self.transit_countposts, orient='index')
            geom = gpd.points_from_xy(cp_df['longitude'], cp_df['latitude'])
            self.transit_countposts = gpd.GeoDataFrame(
                index=cp_df.index, data=cp_df['modes'], geometry=geom, crs='EPSG:4326')

        # Used to rename output columns to the GTAModel v4.1-v4.2 standard
        # Only needs to be defined if output columns don't match
        # that
        self.microsim_rename_columns = c.get('microsim_rename_columns')

        # Number of samples used in the trip mode choice
        # This is 100 in version v4.0, and 10 in versions v4.1 and 4.2.
        self.microsim_tripmode_nsamples = c.get('microsim_tripmode_nsamples')
