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
from shapely import Point, Polygon
from typing import Self, Type

from gtamodel_tools.common.gis import calculate_direction
from gtamodel_tools.common.screenlines import read_screenlines
from gtamodel_tools.common.spatial_aggregator import create_spatial_aggregator
from gtamodel_tools.common.spatial_aggregator import SpatialAggregator
from gtamodel_tools.config import Config
from gtamodel_tools.network.read_emme_network import read_nwp_base_network, \
    merge_attributes, read_nwp_node_attributes, read_nwp_link_attributes, \
    read_nwp_traffic_results, read_nwp_transit_vehicles, \
    read_nwp_transit_network, read_nwp_transit_line_attributes, \
    read_nwp_transit_segment_results
from gtamodel_tools.enums.common import GPD_GEOM_COL

idx = pd.IndexSlice

class Network(object):
    """ 
    Stores Emme network, optionally including results, and includes low-level
    summary methods.

    Args:
        config: gtamodel_tools.config.Config
            Stored post-processsing configuration.
        start_time: int | None
            Start time of the network assignment_period in minutes after 
            midnight. This is needed period-level transit summaries.
            Default is None.
        end_time: int | None
            End time of the network assignment_period in minutes after 
            midnight. This is needed period-level transit summaries. 
            Default is None.
        auto_phf: float | None
            Auto peak-hour factor. Is None if network does not have auto 
            assignment results. Default is None.

    """

    def __init__(
            self, 
            config: Config, 
            start_time: int|None=None, 
            end_time: int|None=None,
            auto_phf: float|None=None,
            ) -> None:

        # The following attributes are defined directly in the config file
        self.network_crs = config.network_crs
        self.grid_offset = config.grid_offset
        self.automode_id = config.automode_id
        self.lk_ffspeed_col = config.link_freeflow_speed_col
        self.lk_lanecap_col = config.link_lane_capacity_col
        self.time_periods = config.time_periods
        self.link_cldefs = config.link_classification_defs
        self.zone_range_defs = config.zone_ranges
        self.node_range_defs = config.node_ranges
        self.transit_operator_regexprs = config.transit_operator_regexprs
        self.line_profile_definitions = config.line_profile_definitions
        self.station_name_filepath = config.station_name_filepath
        self.traffic_countposts = config.traffic_countposts
        self.transit_countposts = config.transit_countposts

        self.start_time = start_time
        self.end_time = end_time
        self.auto_phf = auto_phf

        self.geometry_col = 'geometry'

        # Column to store link classification
        self.linkclass = 'link_class'
        # Column to store cartesian directions, used to match validation counts
        self.link_dir_col = 'link_dir' 
        # Column to store counts station name
        self.station_name_col = 'stn'
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
            node_attributes: str | list[str] | None = None,
            link_attributes: str |  list[str] | None = None,
            tline_attributes: str | list[str] | None = None
        ) -> None:
        """ Read Emme network from TMG's nwp file format.
        
        Args:
            nwp_fp:
                Path to network package (.nwp) containing network and
                (optionally) results.
            node_attributes:
                Node extra attributes to import. If None will import all node 
                extra attributes. To skip node extra attribute imports, 
                set to []. Default is None.
            link_attributes: 
                Link extra attributes to import. If None will import all link 
                extra attributes. To skip link extra attribute imports, 
                set to []. Default is None.
            tline_attributes:
                Transit line extra attributes to import. If None will import all 
                transit line extra attributes. To skip node transit line 
                attribute imports, set to []. Default is None.

        
        """
        if self.network_crs is None:
            raise RuntimeError(
                "Network CRS must be defined in config to read network."
            )
        if self.grid_offset is None:
            raise RuntimeError(
                "Grid offset must be defined in config to read network."
            )
        if self.automode_id is None:
            raise RuntimeError(
                "Automode ID must be defined in config to read network."
            )
        if self.lk_ffspeed_col is None:
            raise RuntimeError(
                "Link freeflow speed column must be defined in config "
                "to read network."
            )
        if self.lk_lanecap_col is None:
            raise RuntimeError(
                "Link lane capacity column must be defined in config to "
                "read network."
            )

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
        self.ndid_col = 'node'
        self.nd_iscentroid_col = 'is_centroid'
        self.lk_fnode_col = 'inode'
        self.lk_tnode_col = 'jnode'
        self.lk_len_col = 'length'
        self.lk_modes_col = 'modes'
        self.lk_nlanes_col = 'lanes'
        self.lk_autocap_col = 'auto_capacity'
        self.links[self.lk_autocap_col] = \
            self.links[self.lk_nlanes_col] \
                * self.links[self.lk_lanecap_col]
        self.lk_autovol_col = 'auto_volume'
        self.lk_addvolume_col = 'additional_volume'
        self.lk_totvol_col = 'traffic_volume'
        self.lk_autottime_col = 'auto_time'
        self.traffic_results_cols = \
            ['auto_volume', 'additional_volume', 'auto_time']

        # Transit columns
        self.toperator = "operator"
        self.tv_veh_col = 'veh'
        self.tl_mode_col = 'mode'
        self.tl_line_col = 'line'
        self.ts_loop_col = 'loop'
        self.tl_hdw_col = 'headway'
        self.ts_board_col = 'boardings'
        self.ts_alight_col = 'alightings'
        self.ts_vol_col = 'volume'
        self.transit_results_cols  = ['boardings', 'alightings', 'volume']
        self.tv_vcap_col = 'total_capacity'

        if self.has_traffic_results:
            self.links[self.lk_totvol_col] = \
                self.links[self.lk_autovol_col] \
                    + self.links[self.lk_addvolume_col]

        # These are used when collapsing a transit hypernetwork
        self.base_node_col = 'base_node'
        self.base_fnode_col = 'base_fromnode'
        self.base_tnode_col = 'base_tonode'
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
            self.zone_ranges = create_spatial_aggregator(
                'custom_ranges', 
                ranges=zone_ranges,
                ids=self.nodes.loc[self.nodes[self.nd_iscentroid_col]].index,
                name='zone_ranges'
            )

    def apply_node_ranges(self) -> None:
        if self.node_range_defs is not None:
            node_ranges = []
            for k, v in self.node_range_defs.items():
                node_ranges.append([k, v['min'], v['max']])
            self.node_ranges = create_spatial_aggregator(
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
        if self.link_cldefs is not None:
            self.links[self.linkclass] = ''
            for k, v in self.link_cldefs.items():
                fltr = self.links[v['attr']].isin(v['values'])
                self.links.loc[fltr, self.linkclass] = k  

    def calculate_link_direction(self) -> None:
        """ 
        Calculate link direction (NE, EB, SB, WB) based on node coordinates. 
        Direction is based on North direction, which can be offset to a 
        perceived north direction in the region. This offset is defined
        in the network coding standard. 
        """
        def calc_link_direction_(row):
            frompt = Point(row.geometry.coords[0])
            topt = Point(row.geometry.coords[-1])
            return calculate_direction(frompt, topt, self.grid_offset)

        self.links[self.link_dir_col] = self.links.apply(
            lambda x: calc_link_direction_(x), axis=1)

    def apply_transit_operator(self):
        """ 
        Apply the operator regex, defined in the enumeration,to append
        the transit operator to the transit lines and transit segments tables.
        """
        if self.transit_operator_regexprs is not None:
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
        centroids = self.nodes.loc[self.nodes['is_centroid']].index
        links = self.links.copy().reset_index()
        links = links.loc[
            ~links[self.lk_fnode_col].isin(centroids) & 
            ~links[self.lk_tnode_col].isin(centroids)
        ]
        return links.set_index([self.lk_fnode_col, self.lk_tnode_col])

#region Auto traffic summary methods
    def summarize_link_attributes(
            self,
            summary: str,
            include_connectors: bool=False,
            *,
            filter_expression: str | None = None,
            congested_threshold: float | None = None,
            node_aggregation: Type[SpatialAggregator] | None = None,
            aggregate_on_node: str | None = None,
            segment_by_linkclass: bool | None = None,
        ) -> float | pd.DataFrame:
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
                links table (inode or jnode for Emme networks). If not defined, 
                then will be set to the from-node column in the links table.
            segment_by_linkclass: bool
                If True, additionally segment VKT by link classification.
        """

        # Lookup the expression
        if summary == 'length':
            expression = self.lk_len_col
        elif summary == 'lane_length':
            expression = self.lane_length_expr
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
            if self._test_attrs_in_expression(
                    expression, self.traffic_results_cols):
                raise RuntimeError(self.err_msg_no_traffic_results)
            if self._test_attrs_in_expression(
                    filter_expression, self.traffic_results_cols):
                raise RuntimeError(self.err_msg_no_traffic_results)

        # Set cross-tab columns, either by link facility type
        # and/or node aggregation.
        if node_aggregation is not None:
            if aggregate_on_node == None:
                aggregate_on_node = self.lk_fnode_col
            elif aggregate_on_node not in [
                    self.lk_fnode_col, self.lk_tnode_col]:
                raise ValueError(
                    f"Invalid parameter 'aggregate_on_node'. Must be either "
                    f"{self.lk_fnode_col} or {self.lk_tnode_col}")
            aggr_colname = node_aggregation.name
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
                    node_aggregation.mapping, 
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
                return final.unstack(fill_value=0)  # unstack last level

    def summarize_traffic_across_screenlines(
            self, screenlines_fp: PathLike, index_col: str
        ) -> pd.DataFrame:
        """ Summarize traffic volumes and capacity across screenlines:
    
        Args:
            screenlines_fp: Path to shapefile, or equivalent
            index_col: column in geospatial data containing the 
                screenlines names.

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
        screenlines = read_screenlines(screenlines_fp, index_col)
        screenlines = screenlines.to_crs(self.network_crs)

        # Filter out the connectors and non-auto links
        links = self.filter_link_connectors()
        fltr = links[self.lk_modes_col].str.contains(self.automode_id)
        links = gpd.GeoDataFrame(links.loc[fltr])  # keep typehinting happy

        summary_columns = ['n_links', 'n_lanes', 'capacity']
        aggr_dict = {
            self.lk_nlanes_col: ['count', 'sum'],       
            self.lk_autocap_col: 'sum',
        }
        if self.has_traffic_results:
            summary_columns.extend([
                'auto_vol', 'additional_vol', 'traffic_vol'])
            aggr_dict[self.lk_autovol_col] = 'sum'
            aggr_dict[self.lk_addvolume_col] = 'sum'
            aggr_dict[self.lk_totvol_col] = 'sum'

        # Because links can be defined in multiple screenlines, links are
        # matched one-by-one to each screenline. The final step is to concat
        # all the individual screenlines together.
        screenlines_list = []
        for scrnln_name, scrnln_def in screenlines.iterrows():
            scrnln_gdf = gpd.GeoDataFrame(
                index=[scrnln_name],
                geometry=[scrnln_def.geometry],
                crs=self.network_crs
            )
            links2 = links.sjoin(scrnln_gdf)
            equiv_dir = {
                'NB': scrnln_def['EquivNB'], 
                'EB': scrnln_def['EquivEB'],
                'SB': scrnln_def['EquivSB'],
                'WB': scrnln_def['EquivWB']
            }
            links2['equiv_linkdir'] = links2[self.link_dir_col].map(equiv_dir)
            scrnln_summary = links2.groupby(
                ['index_right', 'equiv_linkdir']).agg(aggr_dict)
            scrnln_summary.columns = summary_columns
            scrnln_summary.index.names = ['screenline', 'dir']
            scrnln_summary.columns.name = 'measure'
            scrnln_summary = scrnln_summary.groupby(
                level=['screenline', 'dir']).sum()
            if len(scrnln_summary) > 2:
                print(f'More than 2 directions produced '
                      f'for screenline {scrnln_name}.')
                print('These are the links matched to this screenline:')
                print(links2[[self.link_dir_col]])
            screenlines_list.append(scrnln_summary)
        final = pd.concat(screenlines_list, axis=0)
        final['vcr'] = final['traffic_vol'] / final['capacity']
        return final
    
    def output_traffic_results_at_countposts(
            self, max_distance: float=100.0, tol: float=0.1) -> pd.DataFrame:
        """ 
        Outputs auto, additional volume and total volume at countposts,
        which are defined in the configuration file.

        Args:
            max_distance: maximum search distance in metres
                Default is 100 metres.
            tol: threshold at which to match additional links to a countpost
                in metres. Default is 0.1 metres.
                
        Returns:
            pandas DataFrame:
                - MultiIndex is the countpost description and direction
                - Values are:
                    auto volume, additional volume, total volume, link 
                    capacity and V/C ratio.
        """

        countposts = self.traffic_countposts
        if self.traffic_countposts is None:
            raise RuntimeError(
                "No traffic countposts defined in the configuration file.")
        countposts = self.traffic_countposts.to_crs(self.network_crs)
        countposts_col = 'countpost'

        # Filter out connectors and non-auto links
        links = self.filter_link_connectors()
        auto_filter = links[self.lk_modes_col].str.contains(
            self.automode_id)
        links = links.loc[auto_filter]

        # This is the full search list of the links 
        # (keeping the typehinting happy) by forcing the GeoDataFrame
        full_list = gpd.GeoDataFrame(links.copy())
        
        # Find closest links
        #   As it is possible for multiple links to have the same distance
        #   (e.g. reverse links)  but testing has found cases where all links 
        #   are not picked up sjoin_nearest. Hence I will do this by looping
        #   through each countpost, and for each countpost iteratively
        #   removing matched links until distance threshold is exceeded.
        cp_links_l = []
        for cp_id, row in countposts.iterrows():
            # Get a fresh list of the links (keeping the typehinting happy)
            links = full_list  
            cp = countposts.loc[[cp_id]]
            cp_links = cp.sjoin_nearest(links, distance_col='distance')
            current_dist = cp_links['distance'].min()
            if current_dist > max_distance:
                continue
            cp_links_l.append(cp_links)
            while True:
                # Drop the matched links from the links GeoDataFrame
                linkids_to_drop = list(
                    cp_links[
                        [self.lk_fnode_col, self.lk_tnode_col]
                    ].itertuples(index=False, name=None)
                )
                links = links.drop(linkids_to_drop, axis=0)
                cp_links = cp.sjoin_nearest(links, distance_col='distance')
                if cp_links['distance'].min() > current_dist + tol:
                    break
                cp_links_l.append(cp_links)
        cp_links = pd.concat(cp_links_l, axis=0)

        cp_links.index.name = countposts_col
        cp_links = cp_links.reset_index()
        cp_links = cp_links.set_index([countposts_col, self.link_dir_col])
        cp_links.to_clipboard()
        # Check that the same link doesn't show up for multiple countposts
        chk = cp_links.groupby([
            self.lk_fnode_col, self.lk_tnode_col])['length'].count()
        if chk.max() > 1:
            raise RuntimeError('Links were connected to multiple countposts.')
        cp_links = cp_links[[
            self.lk_autovol_col, 
            self.lk_addvolume_col, 
            self.lk_totvol_col, 
            self.lk_autocap_col]]
        cp_links['vcr'] = cp_links[self.lk_totvol_col].divide(
            cp_links[self.lk_autocap_col])
        return cp_links

#endregion


#region Transit

    def summarize_transit_across_screenlines(
            self, screenlines_fp: PathLike, index_col: str
        ) -> pd.DataFrame:
        """ Summarize transit volumes and capacity across screenlines:
    
        Args:
            screenlines_fp: Path to shapefile, or equivalent
            index_col: column in geospatial data containing the 
                screenlines names.

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
        screenlines = read_screenlines(screenlines_fp, index_col)
        screenlines = screenlines.to_crs(self.network_crs)

        # Merge in mode, headway and vehicle capacities
        tsegs = self.tsegments.reset_index()
        tsegs = tsegs.merge(
            self.tlines[[self.tl_mode_col, self.tv_veh_col, self.tl_hdw_col]], 
            left_on=self.tl_line_col, 
            right_index=True
        )
        tsegs = tsegs.merge(
            self.tvehicles[[self.tv_vcap_col]], 
            left_on=self.tv_veh_col, 
            right_index=True
        )
        # Merge in the link geometries cartesian direction columns
        tsegs = tsegs.merge(
            self.links[[GPD_GEOM_COL, self.link_dir_col]], 
            left_on=[self.lk_fnode_col, self.lk_tnode_col], 
            right_index=True
        )
        tsegs = gpd.GeoDataFrame(
            index=tsegs.index,
            geometry=tsegs[GPD_GEOM_COL],
            data=tsegs,
            crs=self.network_crs
        )
        tsegs['n_routes'] = 1
        summary_columns = ['n_routes']
        if self.start_time is not None and self.end_time is not None:
            tsegs['capacity'] = tsegs[self.tv_vcap_col] * \
                (self.end_time - self.start_time) / tsegs[self.tl_hdw_col]
            summary_columns.append('capacity')
        else:
            print('    Not computing countpost capacity as network period '
            'start and end times are not defined.')
        if self.has_transit_results:
            summary_columns.append('volume')

        # Because links can be defined in multiple screenlines, links are
        # matched one-by-one to each screenline. The final step is to concat
        # all the individual screenlines together.
        screenlines_list = []
        for scrnln_name, scrnln_def in screenlines.iterrows():
            scrnln_gdf = gpd.GeoDataFrame(
                index=[scrnln_name],
                geometry=[scrnln_def.geometry],
                crs=self.network_crs
            )
            tsegs2 = tsegs.sjoin(scrnln_gdf)
            equiv_dir = {
                'NB': scrnln_def['EquivNB'], 
                'EB': scrnln_def['EquivEB'],
                'SB': scrnln_def['EquivSB'],
                'WB': scrnln_def['EquivWB']
            }
            tsegs2['equiv_linkdir'] = tsegs2[self.link_dir_col].map(equiv_dir)

            scrnln_summary = tsegs2.groupby(
                ['index_right', 'equiv_linkdir', self.tl_mode_col]
            )[summary_columns].sum()
            scrnln_summary.index.names = ['screenline', 'dir', 'mode']
            scrnln_summary.columns.name = 'measure'
            screenlines_list.append(scrnln_summary)
        final = pd.concat(screenlines_list, axis=0)
        if 'capacity' in final.columns:
            final['vcr'] = final['volume'] / final['capacity']
        return final.sort_index()


    def output_transit_results_at_countposts(
            self, max_distance: float=100.0, tol: float=0.1) -> pd.DataFrame:
        """ 
        Outputs transit volumes and capacities at countposts,
        which are defined in the configuration file. Summaries
        are always output for the transit period.

        Args:
            max_distance: maximum search distance in metres
                Default is 100 metres.
            tol: threshold at which to match additional links to a countpost
                in metres. Default is 0.1 metres.

        Returns:
            pandas DataFrame:
                - MultiIndex is the countpost description and direction
                - Values are:
                    - 'volume': transit volume on all routes using the link
                    if the network start_time and end_time are set, will also
                    compute:
                    - 'capacity': total capacity of all routes using the link
                    - 'vcr': V/C ratio.

        """    
        volume_col = self.ts_vol_col
        capacity_col = 'capacity'
        countposts_col = 'countpost'
        vcr_col = 'vcr'
        if self.is_hypernetwork:
            raise RuntimeError(
                "Transit countposts cannot be computed on a hyper network... "
                "Collapse first.")
        countposts = self.transit_countposts
        if countposts is None:
            raise RuntimeError(
                "No transit countposts defined in the configuration file.")
        countposts = countposts.to_crs(self.network_crs)  

        # Merge in mode, headway and vehicle capacities
        tsegs = self.tsegments.reset_index()
        tsegs = tsegs.merge(
            self.tlines[[self.tl_mode_col, self.tv_veh_col, self.tl_hdw_col]], 
            left_on=self.tl_line_col, 
            right_index=True
        )
        tsegs = tsegs.merge(
            self.tvehicles[[self.tv_vcap_col]], 
            left_on=self.tv_veh_col, 
            right_index=True
        )

        output_cols = ['volume']
        if self.start_time is not None and self.end_time is not None:
            tsegs[capacity_col] = tsegs[self.tv_vcap_col] * \
                (self.end_time - self.start_time) / tsegs[self.tl_hdw_col]
            output_cols.append(capacity_col)
        else:
            print('    Not computing countpost capacity as network period '
            'start and end times are not defined.')

        # Find closest links
        #   As it is possible for multiple links to have the same distance
        #   (e.g. reverse links)  but testing has found cases where all links 
        #   are not picked up sjoin_nearest. Hence I will do this by looping
        #   through each countpost, and for each countpost iteratively
        #   removing matched links until distance threshold is exceeded.
        cp_links_l = []
        for cp_id, row in countposts.iterrows():
            # Get a fresh list of the links with modes used in countpost
            ts_tmp = tsegs.loc[tsegs[self.tl_mode_col].isin(row['modes'])]

            # Aggregate transit segments up to links, then we can use the
            # same approach as output_traffic_results_at_countposts
            a2links = ts_tmp.groupby(
                [self.lk_fnode_col, self.lk_tnode_col])[output_cols].sum()
            # Merge in the link geometry
            a2links = a2links.merge(
                self.links[[self.link_dir_col, GPD_GEOM_COL]], 
                left_index=True, 
                right_index=True
            )
            a2links = gpd.GeoDataFrame(
                index=a2links.index,
                data=a2links[[self.link_dir_col] + output_cols],
                geometry=a2links[GPD_GEOM_COL],
                crs=self.network_crs
            )
            
            # Find the closest links (that are in the previously defined
            # links list) to the countpost
            cp = countposts.loc[[cp_id]]
            cp_links = cp.sjoin_nearest(a2links, distance_col='distance')
            current_dist = cp_links['distance'].min()
            if current_dist > max_distance:
                continue
            cp_links_l.append(cp_links)
            while True:
                # Drop the matched links from the links GeoDataFrame
                linkids_to_drop = pd.MultiIndex.from_arrays([
                    cp_links[self.lk_fnode_col], 
                    cp_links[self.lk_tnode_col]
                ])
                a2links = a2links.drop(linkids_to_drop, axis=0)
                if len(a2links) == 0:
                    break
                cp_links = cp.sjoin_nearest(a2links, distance_col='distance')
                if cp_links['distance'].min() > current_dist + tol:
                    break
                cp_links_l.append(cp_links)
        final = pd.concat(cp_links_l, axis=0)
        final.index.name = countposts_col
        final = final.reset_index()
        final = final.set_index([countposts_col, self.link_dir_col])
        if capacity_col in output_cols:
            final[vcr_col] = final[volume_col] / final[capacity_col]
            output_cols.append(vcr_col)
        return final[output_cols]


    def calculate_line_profiles(
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
            self, tline_ids: str | list[str], 
            stn_labels: pd.Series | dict | None=None
        ) -> pd.DataFrame | None:
        """ 
        Calculate boardings, alightings and on-board riders along transit lines. 
        If multiple lines are defined, one line must be a shorter version of the 
        other line (This function cannot currently handle branching).
        
        Args:
            tline_id: 
                Transit line id(s)
            stn_labels:
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


    def calc_line_profile_1line(self, tline_id) -> pd.DataFrame | None:
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
        # tsegs.name ['line', 'inode', 'jnode', 'loop']
        fromnode = last_tseg.name[2]  # jnode
        tonode = 0                    # hidden node is always 0
        loop = last_tseg.name[3]      # loop   
        alightings = last_tseg[self.ts_vol_col]  # everyone gets off
        # Add a row to the end, pandas will do this through a loc 
        # if the row does not exist in the index

        tsegs.loc[tline_id, fromnode, tonode, loop] = [0, 0, 0]
        tsegs.at[(tline_id, fromnode, tonode, loop), 
                 self.ts_alight_col] = alightings

        # Drop the line and to_node columns out of the index
        tsegs = tsegs.reset_index(
            [self.tl_line_col, self.lk_tnode_col], drop=True)
        return tsegs


    def remove_unused_loops(self, line_profile: pd.DataFrame) -> pd.DataFrame:
        """ Remove the loop column if the line is not looped. """
        tseg_loop = line_profile.index.get_level_values(self.ts_loop_col)
        if tseg_loop.nunique() == 1:
            return line_profile.droplevel(self.ts_loop_col, axis=0)
        else:
            return line_profile


    def apply_stnname_mapping(
            self, 
            line_profile: pd.DataFrame, 
            stn_labels: dict | pd.Series | None
        ) -> pd.DataFrame:
        if stn_labels is None:
            return line_profile
        line_profile = line_profile.copy()
        node_ids = pd.Series(
            line_profile.index.get_level_values(self.lk_fnode_col))
        stns = node_ids.map(stn_labels)
        isna = pd.isna(stns)
        stns.loc[isna] = node_ids.loc[isna]    
        if line_profile.index.nlevels == 1:  # no loops
            line_profile = line_profile.set_index(stns)
            line_profile.index.name = self.station_name_col
        else:
            index_cols = line_profile.index.names.copy()
            index_cols.remove(self.lk_fnode_col)
            index_cols = [self.station_name_col] + index_cols
            line_profile = line_profile.reset_index()
            line_profile[self.station_name_col] = stns
            line_profile = line_profile.set_index(index_cols)
            line_profile.index.names = index_cols
            line_profile = line_profile.drop(self.lk_fnode_col, axis=1)
        return line_profile 


    def summarize_transit_segments(
            self, 
            summary: str,
            *,
            filter_expression: str | None = None,
            node_aggregation: Type[SpatialAggregator] | None = None,
            crosstab_columns: str | list[str] | None = None
        ) -> float | pd.DataFrame:
        """ 
        Summarizes an expression over a transit segment table. Summaries
        are always output for the transit period.

        Can optionally choose to:
        - apply arbitrary filters.
        - apply geographical aggregations
        - include crosstab columns, in which case the expression is summarized 
          for each segment. 

        Arguments:
            expression: 
            summary: str:
                summary: One of 'vkt', 'vht', 'pkt', 'pht', or a custom 
                expression
            filter_expression: 
                Defines transit segment filter using expression that will be  
                evaluatated using pandas.eval. If None then no filter is 
                applied. Link, transit line and transit segment and transit 
                vehicle attributes can be specified. Default is None.
            node_aggregation: 
                Spatial aggregation applied to nodes. All segment attributes
                are aggregated at the I-node. If None, then values from all 
                segments are summarized together. Default is None.
            crosstab_columns: 
                If None, will compute a single value per spatial aggregation
                area. Otherwise will segment calculations by defined columns.
                Default is None.

        """
        def test_attrs_in_expr_or_filter(expression, filter_expression, cols):
            return (self._test_attrs_in_expression(expression, cols) or 
                self._test_attrs_in_expression(filter_expression, cols))

        # Lookup the expression
        if summary == 'vkt':
            expression = self.transit_vkt_expr
        elif summary == 'vht':
            expression = self.transit_vht_expr
        elif summary == 'pkt':
            expression = self.transit_pkt_expr
        elif summary == 'pht':
            expression = self.transit_pht_expr
        else:
            expression = summary

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
        if isinstance(node_aggregation, SpatialAggregator) \
                and self.is_hypernetwork:
            raise RuntimeError(
                'Cannot perform transit summaries with node aggregations on a '
                'hypernetwork. Collapse network before running summary.')

        # Merge in required tables to the transit segments
        tsegs = self.tsegments.reset_index()
        if reqs_links_columns:
            tsegs = tsegs.merge(
                self.links, 
                left_on=[self.lk_fnode_col, self.lk_tnode_col], 
                right_index=True
            )
        if reqs_tlines_columns or reqs_tvehs_columns:
            tsegs = tsegs.merge(
                self.tlines, left_on=[self.tl_line_col], 
                right_index=True, suffixes=['', '_l'])
            if reqs_tvehs_columns:
                tsegs = tsegs.merge(
                    self.tvehicles, left_on=[self.tv_veh_col], 
                    right_index=True, suffixes=['', '_v'])
                
        # Apply filter if defined
        tsegs[self.fltr_colname] = True
        if isinstance(filter_expression, str):
            tsegs[self.fltr_colname] = \
                tsegs.eval(filter_expression).astype(bool)
        tsegs = tsegs.loc[tsegs[self.fltr_colname]]
        #Evalulate expression
        tsegs[self.expr_colname] = tsegs.eval(expression)   

        if not isinstance(node_aggregation, SpatialAggregator):
            if crosstab_columns is None:
                # This is the simple case, no spatial aggregation   
                return tsegs[self.expr_colname].sum()
            else:
                aggregation_columns = crosstab_columns
        else:
            # Merge in geographic segmentation
            aggregation_columns = []
            aggr_colname = node_aggregation.mapping.name
            nodes = self.nodes.merge(
                node_aggregation.mapping, how="inner", 
                left_index=True, right_index=True)
            tsegs = tsegs.merge(
                nodes[[aggr_colname]], 
                left_on=self.lk_fnode_col, 
                right_index=True
            )
            if crosstab_columns is None:
                aggregation_columns = [aggr_colname]
            elif isinstance(crosstab_columns, str):
                aggregation_columns = [aggr_colname] + [crosstab_columns]
            else:
                aggregation_columns = [aggr_colname] + crosstab_columns
        return tsegs.groupby(
            aggregation_columns)[self.expr_colname].sum()      


    def _test_if_hypernetwork(self) -> bool:
        """ Look for overlapping links, indicating this is a hypernetwork. """
        links = self.links.reset_index()   
        links = links.merge(
            self.nodes[['x', 'y']], 
            how='left', 
            left_on=self.lk_fnode_col, 
            right_index=True)
        links = links.merge(
            self.nodes[['x', 'y']], 
            how='left', 
            left_on=self.lk_tnode_col, 
            right_index=True, 
            suffixes=['_i', '_j']
        )
        n_links = links.groupby(['x_i', 'y_i', 'x_j', 'y_j'])[
            self.lk_fnode_col].count()
        n_links.name = 'n_links'
        if n_links.max() > 1:
            return True
        else:
            return False

    def _read_station_names_file(self) -> pd.Series | None:
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
            aggregation_rules:
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
        fromnode_col = self.lk_fnode_col
        tonode_col = self.lk_tnode_col
        base_fromnode_col = self.base_fnode_col
        base_tonode_col = self.base_tnode_col
        nodeid_col = self.ndid_col
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
            aggr_rules: dict, df_cols: pd.Index, results_cols: list | None,
        ) -> dict:
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

    def _create_aggregation_dictionary(self, agg_rules: dict | None) -> dict:
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
                self.lk_autovol_col, self.lk_addvolume_col])
        return agg_rules

    def _collapse_links(
            self, links: pd.DataFrame, agrls: dict) -> pd.DataFrame:
        """ Produces collapsed link table.  """
        fltr = links[self.base_fnode_col] != links[self.base_tnode_col]
        links2 = links.loc[fltr].groupby(
            [self.base_fnode_col, self.base_tnode_col]).aggregate(agrls)
        links2.index.names = self.links.index.names
        return gpd.GeoDataFrame(
            links2, geometry=self.geometry_col, crs=self.network_crs)
    
    def _collapse_nodes(
            self, node_mappings: pd.Series, agrls: dict) -> pd.DataFrame:
        """ Produces collapsed node table. """
        nodes = self.nodes.reset_index()
        nodes['new_node'] = nodes[self.ndid_col].map(node_mappings)
        nodes2 = nodes.groupby('new_node').aggregate(agrls)
        nodes2.index.name = self.nodes.index.name
        return gpd.GeoDataFrame(
            nodes2, geometry=self.geometry_col, crs=self.network_crs)
    
    def _collapse_tsegments(self, node_mappings: pd.Series) -> pd.DataFrame:
        """ Produces transit segment table using collapsed links.  
        
        Note that this function involves simply swapping out the base network
        node ids, switching the links to the base network links. 
        
        """
        tsegments = self.tsegments.reset_index()
        tsegments[self.lk_fnode_col] = \
            tsegments[self.lk_fnode_col].map(node_mappings)
        tsegments[self.lk_tnode_col] = \
            tsegments[self.lk_tnode_col].map(node_mappings)
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
        fromnode_col = self.lk_fnode_col
        tonode_col = self.lk_tnode_col
        base_fromnode_col = self.base_fnode_col
        base_tonode_col = self.base_tnode_col
        nodeid_col = self.ndid_col

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
        fltr = self.node_ranges.mapping != 'Hypernetwork nodes'
        non_hypntwk_nodes = self.node_ranges.mapping.loc[fltr]
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
                'merged in links to base_network links merge. ' \
                'This could be due to an incorrect hyper-network node range ' \
                'in the config file.')
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
    def _test_attrs_in_expression(expr: str | None, attributes: list):
        """ Check if attributes are in an expression. """
        if expr is None:
            return False
        for attr in attributes:
            if attr in expr:
                return True
        return False


