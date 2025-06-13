""" 
Module to read Emme network from network packages, and offer low-level
analysis tools called from other tools in this package.

Network packages are a development of the TravelModellingGroup at the 
University of Toronto that extends Emme's text output to include 
assignment results.
 
"""

from __future__ import annotations

from copy import deepcopy
import geopandas as gpd
import numpy as np
from os import PathLike
import pandas as pd
from pathlib import Path
from typing import Dict, List, Self, Type

from gtamodel_tools.common.gis import calc_linestring_orientation
import gtamodel_tools.common.spatial_aggregator as sa
from gtamodel_tools.config import Config
from gtamodel_tools.network.read_emme_network import read_nwp_base_network, \
    merge_attributes, read_nwp_node_attributes, read_nwp_link_attributes, \
    read_nwp_traffic_results, read_nwp_transit_vehicles, \
    read_nwp_transit_network, read_nwp_transit_line_attributes, \
    read_nwp_transit_segment_results


idx = pd.IndexSlice

class Network(object):
    """ 
    Stores Emme network, optionally including results, and includes low-level
    summary methods.

    Args:
        config: gtamodel_tools.config.Config
            Stored post-processsing configuration.

    """

    def __init__(self, config: Config) -> None:

        # The following attributes are defined directly in the config file
        self.network_crs = config.network_crs
        self.grid_offset = config.grid_offset
        self.automode_id = config.automode_id
        self.link_freeflow_speed_col = config.link_freeflow_speed_col
        self.link_lane_capacity_col = config.link_lane_capacity_col
        self.time_periods = config.time_periods
        self.link_classification_defs = config.link_classification_defs
        self.zone_range_defs = config.zone_ranges
        self.node_range_defs = config.node_ranges
        self.transit_operator_regexprs = config.transit_operator_regexprs
        self.line_profile_definitions = config.line_profile_definitions
        self.station_name_filepath = config.station_name_filepath
        self.station_name_col = 'stn'

        # Column to store cartesian directions, used to match validation counts
        self.link_dir_col = 'link_dir' 

        # Define temporary column names
        self.expr_colname = '_eval_'
        self.fltr_colname = '_filtered_'

        self.err_msg_not_hypernetwork = \
            "This method cannot be run on a hypernetwork."
        self.err_msg_no_traffic_results = \
            "Network with traffic results required."
        self.err_msg_no_transit_results = \
            "Network with transit results required."
        
        if self.station_name_filepath is not None:
            self.station_names = self._read_station_names_file()

    def read_from_nwp(
            self,
            nwp_fp: str | PathLike,
            *,
            node_attributes: str | List[str] | None = None,
            link_attributes: str |  List[str] | None = None,
            tline_attributes: str | List[str] | None = None
        ) -> None:
        """ Read Emme network from TMG's nwp file format.
        
        Args:
            nwp_fp: str | PathLike
                Path to network package (.nwp) containing network and
                (optionally) results.
            coding_standard: str
                Currently must be one of ['ncs11', 'ncs16', 'ncs22']
            node_attributes: str | List[str] | None = None
                Node extra attributes to import. If None will import all node 
                extra attributes. To skip node extra attribute imports, set to [].
                Default is None
            link_attributes: str |  List[str] | None = None
                Link extra attributes to import. If None will import all link 
                extra attributes. To skip link extra attribute imports, set to []
                Default is None
            tline_attributes: str | List[str] | None = None
                Transit line extra attributes to import. If None will import all 
                transit line extra attributes. To skip node transit line attribute 
                imports, set to []. Default is None

        
        """
        linkcols_rename = {'data1': 'ul1', 'data2': 'ul2', 'data3': 'ul3'}
        tlinecols_rename = {'data1': 'ut1', 'data2': 'ut2', 'data3': 'ut3'}
        tsegcols_rename = {'data1': 'uS1', 'data2': 'uS2', 'data3': 'uS3'}

        nwp_fp = Path(nwp_fp)
        if not nwp_fp.is_file():
            raise FileExistsError(f'File does not exsit: {nwp_fp}')
        print(f'Reading Emme network from {nwp_fp}')
        # Read nodes and links, extra attributes and results (if available)
        print('  Reading in base network -- nodes and links')
        self.nodes, self.links = read_nwp_base_network(nwp_fp, self.network_crs)
        # Merge in node and link results, if desired
        self.nodes = merge_attributes(
            self.nodes, nwp_fp, read_nwp_node_attributes, node_attributes)
        self.links = merge_attributes(
            self.links, nwp_fp, read_nwp_link_attributes, link_attributes)
        self.links = self.links.rename(linkcols_rename, axis=1)
        try:
            results = read_nwp_traffic_results(nwp_fp)
            self.links = self.links.merge(
                results, how='left', left_index=True, right_index=True)
            self.has_traffic_results = True
            print('  Network has traffic assignment results')
        except KeyError:
            self.has_traffic_results = False
            print('  Network does not have traffic assignment results')

        # Read in transit network, extra attributes and results (if available)
        print('  Reading in transit network.')
        self.tvehicles = read_nwp_transit_vehicles(nwp_fp)
        self.tlines, self.tsegments = read_nwp_transit_network(nwp_fp)
        try:
            self.tlines = merge_attributes(
                self.tlines, nwp_fp, read_nwp_transit_line_attributes, 
                tline_attributes
            )
        except KeyError:
            print('  Could not merge in transit line attributes.')
        self.tlines = self.tlines.rename(tlinecols_rename, axis=1)
        self.tsegments = self.tsegments.rename(tsegcols_rename, axis=1)
        try:
            results = read_nwp_transit_segment_results(
                nwp_fp, self.tsegments)
            self.tsegments = self.tsegments.merge(
                results[['boardings', 'alightings', 'volume']], 
                how='left', 
                left_index=True, 
                right_index=True
            )
            self.has_transit_results = True
            print('  Network has transit assignment results.')
        except KeyError:
            self.has_transit_results = False
            print('  Network does not have transit assignment results.')


        # Set Emme-specific column names
        self.nodeid_col = 'node'
        self.node_is_centroid_col = 'is_centroid'
        self.link_fromnode_col = 'inode'
        self.link_tonode_col = 'jnode'
        self.link_length_col = 'length'
        self.link_allowed_modes_col = 'modes'
        self.link_numlanes_col = 'lanes'
        self.link_auto_capacity_col = 'auto_capacity'
        self.links[self.link_auto_capacity_col] = \
            self.links[self.link_numlanes_col] \
                * self.links[self.link_lane_capacity_col]
        self.link_auto_volume_col = 'auto_volume'
        self.link_additional_volume_col = 'additional_volume'
        self.link_total_volume_col = 'traffic_volume'
        self.link_auto_travel_time_col = 'auto_time'
        self.traffic_results_cols = \
            ['auto_volume', 'additional_volume', 'auto_time']

        # Transit columns
        self.toperator = "operator"
        self.tvehs_veh_col = 'veh'
        self.tline_line_col = 'line'
        self.tseg_loop_col = 'loop'
        self.tsegment_boardings_col = 'boardings'
        self.tsegment_alightings_col = 'alightings'
        self.tsegments_volume_col = 'volume'
        self.transit_results_cols  = ['boardings', 'alightings', 'volume']

        if self.has_traffic_results:
            self.links[self.link_total_volume_col] = \
                self.links[self.link_auto_volume_col] \
                    + self.links[self.link_additional_volume_col]

        # These are used when collapsing a transit hypernetwork
        self.base_node_col = 'base_node'
        self.base_fromnode_col = 'base_fromnode'
        self.base_tonode_col = 'base_tonode'
        print('  Applying link classifications.')
        self.apply_link_classification()
        print('  Calculating link cartesian directions.')
        self.calculate_link_direction()
        print('  Assigning to transit operators from transit line ID')
        self.apply_transit_operator()
        print('  Applying summary node and zone ranges.')
        self.apply_node_ranges()
        self.apply_zone_ranges()
        print('  Completed reading Emme Network.')

    def apply_zone_ranges(self):
        if self.zone_range_defs is not None:
            zone_ranges = []
            for k, v in self.zone_range_defs.items():
                zone_ranges.append([k, v['min'], v['max']])
            self.zone_ranges = sa.create_spatial_aggregator(
                'custom_ranges', 
                ranges=zone_ranges,
                ids=self.nodes.loc[self.nodes[self.node_is_centroid_col]].index,
                name='zone_ranges'
            )

    def apply_node_ranges(self) -> None:
        if self.node_range_defs is not None:
            node_ranges = []
            for k, v in self.node_range_defs.items():
                node_ranges.append([k, v['min'], v['max']])
            self.node_ranges = sa.create_spatial_aggregator(
                'custom_ranges', 
                ranges=node_ranges,
                ids=self.nodes.index,
                name='node_ranges'
            )

    def apply_link_classification(self):
        """ 
        Add link classification column, as defined in network coding standard
        to links table. 
        """
        if self.link_classification_defs is not None:
            self.linkclass = 'link_class'
            self.links[self.linkclass] = ''
            for k, v in self.link_classification_defs.items():
                fltr = self.links[v['attr']].isin(v['values'])
                self.links.loc[fltr, self.linkclass] = k  

    def calculate_link_direction(self) -> None:
        """ 
        Calculate link direction (NE, EB, SB, WB) based on node coordinates. 
        Direction is based on North direction, which can be offset to a 
        perceived north direction in the region. This offset is defined
        in the network coding standard. 
        """
        self.links[self.link_dir_col] = self.links.apply(
            lambda x: calc_linestring_orientation(
                x['geometry'], self.grid_offset, 'cartesian'), axis=1)

    def apply_transit_operator(self):
        """ 
        Apply the operator regex, defined in the enumeration,to append
        the transit operator to the transit lines and transit segments tables.
        """
        tlines_index = self.tlines.index
        tsegments_index = self.tsegments.index.get_level_values(0)
        self.tlines[self.toperator] = ''
        self.tsegments[self.toperator] = ''
        for operator, regex_expr in self.transit_operator_regexprs.items():
            fltr = tlines_index.str.match(regex_expr)
            self.tlines.loc[fltr, self.toperator] = operator
            fltr = tsegments_index.str.match(regex_expr)
            self.tsegments.loc[fltr, self.toperator] = operator

    def filter_link_connectors(self):
        """ Returns copy of links table with connectors removed"""
        fltr_inode_is_cntrd = self.links.index.get_level_values(
            self.link_fromnode_col).isin(self.zone_ranges().index)
        fltr_jnode_is_cntrd = self.links.index.get_level_values(
            self.link_tonode_col).isin(self.zone_ranges().index)
        return self.links.loc[
            (~fltr_inode_is_cntrd) & (~fltr_jnode_is_cntrd)].copy()



