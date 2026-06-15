""" 
Module to store all inputs entered from the configuration file.
"""
import geopandas as gpd
from os import PathLike
import pandas as pd
from pathlib import Path
from yaml import safe_load

import gtamodel_tools.enums.common as en_cmn

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
        self.networks_subdir = c.get('network_subdirectory')
        if self.networks_subdir is not None:
            self.networks_subdir = \
                self.model_outputs_dir / self.networks_subdir
        
        # Test subdirectory holding MicroSim results
        self.microsim_subdir = c.get('microsim_subdirectory')
        if self.microsim_subdir is not None:
            self.microsim_subdir = \
                self.model_outputs_dir / self.microsim_subdir
        # MicroSim results files, within the microsim directory
        self.microsim_filepaths = c.get('microsim_filenames')

        # The demand directory holds auto and transit demand matrices
        # by time period, and also the uses-TTC path-based analysis results.
        self.demand_subdir = c.get('demand_subdirectory')
        if self.demand_subdir is not None:
            self.demand_subdir = \
                self.model_outputs_dir / self.demand_subdir
        
        # The LOS directory holds cost and travel time matrices by time period.
        # The station tranfer files are also stored here.
        # Note that each time period has its own subdirectory.
        self.los_subdirectory = c.get('los_subdirectory')   
        if self.los_subdirectory is not None:
            self.los_subdir = \
                self.model_outputs_dir / self.los_subdirectory

        # Time period definitions
        # Can hold is_assigned flag, auto and transit peak-hr factors and start
        # and end times (minutes after midnight)
        self.time_periods = c.get('time_period_definitions')

        # coordinate reference system underlying network coordinates
        self.network_crs = c.get('network_crs')
        # angle between true-north and local north (degrees counter-clockwise)
        # used for interpretation of validation count data.
        self.grid_offset = c.get('grid_offset')
        self.automode_id = c.get('automode_id')

        # the following inputs are not hard-coded in Emme, hence include
        # here in the config file. Other attributes, such as lanes,
        # are fixed in Emme and hence are not needed here.
        self.link_freeflow_speed_col = c.get('link_freeflow_speed_col')
        self.link_lane_capacity_col = c.get('link_lane_capacity_col')

        self.link_classification_defs = c.get('link_classification_defs')
        self.zone_ranges = c.get('zone_ranges')
        self.node_ranges = c.get('node_ranges')
        self.transit_operator_regexprs = c.get('transit_opererator_regexprs')
        self.line_profile_definitions = c.get('line_profile_definitions')
        self.stn_transfer_regexprs = c.get('stn_transfer_regexprs')
        self.station_name_filepath = c.get('station_name_filepath')
        if self.station_name_filepath is not None:
            self.station_name_filepath = Path(self.station_name_filepath)

        self.traffic_countposts = c.get('traffic_countposts')
        if self.traffic_countposts is not None:
            cp_df = pd.DataFrame.from_dict(
                self.traffic_countposts, orient='index'
            )
            geom = gpd.points_from_xy(cp_df['longitude'], cp_df['latitude'])
            self.traffic_countposts = gpd.GeoDataFrame(
                index=cp_df.index, geometry=geom, crs=en_cmn.WGS_CRS)

        self.transit_countposts = c.get('transit_countposts')
        if self.transit_countposts is not None:
            cp_df = pd.DataFrame.from_dict(
                self.transit_countposts, orient='index'
            )
            geom = gpd.points_from_xy(cp_df['longitude'], cp_df['latitude'])
            self.transit_countposts = gpd.GeoDataFrame(
                index=cp_df.index, 
                data=cp_df['modes'], 
                geometry=geom, 
                crs=en_cmn.WGS_CRS
            )

        # Used to rename output columns to the GTAModel v4.1-v4.2 standard
        # Only needs to be defined if output columns don't match
        # that
        self.microsim_rename_columns = c.get('microsim_rename_columns')

        # Number of samples used in the trip mode choice
        # This is 100 in version v4.0, and 10 in versions v4.1 and 4.2.
        self.microsim_tripmode_nsamples = c.get('microsim_tripmode_nsamples')