#region properties

    @property
    def lane_length_expr(self) -> str:
        return f'{self.lk_len_col} * {self.lk_nlanes_col}'

    @property
    def traffic_vkt_expr(self) -> str:
        return f'{self.lk_len_col} * {self.lk_totvol_col}'

    @property
    def traffic_vht_expr(self) -> str:
        return f'{self.lk_autottime_col} * {self.lk_totvol_col} / 60.0'

    @property
    def vcr_extr(self) -> str:
        return f'{self.lk_totvol_col} / {self.lk_autocap_col}'

    @property
    def transit_vkt_expr(self) -> str:
        if self.start_time is None or self.end_time is None:
            raise ValueError(
                'Network period start and end times must be defined to '
                'calculated transit VKT.'
                )
        return f'{self.lk_len_col} * ' \
               f'({self.end_time} - {self.start_time}) / ' \
               f'{self.tl_hdw_col}'

    @property
    def transit_vht_expr(self) -> str:
        raise NotImplementedError(
            'Cannot calculate transit VHT as transit travel time not ' \
            'currently exported by TMG export_network_package tool.'
        )

    @property
    def transit_pkt_expr(self) -> str:
        # Volumes are already peak-period
        return f'{self.lk_len_col} * {self.ts_vol_col}'

    @property
    def transit_pht_expr(self) -> str:
        raise NotImplementedError(
            'Cannot calculate transit PHT as transit travel time not ' \
            'currently exported by TMG export_network_package tool.'
        )

    @property
    def is_hypernetwork(self) -> bool:
        return self._test_if_hypernetwork()

#endregion