#region Auto traffic summary methods
    def summarize_link_attributes(
            self,
            summary: str,
            include_connectors: bool=False,
            *,
            filter_expression: str | None = None,
            congested_threshold: float | None = None,
            node_aggregation: Type[sa.SpatialAggregator] | None = None,
            aggregate_on_node: str | None = None,
            segment_by_linkclass: bool | None = None,
        ):
        """ Calculate vehicle kilometers travelled.

        Arguments:
            summary: One of 'length', 'lane_length', 'vkt', 'vht'
                or a custom expression
            include_connectors: If True, include connectors in summaries.
                Default is False.
            filter_expression: str or None
                Optional expression to filter links. This is an expression that 
                will be evaluatated using pandas.eval. If used, expression must
                evaluate to either True or False. Default is None. A congestion
                threshold filter is added on top of this expression using the
                congested_threshold parameter.
            congested_threshold: float or None
                If defined, will only calculate VKT on links whose 
                volume/capacity ratio exceeds this treshold.
            node_aggregation: Optional spatial aggregator. If defined will  
                segment by region. Default is None.
            aggregate_on_node: Used if node_aggregation is defined.
                Must either match the from-node or to-node column in the 
                links table. If not defined, then will be set to the 
                from-node column in the links table.
            segment_by_linkclass: bool
                If True, additionally segment VKT by link classification.
        """

        # Lookup the expression
        if summary == 'length':
            expression = self.link_length_col
        elif summary == 'lane_length':
            expression = f'{self.link_length_col} * {self.link_numlanes_col}'
        elif summary == 'vkt':
            expression = self.traffic_vkt_expr
        elif summary == 'vht':
            expression = self.traffic_vht_expr
        else:
            expression = summary
        # Set filter expression
        if isinstance(congested_threshold, int) or \
                isinstance(congested_threshold, float):
            cong_fltr_expr = f'{self.vcr_extr} > {congested_threshold}'
            if filter_expression is not None:
                filter_expression = \
                    f'({filter_expression}) and ({cong_fltr_expr})'
            else:
                filter_expression = cong_fltr_expr
        # See if we need traffic results and don't have them.
        if not self.has_traffic_results:
            if self._test_attrs_in_expression(expression, self.traffic_results):
                raise RuntimeError(self.err_msg_no_traffic_results)
            if self._test_attrs_in_expression(
                    filter_expression, self.traffic_results):
                raise RuntimeError(self.err_msg_no_traffic_results)

        # Set cross-tab columns, either by link facility type
        # and/or node aggregation.
        if node_aggregation is not None:
            if aggregate_on_node == None:
                aggregate_on_node = self.link_fromnode_col
            elif aggregate_on_node not in [
                    self.link_fromnode_col, self.link_tonode_col]:
                raise ValueError(
                    f"Invalid parameter 'aggregate_on_node'. Must be either "
                    f"{self.link_fromnode_col} or {self.link_tonode_col}")
            aggr_colname = node_aggregation().name
            crosstab_columns = [aggr_colname]
        else:
            crosstab_columns = []
        if segment_by_linkclass: 
            crosstab_columns.append(self.linkclass)
        
        # Filter out connectors, if desired
        if include_connectors:
            links = self.links.copy()
        else:
            links = self.filter_link_connectors()

        # Apply filters, start by including everything
        links[self.fltr_colname] = True
        if filter_expression is not None:
            fltr = links.eval(filter_expression).astype(bool)
            links.loc[~fltr, self.fltr_colname] = False

        # Evaluate the summary expression by link
        links[self.expr_colname] = links.eval(expression)    

        # This is the simple case, no geographic or attribute segmentation   
        if len(crosstab_columns) == 0:
            return links.loc[links[self.fltr_colname], self.expr_colname].sum()
        else:
            # Apply geographic segmentation to nodes, merging to links as needed.
            if node_aggregation is not None:
                nodes = self.nodes.merge(
                    node_aggregation(), 
                    how="inner", 
                    left_index=True, 
                    right_index=True
                    )
                links = links.merge(
                    nodes[[aggr_colname]], 
                    left_on=aggregate_on_node, 
                    right_index=True
                    )
            final = links.loc[links[self.fltr_colname]].groupby(
                    by=crosstab_columns)[self.expr_colname].sum()
            if final.index.nlevels == 1:
                return final
            else:
                return final.unstack(fill_value=0.0)  # unstack last level

    def summarize_traffic_across_screenlines(
            self, 
            screenlines: gpd.GeoDataFrame) -> pd.DataFrame:
        """ Summarize traffic volumes and capacity across screenlines:
    
        Args:
            screenlines: gpd.GeoDataFrame with one row per screenline.
                This GeoDataFrame is expected to have the following format:
                - Index is cthe screenline name 
                - geometry column is a LineString that defines the screenline
                - Four columns: Equiv_NB, Equiv_Eb, Equiv_SB, Equiv_WB, which
                  apply a direction label to links, based on their cartesian
                  angle ('NB', 'EB', 'SB', 'WB', respectively). For example,
                  if 'Equiv_NB' is set to 'C1', then all NB links are marked
                  as being in the direction 'C1'.
        Returns:
            pd.DataFrame
                Outputs one row per combination of screenline and direction
                that contains the following:
                - n_links: number of links in direction
                - n_lanes: total number of lanes crossing screenline
                - capacity: total link capacity crossing screenline
                - if the network has traffic results, also outputs
                    - 'auto_vol': assigned auto volumes
                    - 'additional_vol': additional (background) volumes
                    - 'traffic_vol': auto + additional volumes
    
        """
        screenlines = screenlines.to_crs(self.links.crs)

        # Filter out the connectors
        links = self.filter_link_connectors()

        # Remove non-auto-links
        fltr = links[self.link_allowed_modes_col].str.contains(self.automode_id)
        links = links.loc[fltr]
        summary_columns = ['n_links', 'n_lanes', 'capacity']
        aggr_dict = {
            self.link_numlanes_col: ['count', 'sum'],       
            self.link_auto_capacity_col: 'sum',
        }
        if self.has_traffic_results:
            aggr_dict[self.link_auto_volume_col] = 'sum'
            aggr_dict[self.link_additional_volume_col] = 'sum'
            aggr_dict[self.link_total_volume_col] = 'sum'
            summary_columns.extend([
                'auto_vol', 'additional_vol', 'traffic_vol'])

        # Because links can be defined in multiple screenlines, links are
        # matched one-by-one to each screenline.
        screenlines_list = []
        for scrnln_name, scrnln_def in screenlines.iterrows():
            scrnln_gdf = gpd.GeoDataFrame(
                index=[scrnln_name],
                geometry=[scrnln_def.geometry],
                crs=self.links.crs
            )
            links2 = links.sjoin(scrnln_gdf)
            scrnln_summary = links2.groupby(
                ['index_right', self.link_dir_col]).agg(aggr_dict)
            scrnln_summary.columns = summary_columns
            scrnln_summary.index.names = ['screenline', 'dir']
            scrnln_summary.columns.name = 'measure'
            # Apply direction mappings
            scrnln_summary = scrnln_summary.reset_index()
            mapping_dict = {
                'NB': scrnln_def['Equiv_NB'], 
                'EB': scrnln_def['Equiv_EB'],
                'SB': scrnln_def['Equiv_SB'],
                'WB': scrnln_def['Equiv_WB']
            }
            scrnln_summary['dir'] = scrnln_summary['dir'].map(mapping_dict)
            scrnln_summary = scrnln_summary.groupby(['screenline', 'dir']).sum()
            if len(scrnln_summary) > 2:
                print(f'More than 2 directions produced '
                      f'for screenline {scrnln_name}.')
                print('These are the links matched to this screenline:')
                print(links2[['link_dir']])
            screenlines_list.append(scrnln_summary)
        return pd.concat(screenlines_list, axis=0)
#endregion


# #region Auto validation
#     def prepare_trafficvol_expr(
#             self, vol_to_compare: str, phf: float | None) -> str:
#         """ 
#         Convert vol_to_compare to an expression that can be run in pandas.eval.
        
#         Args:
#             vol_to_compare: one of 'auto', 'total', or an expression
#                 using link attributes.
#             phf: peak-hour factor used by model to convert period to
#                 peak-hour demand. If not specified then a peak-hour
#                 validation is performed (equivalent to phf = 1.0).
        
#         """
#         if isinstance(phf, float) or isinstance(phf, int):
#             phf_inv = 1.0 / phf
#         else:
#             phf_inv = 1.0
        
#         if vol_to_compare == 'total':
#             compare_expr = self.trafficvol
#         elif vol_to_compare == 'auto':
#             compare_expr = self.autovol
#         else:
#             compare_expr = vol_to_compare
#         return f'({compare_expr}) * {phf_inv}'

#     def match_links_to_auto_count_stations(
#             self, stns: gpd.GeoDataFrame) -> None:
#         """ Modifies network links table by adding count stations.

#         Args:
#             stns: GeoPandas.GeoDataFrame
#                 Count stations

#         """
#         PT_MAXSPACING = 50
#         BUFFER = 60   # metres
#         N_PTS_COL = 'n_pts'
#         N_INTSC_COL = 'n_intsc_pts'
#         PR_INTSC_COL = 'prop_intsc'
#         GEOM_COL = 'geometry'
#         MAX_ORIENTATION_DELTA = 30
        
#         # Add fields to the links table to hold the match station
#         self.links[en_traffic.SOURCE] = ''
#         self.links[en_traffic.STN_ID] = ''
#         self.links[en_traffic.DIR] = ''
        
#         # Limit to candidate links by using a sideways-only buffer
#         # Create a table of links and candidate count stations
#         fltr_hasautomode = self.links[
#             self.modes].str.contains(self.auto_mode)
#         fltr_not_connector = \
#             (self.links.index.get_level_values(0) >= self.min_regnode_id) & \
#             (self.links.index.get_level_values(1) >= self.min_regnode_id)
#         road_links = self.links.loc[fltr_hasautomode & fltr_not_connector]
#         stns2 = stns.to_crs(self.crs)
#         stns_buffer_geom = stns2.geometry.buffer(BUFFER, cap_style='flat')
#         stns_buffer = gpd.GeoDataFrame(stns2, geometry=stns_buffer_geom)
#         candidate_matches = stns_buffer.sjoin(road_links, how='inner')
#         candidate_matches = candidate_matches.rename({
#             'index_right0': 'i', 'index_right1': 'j'}, axis=1)
#         candidate_matches = candidate_matches[['i', 'j']].merge(
#             road_links[[GEOM_COL]], left_on=['i', 'j'],right_index=True)
#         candidate_matches = gpd.GeoDataFrame(
#             candidate_matches, geometry=candidate_matches[GEOM_COL])
#         candidate_match_stns = candidate_matches.index.unique()
#         candidate_matches = candidate_matches.reset_index()
#         candidate_matches = candidate_matches.set_index(
#             [en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR, 'i', 'j'])
#         candidate_matches = candidate_matches.sort_index()
        
#         for cmstn in candidate_match_stns:
#             # Get a buffer around the station
#             stn_geom = stns2.at[cmstn, GEOM_COL]
#             stn_buffer = stn_geom.buffer(BUFFER, cap_style='flat')

#             # Search for points along each link that lie within buffer
#             subset = candidate_matches.loc[idx[cmstn]].copy()
#             subset[N_PTS_COL] = 0
#             subset[N_INTSC_COL] = 0
#             for sbt_i, sbt in subset.iterrows():
#                 vx, vy = sbt.geometry.segmentize(PT_MAXSPACING).xy
#                 seg_pts = gpd.points_from_xy(vx, vy)
#                 subset.at[sbt_i, N_PTS_COL] = len(seg_pts)
#                 subset.at[sbt_i, N_INTSC_COL] = seg_pts.intersects(
#                     stn_buffer).sum()
#             if subset[N_INTSC_COL].max() == 0:
#                 # No intersections found -- move on
#                 continue
#             subset[PR_INTSC_COL] = subset[N_INTSC_COL] / subset[N_PTS_COL]
#             max_prop_intsc = subset[PR_INTSC_COL].max()
#             fltr_subset_max = (subset[PR_INTSC_COL] == max_prop_intsc)
#             # Find the first entry with the same orientation
#             stn_angle = calc_linestring_orientation(stn_geom, 0, 'angle')
#             for sbt_i, sbt in subset.loc[fltr_subset_max].iterrows():
#                 lk_angle = calc_linestring_orientation(sbt.geometry, 0, 'angle')
#                 if fabs(lk_angle - stn_angle) < MAX_ORIENTATION_DELTA:
#                     self.links.loc[
#                         sbt_i, idx[en_traffic.SOURCE, en_traffic.STN_ID, 
#                                    en_traffic.DIR]
#                         ] = cmstn
#                     break

#     def save_link_auto_cntstation_mappings(self, fp: PathLike) -> None:
#         """ Output link mappings to csv file. 
        
#         Args:
#             fp: File in which to save link mappings
#         """
#         fltr = self.links['source'] != ''
#         self.links.loc[
#                 fltr, 
#                 [en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR]
#             ].to_csv(fp)

#     def read_and_apply_link_auto_cntstation_mappings(
#             self, fp: PathLike) -> None:
#         """ 
#         Read previously calculated link mappings from a file and apply to links.

#         Args:
#             fp: File from which to read link mappings
#         """
#         mappings = pd.read_csv(
#             fp, index_col=self.links.index.names, dtype=str, na_values='')
#         stn_mapping_cols = [en_traffic.SOURCE, en_traffic.STN_ID, 
#                             en_traffic.DIR]
#         for col in stn_mapping_cols:
#             if col in self.links.columns:
#                 raise RuntimeError(
#                     f'Cannot have {stn_mapping_cols} columns in links table '
#                     f'before merging in count station mapping.'
#                 )
#         self.links = self.links.merge(
#             mappings, how='left', left_index=True, right_index=True)
#         self.links[stn_mapping_cols] = self.links[stn_mapping_cols].fillna('')

#     def prepare_link_validation_table(
#             self, 
#             counts: pd.Series, 
#             vol_to_compare: str,
#             phf: float | None = None, 
#         ) -> pd.DataFrame:
#         """ Prepare a table comparing link volumes vs period traffic counts.

#         Links must be matched to count stations before running this method.

#         Args:
#             counts: pd.Series containing traffic counts against which,
#                 the modelled volumes are to be compared. 
#             vol_to_compare: one of 'auto', 'total', or an expression
#                 using link attributes.
#             phf: peak-hour factor used by model to convert period to
#                 peak-hour demand. If not specified then a peak-hour
#                 validation is performed (equivalent to phf = 1.0).
                
#         Returns:
#             links pandas DataFrame with the following columns:
#                 - link class
#                 - traffic count source
#                 - traffic count direction
#                 - count volume in column 'count_vol'
#                 - model volume in column 'model_vol'

#         """
#         modelvol_attr = 'model_vol'
#         vdtnvol_attr = 'count_vol'
#         compare_expr = self.prepare_trafficvol_expr(vol_to_compare, phf)
            
#         links = self.links.copy()
#         # Calculate modelled volume
#         links[modelvol_attr] = links.eval(compare_expr)  
#         # Merge in count volume
#         counts = counts.copy()
#         counts.name = vdtnvol_attr
#         links = links.merge(
#             counts,
#             left_on=[en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR],
#             right_index=True
#         )
#         return links[[self.linkclass, en_traffic.SOURCE, en_traffic.DIR, 
#                     modelvol_attr, vdtnvol_attr]]

#     def validate_traffic_across_screenlines(
#             self,
#             screenlines: gpd.GeoSeries,
#             comparisons: Dict,
#         ) -> pd.DataFrame:
#         """ Summarize traffic volumes and capacity across screenlines:
    
#         Args:
#             screenlines: gpd.GeoSeries with one row per screenline.
#                 Index is considered as the screenline name while
#                 the geometry defines the screenline.
#             comparisons: Dict
#                 - key is the comparison name
#                 - the value is another dictionary defined as follows:
#                     model_volumes: str 
#                         Can be one of:
#                         - 'auto': auto volumes only
#                         - 'total': total volumnes, or 
#                         - an expression using link attributes.
#                     counts: pd.Series
#                         Traffic counts against which, the modelled volumes 
#                         are to be compared.
#                     phf: float | None
#                         peak-hour factor used by model to convert period to
#                         peak-hour demand. If not specified then a peak-hour
#                         validation is performed (equivalent to phf = 1.0).
#         Returns:
#             pd.DataFrame
#                 Outputs one row per combination of screenline and direction
#                 that contains the following:
#                 - n_links: number of links in direction
#                 - n_lanes: total number of lanes crossing screenline
#                 - capacity: total link capacity crossing screenline
#                 - modelled_vol: modelled volume on all links
#                 - n_obsv_links: number of links with counts
#                 - n_obsv_lanes: number of lanes on links with counts
#                 - link_porosity: proportion of observed links
#                 - lane_porosity: proportion of observed lanes
#                 - capacity_porosity: proportion of observed link capacity
#                 - count: traffic counts on observed links
#                 - obsv_modelled_vol: modelled volume on observed links

    
#         """
#         linkcap_col = 'link_cap'
#         is_cntstn_col = 'is_cnt_stn'
#         model_vol_col = 'model_vol'
#         screenlines = screenlines.to_crs(self.links.crs)
#         for k_cmp, v_cmp in comparisons.items():
#             if 'phf' not in v_cmp.keys():
#                 comparisons[k_cmp]['phf'] = None

#         # Prepare links table
#         links = self.links
#         links[linkcap_col] = links.eval(f'{self.lanes} * {self.lanecap}')
#         links[is_cntstn_col] = 0
#         links.loc[links[en_traffic.SOURCE] != '', is_cntstn_col] = 1
#         fltr_inode_is_cntrd = \
#             links.index.get_level_values('inode') < self.min_regnode_id
#         fltr_jnode_is_cntrd = \
#             links.index.get_level_values('jnode') < self.min_regnode_id
#         links = links.loc[(~fltr_inode_is_cntrd) & (~fltr_jnode_is_cntrd)]
#         results_list = []
#         for scrn_idx, scrn_row in screenlines.iterrows():
#             if 'index_right' in links.columns:
#                 links = links.drop('index_right', axis=1)
#             screenline_gdf = gpd.GeoDataFrame(
#                 geometry=[scrn_row.geometry],
#                 index=[scrn_idx],
#                 crs=screenlines.crs
#             )
#             links2 = links.sjoin(screenline_gdf)

#             for k_cmp, v_cmp in comparisons.items():
#                 counts_col = f'{k_cmp}_counts'
#                 modelvol_eval_str = self.prepare_trafficvol_expr(
#                     v_cmp['model_volumes'], v_cmp['phf'])
#                 links2[model_vol_col] = links2.eval(modelvol_eval_str)
#                 # Merge in the counts
#                 counts = v_cmp['counts']
                
#                 counts.name = counts_col
#                 links2 = links2.merge(
#                     v_cmp['counts'], how='left', 
#                     left_on=en_traffic.STN_INDEX_COLS, right_index=True,
#                 )
#                 all = links2.groupby(self.link_dir_col).agg({
#                     self.lanes: ['count', 'sum'], 
#                     linkcap_col: 'sum',
#                     model_vol_col: 'sum'
#                 })
#                 all.columns = ['n_links', 'n_lanes', 'capacity', 'modelled_vol']
                
#                 obsv_fltr = links2[en_traffic.SOURCE] != ''
#                 links_obsv = links2.loc[obsv_fltr]
#                 obsvd = links_obsv.groupby(self.link_dir_col).agg({
#                     self.lanes: ['count', 'sum'], 
#                     linkcap_col: 'sum',
#                     counts_col: 'sum', 
#                     model_vol_col: 'sum'
#                 })
#                 obsvd.columns = ['n_obsv_links', 'n_obsv_lanes', 'obsv_linkcap', 
#                                  'count', 'obsv_modelled_vol']
#                 combined = pd.concat([all, obsvd], axis=1)
#                 combined['link_porosity'] = \
#                     combined['n_obsv_links'] / combined['n_links']
#                 combined['lane_porosity'] = \
#                     combined['n_obsv_lanes'] / combined['n_lanes']
#                 combined['capacity_porosity'] = \
#                     combined['obsv_linkcap'] / combined['capacity']
#                 combined = combined.reset_index()
#                 combined['screenline'] = scrn_idx
#                 combined['comparison'] = k_cmp
#                 combined = combined.set_index(
#                     ['screenline', 'link_dir', 'comparison']).fillna(0)
#                 results_list.append(combined)
                
#         return pd.concat(results_list, axis=0)


# #endregion


#region Transit
    def calculate_line_profiles_from_config(
            self) -> pd.DataFrame:
        """ 
        Calculate line profiles for all transit lines defined in the 
        network configuration file. This is a convenience method that
        calls calc_line_profile for each transit line defined in the 
        network configuration file.
        
        Returns:
            pd.DataFrame
                MultiIndex DataFrame indexed by transit line ID and station ID/label
                Contains the following columns:
                - boardings: Number of boardings at the station
                - alightings: Number of alightings at the station
                - volume: Passenger volume leaving the station
        """
        all_profiles = []
        for line, line_directions in self.line_profile_definitions.items():
            for ld, tlines in line_directions.items():
                try:
                    station_names = self.station_names.loc[idx[:, line]]
                    profile = self.calc_line_profile(tlines, station_names)
                except KeyError:
                    profile = self.calc_line_profile(tlines, None)
                if profile is not None:
                    profile['Line'] = line
                    profile['Direction'] = ld
                    all_profiles.append(profile)
                else:
                    print(f'    No profile for {line} {ld}, skipping.')
        final = pd.concat(all_profiles, axis=0)
        final_index_names = final.index.names
        final = final.reset_index()
        final = final.set_index(['Line', 'Direction'] + final_index_names)
        return final

    def calc_line_profile(
            self, tline_ids: str|List[str], 
            stn_labels: pd.Series | Dict | None=None
        ) -> pd.DataFrame | None:
        """ 
        Calculate boardings, alightings and on-board riders along transit lines. 
        If multiple lines are defined, one line must be a shorter version of the 
        other line (This function cannot currently handle branching).
        
        Args:
            tline_id: str or List[str]
                Transit line id(s)
            stn_labels: pd.Series | Dict | None
                Optional mapping between node ID and station label.
                Default is None.

        Returns:
            pd.DataFrame | None
                - Index: station label, if defined in stn_labels, or the node id. 
                - Contains the following columns:
                    - boardings: Number of boardings at the station
                    - alightings: Number of alightings at the station
                    - volume: Passenger volume leaving the station
            Returns None if none of the transit lines exist in the network.
        """
        def combine_lineprofiles(current, new, how, s):
            df = current.merge(
                new, how=how, left_index=True, right_index=True, suffixes=s
            ).fillna(0)
            for col in self.transit_results_cols:
                xcol = f'{col}{s[0]}'
                ycol = f'{col}{s[1]}'
                df[col] = df[xcol] + df[ycol]
                df = df.drop([xcol, ycol], axis=1)
            return df
            
        suffixes=['_x', '_y']
        if isinstance(tline_ids, list) and len(tline_ids) == 1:
            tline_ids = tline_ids[0]

        # Case 1: single line
        if isinstance(tline_ids, str):
            line_profile = self.calc_line_profile_1line(tline_ids)
        else:
            # Case 2: multiple lines
            tsegs_list = []
            for tline_id in tline_ids:
                line_profile = self.calc_line_profile_1line(tline_id)
                if line_profile is not None:
                    tsegs_list.append(line_profile)
            # This is the case where multiple lines are in the list but
            # only one actually exists.
            if len(tsegs_list) == 1:
                line_profile = tsegs_list[0]
            else:
                # At this point we know there are at least two transit lines.
                ex = tsegs_list[0]
                for i in range(1, len(tsegs_list)):
                    new = tsegs_list[i]
                    if ex.index.equals(new.index):
                        how = 'inner'   # can really be anything
                    else:
                        ex_minus_new = ex.index.difference(new.index)
                        new_minus_ex = new.index.difference(ex.index)
                        if len(ex_minus_new) > 0 and len(new_minus_ex) == 0:
                            how = 'left'
                        elif len(ex_minus_new) == 0 and len(new_minus_ex) > 0:
                            how = 'right'
                        else:
                            print('No transit line is a subset of the other, '
                                'Cannot create joint line profile')
                            return None
                        current = combine_lineprofiles(ex, new, how, suffixes)
                line_profile = current
        if line_profile is None:
            return None
        line_profile = self.remove_unused_loops(line_profile)
        line_profile = self.apply_stnname_mapping(line_profile, stn_labels)
        return line_profile

    def calc_line_profile_1line(self, tline_id) -> pd.DataFrame:
        """ 
        Helper function to get the boardings, alightings and volume along 
        the line. 

        Args:
            tline_id: str
                transit line
        Returns:
            DataFrame where the index matches the transit segments 
            (line, from_node, to_node, loop), and the columns are 
            the transit segmehts results (boardings, alightings, volume)

        Notes:
            This method makes no attempt to remove the loop columns from the 
            segments. This will be done in calc_line_profile.
        """
        if tline_id not in self.tlines.index:
            print(f'Transit line {tline_id} does not exist.')
            return None
        tsegs = self.tsegments.loc[
            idx[tline_id, :, :, :, :], self.transit_results_cols]
        
        # add the hidden segment
        last_tseg = tsegs.iloc[-1]
        fromnode = last_tseg.name[2]  # j-node of last node
        tonode = 0                    # hidden node is always 0
        loop = last_tseg.name[3]      
        alightings = last_tseg[self.tsegments_volume_col]  # everyone gets off
        # Add a row to the end, pandas will do this through a loc 
        # if the row does not exist in the index
        tsegs.loc[tline_id, fromnode, tonode, loop] = [0, 0, 0]
        tsegs.at[(tline_id, fromnode, tonode, loop), 
                 self.tsegment_alightings_col] = alightings

        # Drop the line and to_node columns out of the index
        tsegs = tsegs.reset_index(
            [self.tline_line_col, self.link_tonode_col], drop=True)
        return tsegs

    def remove_unused_loops(self, line_profile: pd.DataFrame) -> pd.DataFrame:
        """ Remove the loop column if the line is not looped. """
        tseg_loop = line_profile.index.get_level_values(self.tseg_loop_col)
        if tseg_loop.nunique() == 1:
            return line_profile.droplevel(self.tseg_loop_col, axis=0)
        else:
            return line_profile

    def apply_stnname_mapping(
            self, 
            line_profile: pd.DataFrame, 
            stn_labels: Dict | pd.Series | None
        ) -> pd.DataFrame:
        if stn_labels is None:
            return line_profile
        line_profile = line_profile.copy()
        node_ids = pd.Series(
            line_profile.index.get_level_values(self.link_fromnode_col))
        stns = node_ids.map(stn_labels)
        isna = pd.isna(stns)
        stns.loc[isna] = node_ids.loc[isna]    
        if line_profile.index.nlevels == 1:  # no loops
            line_profile = line_profile.set_index(stns)
            line_profile.index.name = self.station_name_col
        else:
            index_cols = line_profile.index.names.copy()
            index_cols.remove(self.link_fromnode_col)
            index_cols = [self.station_name_col] + index_cols
            line_profile = line_profile.reset_index()
            line_profile[self.station_name_col] = stns
            line_profile = line_profile.set_index(index_cols)
            line_profile.index.names = index_cols
            line_profile = line_profile.drop(self.link_fromnode_col, axis=1)
        return line_profile 

    def summarize_transit_segments(
            self, 
            expression: str,
            filter_expression: str | None = None,
            node_aggr: Type[sa.SpatialAggregator] | None = None,
            crosstab_columns: str | List[str] | None = None
        ) -> float | pd.DataFrame:
        """ 
        Summarizes an expression over a transit segment table.

        Can optionally choose to:
        - apply arbitrary filters.
        - apply geographical aggregations
        - include crosstab columns, in which case the expression is summarized 
          for each segment. 

        Arguments:
            expression: str
                Value to be aggregated. This is an expression that 
                will be evaluatated using pandas.eval.
            filter_expression: str | None
                Defines transit segment filter using expression that will be  
                evaluatated using pandas.eval. If None then no filter is 
                applied. Link, transit line and transit segment and transit 
                vehicle attributes can be specified. Default is None.
            node_aggr: sa.SpatialAggregator or None
                Spatial aggregation applied to nodes. All segment attributes
                are aggregated at the I-node. If None, then values from all 
                segments are summarized together. Default is None.
            crosstab_columns: str | List[str] | None = None
                If None, will compute a single value per spatial aggregation
                area. Otherwise will segment calculations by defined columns.
                Default is None.

        """
        def test_attrs_in_expr_or_filter(expression, filter_expression, cols):
            return (self._test_attrs_in_expression(expression, cols) or 
                self._test_attrs_in_expression(filter_expression, cols))

        # Test if transit line, transit vehicle or link attributes are 
        # defined in either the expression or the filter
        reqs_transit_results = test_attrs_in_expr_or_filter(
            expression, filter_expression, self.transit_results_cols)
        reqs_traffic_results = test_attrs_in_expr_or_filter(
            expression, filter_expression, self.traffic_results_cols)
        reqs_links_columns = test_attrs_in_expr_or_filter(
            expression, filter_expression, self.links.columns)
        reqs_tlines_columns = test_attrs_in_expr_or_filter(
            expression, filter_expression, self.tlines.columns)
        reqs_tvehs_columns = test_attrs_in_expr_or_filter(
            expression, filter_expression, self.tvehicles.columns)

        if reqs_traffic_results and not self.has_traffic_results:
            raise RuntimeError(self.err_msg_no_traffic_results)
        if reqs_transit_results and not self.has_transit_results:
            raise RuntimeError(self.err_msg_no_transit_results)

        # Test if trying to perform node aggregation on a hypernetwork
        if node_aggr is not None and self.is_hypernetwork:
            raise RuntimeError(
                'Cannot perform transit summaries with node aggregations on a '
                'hypernetwork. Collapse network before running summary.')

        # Merge in required tables to the transit segments
        tsegs = self.tsegments.reset_index()
        if reqs_links_columns:
            tsegs = tsegs.merge(
                self.links, 
                left_on=[self.link_fromnode_col, self.link_tonode_col], 
                right_index=True
            )
        if reqs_tlines_columns or reqs_tvehs_columns:
            tsegs = tsegs.merge(
                self.tlines, left_on=[self.tline_line_col], 
                right_index=True, suffixes=['', '_l'])
            if reqs_tvehs_columns:
                tsegs = tsegs.merge(
                    self.tvehicles, left_on=[self.tvehs_veh_col], 
                    right_index=True, suffixes=['', '_v'])
                
        # Apply filter if defined
        tsegs[self.fltr_colname] = True
        if isinstance(filter_expression, str):
            tsegs[self.fltr_colname] = \
                tsegs.eval(filter_expression).astype(bool)
        tsegs = tsegs.loc[tsegs[self.fltr_colname]]

        #Evalulate expression
        tsegs[self.expr_colname] = tsegs.eval(expression)   

        if node_aggr is None and crosstab_columns is None:
            # This is the simple case, no spatial aggregation   
            return tsegs[self.expr_colname].sum()
        else:
            # Merge in geographic segmentation
            aggregation_columns = []
            if node_aggr is not None:
                aggr_colname = node_aggr().name
                nodes = self.nodes.merge(
                    node_aggr(), how="inner", left_index=True, right_index=True)
                tsegs = tsegs.merge(
                    nodes[[aggr_colname]], left_on='inode', right_index=True)
                if crosstab_columns is not None:
                    aggregation_columns = [aggr_colname] + crosstab_columns
            else:
                aggregation_columns = crosstab_columns
            return tsegs.groupby(
                aggregation_columns)[self.expr_colname].sum()      


    def _test_if_hypernetwork(self) -> bool:
        """ Look for overlapping links, indicating this is a hypernetwork. """
        links = self.links.reset_index()   
        links = links.merge(
            self.nodes[['x', 'y']], 
            how='left', 
            left_on='inode', 
            right_index=True)
        links = links.merge(
            self.nodes[['x', 'y']], 
            how='left', 
            left_on='jnode', 
            right_index=True, 
            suffixes=['_i', '_j']
        )
        n_links = links.groupby(['x_i', 'y_i', 'x_j', 'y_j'])['inode'].count()
        n_links.name = 'n_links'
        if n_links.max() > 1:
            return True
        else:
            return False

    def _read_station_names_file(self) -> pd.Series:
        """ 
        Reads station names from the station name file, if it exists.
        
        Returns:
            pd.Series: 
                Series defined as follows:
                - MultiIndex containing: Node ID and Line
                - Series values are station names.

        """
        if self.station_name_filepath is None: 
            return None
        elif not self.station_name_filepath.is_file():
            raise FileNotFoundError(
                f'Station name file {self.station_name_filepath} does not exist.'
            )
        elif self.station_name_filepath.suffix == '.csv':
            s = pd.read_csv(
                self.station_name_filepath, index_col=[0, 1], squeeze=True,
            )
            s.index.names = ['Node ID', 'Line']
            s.name = 'stn_names'
            return s
        elif self.station_name_filepath.suffix == '.xlsx':
            s = pd.read_excel(
                self.station_name_filepath, index_col=[0, 1],
            ).squeeze()
            s.index.names = ['Node ID', 'Line']
            s.name = 'stn_names'
            return s
        else:
            raise ValueError(
                f'Station name file {self.station_name_filepath} must be a .csv or .xlsx file.'
            )

#endregion

#region Collapse transit hypernetwork
    def collapse_hypernetwork(
            self, aggregation_rules: dict | None=None) -> Self:
        """ Returns a new EmmeNetwork with equivalent single-layer network. 
        
        Arguments:
            aggregation_rules: optional Dict
                Optional dictionary containing aggregration rules to apply when 
                collapsing network. If specified, expected keys are 'nodes'
                and 'links'. Under each key is another dictionary containing 
                the attribute (or column) name and aggregation function to be applied 
                in a pandas.groupby.aggregate. See
                https://pandas.pydata.org/docs/reference/api/pandas.core.groupby.DataFrameGroupBy.aggregate.html
                Default is 'sum' for link 'volume' and 'additional_volume'
                columns; otherwise 'first'.

        Returns:
            EmmeNetwork:
                EmmeNetwork with collapsed hypernetwork.
        
        Notes:
            Transit lines do not appear to be modified in a hypernetwork, 
            we can leave unchanged.
        
        """
        fromnode_col = self.link_fromnode_col
        tonode_col = self.link_tonode_col
        base_fromnode_col = self.base_fromnode_col
        base_tonode_col = self.base_tonode_col
        nodeid_col = self.nodeid_col
        base_node_col = self.base_node_col


        agrls = self._create_aggregation_dictionary(aggregation_rules)
        new_network = deepcopy(self)
        if not self.is_hypernetwork:
            return new_network

        # Create a working links table by identifying and merging in
        # base network nodes
        links = self._merge_link_basenodes()
        
        # Create node mapping from the working links table
        inode_mapping = links[[fromnode_col, base_fromnode_col]]
        inode_mapping .columns = [nodeid_col, base_node_col]
        jnode_mapping = links[[tonode_col, base_tonode_col]]
        jnode_mapping .columns = [nodeid_col, base_node_col]
        node_mappings = pd.concat([inode_mapping, jnode_mapping], axis=0)
        node_mappings = node_mappings.drop_duplicates().set_index(
            nodeid_col).squeeze().sort_index()
        
        # Use working links and node mappings to produce collapsed network
        new_network.links = self._collapse_links(links, agrls['links'])
        new_network.nodes = self._collapse_nodes(node_mappings, agrls['nodes'])
        new_network.tsegments = self._collapse_tsegments(node_mappings)
        return new_network

    @staticmethod
    def _add_default_aggr_dict_cols(
            aggr_rules: dict, df_cols: pd.Index, results_cols: List | None,
        ) -> Dict:
        user_setcols = list(aggr_rules.keys())
        aggr_rules2 = {}
        for c in df_cols:
            if c in user_setcols:
                aggr_rules2[c] = aggr_rules[c]
            elif c in results_cols:
                aggr_rules2[c] = 'sum'
            else:
                aggr_rules2[c] = 'first'
        return aggr_rules2

    def _create_aggregation_dictionary(self, agg_rules: dict | None) -> Dict:
        if agg_rules is None:
            agg_rules = {}
        if 'nodes' not in agg_rules.keys():
            agg_rules['nodes'] = {}
        if 'links' not in agg_rules.keys():
            agg_rules['links'] = {}
        # Complete the aggregation rules dictionary
        agg_rules['nodes'] = self._add_default_aggr_dict_cols(
            agg_rules['nodes'], self.nodes.columns, [])
        agg_rules['links'] = self._add_default_aggr_dict_cols(
            agg_rules['links'], self.links.columns, [
                self.link_auto_volume_col, self.link_additional_volume_col])
        return agg_rules

    def _collapse_links(
            self, links: pd.DataFrame, agrls: Dict) -> pd.DataFrame:
        """ Produces collapsed link table.  """
        fltr = links[self.base_fromnode_col] != links[self.base_tonode_col]
        links2 = links.loc[fltr].groupby(
            [self.base_fromnode_col, self.base_tonode_col]).aggregate(agrls)
        links2.index.names = self.links.index.names
        return links2
    
    def _collapse_nodes(
            self, node_mappings: pd.Series, agrls: Dict) -> pd.DataFrame:
        """ Produces collapsed node table. """
        nodes = self.nodes.reset_index()
        nodes['new_node'] = nodes[self.nodeid_col].map(node_mappings)
        nodes2 = nodes.groupby('new_node').aggregate(agrls)
        nodes2.index.name = self.nodes.index.name
        return nodes2
    
    def _collapse_tsegments(self, node_mappings: pd.Series) -> pd.DataFrame:
        """ Produces transit segment table using collapsed links.  
        
        Note that this function involves simply swapping out the base network
        node ids, switching the links to the base network links. 
        
        """
        tsegments = self.tsegments.reset_index()
        tsegments[self.link_fromnode_col] = \
            tsegments[self.link_fromnode_col].map(node_mappings)
        tsegments[self.link_tonode_col] = \
            tsegments[self.link_tonode_col].map(node_mappings)
        tsegments = tsegments.set_index(self.tsegments.index.names)
        return tsegments

    def _merge_link_basenodes(self) -> pd.DataFrame:
        """ Merges base nodes for link i_nodes and j_nodes into links table. 
            
        Returns:
            pd.DataFrame
                Modified links table with added columnes of base_inode and 
                base_jnode. Note that the index is reset anticipate
                further operations on the returned links table.
            
        """
        # Objective is to return a dataframe of x and y locations
        # for all non-hyper-network links.

        # Merge x and y coordinates to all links in the network
        fromnode_col = self.link_fromnode_col
        tonode_col = self.link_tonode_col
        base_fromnode_col = self.base_fromnode_col
        base_tonode_col = self.base_tonode_col
        nodeid_col = self.nodeid_col

        links = self.links.reset_index()   
        n_links_before_merge = len(links)
        links = links.merge(
            self.nodes[['x', 'y']], left_on=fromnode_col, right_index=True)
        links = links.merge(
            self.nodes[['x', 'y']], 
            left_on=tonode_col, 
            right_index=True, 
            suffixes=['_i', '_j']
        )
        if len(links) != n_links_before_merge:
            raise RuntimeError('Length change after merging node coordinates.')

        # Only keep non-hypernetwork links
        fltr = self.node_ranges() != 'Hypernetwork nodes'
        non_hypntwk_nodes = self.node_ranges().loc[fltr]
        non_hypntwk_nodes = self.nodes.loc[non_hypntwk_nodes.index].index
        base_links = links.loc[
            (links[fromnode_col].isin(non_hypntwk_nodes)) & 
            (links[tonode_col].isin(non_hypntwk_nodes))
        ]
        # Groupby X and Y coordinates
        base_links = base_links.groupby(['x_i', 'y_i', 'x_j', 'y_j'])[
            [fromnode_col, tonode_col]].first()
        base_links.columns = [base_fromnode_col, base_tonode_col]

        # Now merge in the base link to the links hyper-network
        # Doing a left merge to keep all links. 
        # Note that links that transfer between hyper-network layers are not 
        # merged as there is no base-network-only equivalent for these links.
        links = links.merge(
            base_links, 
            how='left', 
            left_on=['x_i', 'y_i', 'x_j', 'y_j'], 
            right_index=True
        )
        if len(links) != n_links_before_merge:
            raise RuntimeError(
                'Length change after merging in base I and J nodes.')
        
        # Deal with the base-to-hyper-network transfer links
        fltr_tlinks = \
            pd.isna(links[base_fromnode_col]) | pd.isna(links[base_tonode_col])
        if np.any(
                (links.loc[fltr_tlinks, 'x_i'] != links.loc[fltr_tlinks, 'x_j']) | 
                (links.loc[fltr_tlinks, 'y_i'] != links.loc[fltr_tlinks, 'y_j'])
            ):
            raise RuntimeError(
                'Non base-to-hypernetwork transfer links were not '
                'merged in links to base_network links merge.')
        # Need to find the base nodes in these cases. Note that if there are
        # 3+ layers in the hypernetwork, then there are links where neither
        # their I or J nodes are in the network
        # Make sure that we have all transfer nodes by including I and J nodes
        inodes = links[[fromnode_col, 'x_i', 'y_i']]
        inodes.columns = [nodeid_col, 'x', 'y']
        jnodes = links[[tonode_col, 'x_j', 'y_j']]
        jnodes.columns = [nodeid_col, 'x', 'y']
        tnodes = pd.concat([inodes, jnodes], axis=0)
        tnodes = tnodes.drop_duplicates()
        tnodes = tnodes.sort_values(nodeid_col)
        # Identify base-network nodes
        base_tnodes = tnodes.loc[tnodes[nodeid_col].isin(non_hypntwk_nodes)]
        # Merge in the base transfer node by X and Y location
        tnodes2 = tnodes.merge(
            base_tnodes, how='left', on=['x', 'y'], suffixes=['', '_b'])
        tnodes2 = tnodes2.drop(['x', 'y'], axis=1).set_index(
            nodeid_col).squeeze()
        # Use a mapping to apply the base node (easier than a merge)
        links.loc[fltr_tlinks, base_fromnode_col] = links.loc[
            fltr_tlinks, fromnode_col].map(tnodes2)
        links.loc[fltr_tlinks, base_tonode_col] = links.loc[
            fltr_tlinks, tonode_col].map(tnodes2)

        # Now clean up the links table for all links
        links = links.drop(['x_i', 'y_i', 'x_j', 'y_j'], axis=1)
        links[base_fromnode_col] = links[base_fromnode_col].astype(np.uint32)
        links[base_tonode_col] = links[base_tonode_col].astype(np.uint32)
        return links
    
#endregion

    @staticmethod
    def _test_attrs_in_expression(expr: str | None, attributes: List):
        """ Check if attributes are in an expression. """
        if expr is None:
            return False
        for attr in attributes:
            if attr in expr:
                return True
        return False


#region properties

    @property
    def traffic_vkt_expr(self) -> str:
        return f'{self.link_length_col} * {self.link_total_volume_col}'

    @property
    def traffic_vht_expr(self) -> str:
        return f'{self.link_auto_travel_time_col} * {self.link_total_volume_col} / 60.0'

    @property
    def vcr_extr(self) -> str:
        return f'{self.link_total_volume_col} / {self.link_auto_capacity_col}'

    @property
    def transit_vkt_expr(self) -> str:
        return f'{self.link_length_col} * {self.tsegments_volume_col}'

    @property
    def is_hypernetwork(self) -> bool:
        return self._test_if_hypernetwork()



#endregion

