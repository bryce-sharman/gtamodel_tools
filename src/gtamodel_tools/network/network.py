""" 
Module to read Emme network from network packages, and offer low-level
analysis tools called from other tools in this package.

Network packages are a development of the TravelModellingGroup at the 
University of Toronto that extends Emme's text output to include 
assignment results.

The code in this module is based on the premise developed by WSP Canada
to read Emme network stored in .nwp format directly into Python, and
their initial code to do this task.
 
"""

from __future__ import annotations

from copy import deepcopy
import geopandas as gpd
from math import fabs
import numpy as np
from os import PathLike
import pandas as pd
from pandas.api.types import is_string_dtype
from pathlib import Path
import re
from typing import Callable, List, Hashable, Self, Tuple, Type, Union
import zipfile

from gtamodel_tools.common.gis import calc_linestring_orientation
import gtamodel_tools.common.spatial_aggregator as sa
import gtamodel_tools.enums.validation.traffic.traffic as en_traffic

ERR_MSG_NOT_HYPERNETWORK = "This method cannot be run on a hypernetwork."
ERR_MSG_TRAFFIC_RESULTS = "Network with traffic results required."
ERR_MSG_TRANSIT_RESULTS = "Network with transit results required."
TRAFFIC_RESULTS_COLNAMES = ['auto_volume', 'additional_volume', 'auto_time']
TRANSIT_RESULTS_COLNAMES  = ['boardings', 'alightings', 'volume']
EXPR_COLNAME = '_eval_'
FLTR_COLNAME = '_filtered_'

idx = pd.IndexSlice

class Network(object):
    """ 
    Stores Emme network, optionally including results, and includes low-level
    summary methods.

    Parameters:
        nodes: gpd.GeoDataFrame
            Node definitions including attributes and Point geometry
        links: gpd.GeomDataFrame
            Link definitions including attributes and LineString geometry
        tvehicles: pd.DataFrame
            Transit vehicle definitions
        tlines: pd.DataFrame
            Transit line definitions
        tsegments: pd.DataFrame,
            Transit segment definitions
        crs: str
            Projection string in which network is coded.
        network_coding_standard: str
            Currently must be one of ['ncs11', 'ncs16', 'ncs22'], but it is
            anticipated to add more in the future.
        has_traffic_results: bool
            True if network includes traffic results
        has_transit_results: bool
            True if network includes transit results


    Attributes:
        nodes: pd.DataFrame
            Table of network nodes, including attributes
        links: pd.DataFrame
            Table of network links, including attributes and traffic results
        tvehicles: pd.DataFrame
            Table of transit vehicles
        tlines: pd.DataFrame
            Table of transit lines
        tsegments: pd.DataFrame
            Table of transit segments
        has_traffic_results: bool
            True if network includes traffic results
        has_transit_results: bool
            True if network includes transit results
        is_hypernetwork: bool
            True if network is a hypernetwork.

    Methods:
        collapse_hypernetwork:
            Creates an equivalent network to a hyper-transit network
            collapsing to an equivalent 'regular' (non-hyper) network.
        summarize_link_attrs:
            Summarize link expression including traffic assignment attributes 
            over links with optional filters, geographic and attribute
            segmentation.
        summarize_transit_segments:
            Summarize transit segment expression over with optional filters, 
            geographic and attribute segmentation. The transit segment
            expression can include link, transit line, transit vehicle and 
            transit assignment result attributes.
        summarize_link_attrs_along_screenlines:
            Summarizes link expression over screenlines.

    """

    def __init__(
            self, 
            nodes: gpd.GeoDataFrame,
            links: gpd.GeomDataFrame,
            tvehicles: pd.DataFrame,
            tlines: pd.DataFrame,
            tsegments: pd.DataFrame,
            coding_standard: str,
            has_traffic_results: bool,
            has_transit_results: bool
        ) -> None:
        # Define columns as per coding standard
        if coding_standard == 'ncs11':
            import gtamodel_tools.enums.network.toronto_ncs11 as en_ntcs
        elif coding_standard == 'ncs16':
            import gtamodel_tools.enums.network.toronto_ncs16 as en_ntcs
        elif coding_standard == 'ncs22':
            import gtamodel_tools.enums.network.toronto_ncs22 as en_ntcs
        crs = en_ntcs.CRS
        self.nodes = nodes
        self.links = links
        self.tvehicles = tvehicles
        self.tlines = tlines
        self.tsegments = tsegments
        self.crs = crs
        self.coding_standard = coding_standard

        self.min_regnode_id = en_ntcs.MIN_REGNODE_ID
        self.auto_mode = en_ntcs.AUTO_MODE
        self.length_col = en_ntcs.LENGTH_COL
        self.modes_col = en_ntcs.MODES_COL
        self.type_col = en_ntcs.TYPE_COL
        self.lanes_col = en_ntcs.LANES_COL
        self.vdf_col = en_ntcs.VDF_COL
        self.ffspd_col = en_ntcs.FFSPD_COL
        self.lanecap_col = en_ntcs.LANECAP_COL
        if has_traffic_results:
            self.has_traffic_results = has_traffic_results
            self.autovol_col = en_ntcs.AUTOVOL_COL
            self.autoaddvol_col = en_ntcs.AUTOADDVOL_COL
            self.autotime_col = en_ntcs.AUTOTIME_COL
        if has_transit_results:
            self.has_transit_results = has_transit_results
        self.is_hypernetwork = self._test_if_hypernetwork()


    def match_links_to_count_stations(self, stns: gpd.GeoDataFrame) -> None:
        """ Modifies network links table by adding count stations.

        Args:
            stns: GeoPandas.GeoDataFrame
                Count stations

        """
        PT_MAXSPACING = 50
        BUFFER = 60   # metres
        N_PTS_COL = 'n_pts'
        N_INTSC_COL = 'n_intsc_pts'
        PR_INTSC_COL = 'prop_intsc'
        GEOM_COL = 'geometry'
        MAX_ORIENTATION_DELTA = 30
        
        # Add fields to the links table to hold the match station
        self.links[en_traffic.SOURCE] = ''
        self.links[en_traffic.STN_ID] = ''
        self.links[en_traffic.DIR] = ''
        
        # Limit to candidate links by using a sideways-only buffer
        # Create a table of links and candidate count stations
        fltr_hasautomode = self.links[
            self.modes_col].str.contains(self.auto_mode)
        fltr_not_connector = \
            (self.links.index.get_level_values(0) >= self.min_regnode_id) & \
            (self.links.index.get_level_values(1) >= self.min_regnode_id)
        road_links = self.links.loc[fltr_hasautomode & fltr_not_connector]
        stns2 = stns.to_crs(self.crs)
        stns_buffer_geom = stns2.geometry.buffer(BUFFER, cap_style='flat')
        stns_buffer = gpd.GeoDataFrame(stns2, geometry=stns_buffer_geom)
        candidate_matches = stns_buffer.sjoin(road_links, how='inner')
        candidate_matches = candidate_matches.rename({
            'index_right0': 'i', 'index_right1': 'j'}, axis=1)
        candidate_matches = candidate_matches[['i', 'j']].merge(
            road_links[[GEOM_COL]], left_on=['i', 'j'],right_index=True)
        candidate_matches = gpd.GeoDataFrame(
            candidate_matches, geometry=candidate_matches[GEOM_COL])
        candidate_match_stns = candidate_matches.index.unique()
        candidate_matches = candidate_matches.reset_index()
        candidate_matches = candidate_matches.set_index(
            [en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR, 'i', 'j'])
        candidate_matches = candidate_matches.sort_index()
        
        for cmstn in candidate_match_stns:
            # Get a buffer around the station
            stn_geom = stns2.at[cmstn, GEOM_COL]
            stn_buffer = stn_geom.buffer(BUFFER, cap_style='flat')

            # Search for points along each link that lie within buffer
            subset = candidate_matches.loc[idx[cmstn]].copy()
            subset[N_PTS_COL] = 0
            subset[N_INTSC_COL] = 0
            for sbt_i, sbt in subset.iterrows():
                vx, vy = sbt.geometry.segmentize(PT_MAXSPACING).xy
                seg_pts = gpd.points_from_xy(vx, vy)
                subset.at[sbt_i, N_PTS_COL] = len(seg_pts)
                subset.at[sbt_i, N_INTSC_COL] = seg_pts.intersects(
                    stn_buffer).sum()
            if subset[N_INTSC_COL].max() == 0:
                # No intersections found -- move on
                continue
            subset[PR_INTSC_COL] = subset[N_INTSC_COL] / subset[N_PTS_COL]
            max_prop_intsc = subset[PR_INTSC_COL].max()
            fltr_subset_max = (subset[PR_INTSC_COL] == max_prop_intsc)
            # Find the first entry with the same orientation
            stn_angle = calc_linestring_orientation(stn_geom, 0, 'angle')
            for sbt_i, sbt in subset.loc[fltr_subset_max].iterrows():
                lk_angle = calc_linestring_orientation(sbt.geometry, 0, 'angle')
                if fabs(lk_angle - stn_angle) < MAX_ORIENTATION_DELTA:
                    self.links.loc[
                        sbt_i, idx[en_traffic.SOURCE, en_traffic.STN_ID, 
                                   en_traffic.DIR]
                        ] = cmstn
                    break

    def save_link_cntstation_mappings(self, fp: PathLike) -> None:
        """ Output link mappings to csv file. 
        
        Args:
            fp: File in which to save link mappings
        """
        fltr = self.links['source'] != ''
        self.links.loc[
                fltr, 
                [en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR]
            ].to_csv(fp)


    def read_and_apply_link_mappings(self, fp: PathLike) -> None:
        """ 
        Read previously calculated link mappings from a file and apply to links.

        Args:
            fp: File from which to read link mappings
        """
        mappings = pd.read_csv(
            fp, index_col=self.links.index.names, dtype=str, na_values='')
        stn_mapping_cols = [en_traffic.SOURCE, en_traffic.STN_ID, 
                            en_traffic.DIR]
        for col in stn_mapping_cols:
            if col in self.links.columns:
                raise RuntimeError(
                    f'Cannot have {stn_mapping_cols} columns in links table '
                    f'before merging in count station mapping.'
                )
        self.links = self.links.merge(
            mappings, how='left', left_index=True, right_index=True)
        self.links[stn_mapping_cols] = self.links[stn_mapping_cols].fillna('')
    
    def summarize_link_attrs(
            self, 
            expression: str,
            include_connectors: bool,
            *,
            filter_expression: str | None = None,
            node_aggr: Type[sa.SpatialAggregator] | None = None,
            ij_aggr: str | None = 'ijnodes',
            crosstab_columns: str | List[str] | None = None
        ) -> float | pd.DataFrame:
        """ Summarizes an expression over a link table.

        Can optionally choose to:
        - include connectors
        - apply arbitrary filters.
        - apply geographical aggregations
        - include crosstab columns, in which case the expression is summarized 
            for each segment. 

        Arguments:
            expression: str
                Value to be aggregated. This is an expression that 
                will be evaluatated using pandas.eval.
            include_connectors: bool
                If True, includes connectors in summary calculations.
            filter_expression: str or None
                Optional expression to filter links. This is an expression that 
                will be evaluatated using pandas.eval. If used, expression must
                evaluate to either True or False. Default is None.
            node_aggr: sa.SpatialAggregator or None
                Optional node spatial aggregator. If defined, then the VKT will 
                be returned for each geographic segmentation.
                Default is None.
            ij_aggr: str or None
                Must be defined if node_aggr is defined. 
                If 'inode', link spatial aggregation is by the I-node.
                If 'jnode', link spatial aggregation is by the J-node,
                If 'ijnodes', link spatial aggregation is by both I-node and 
                    J-node. Links straddling aggregation regions will be 
                    included in a separate 'N/A' category.
                    Default is None.
            crosstab_columns: str or List[str] or None = None
                Optional input to specify segmentation by link attribute.
                Attribute must exist in the links table.

        Returns:
            float or pd.DataFrame
                If both node_aggr and crosstab_columns are None, then returns
                a float with summary calculation over entire level.
                Otherwise returns a pandas.DataFrame showing segmented summary.
        
        """
        if node_aggr is not None:
            if ij_aggr not in ['inode', 'jnode', 'ijnodes']:
                raise ValueError("Invalid parameter 'ij_aggr'.")
        # see if we need traffic results and don't have them.
        if not self.has_traffic_results:
            if self._test_attrs_in_expression(
                    expression, self.TRAFFIC_RESULTS_COLNAMES):
                raise RuntimeError(self.ERR_MSG_TRAFFIC_RESULTS)
            if self._test_attrs_in_expression(
                    filter_expression, self.TRAFFIC_RESULTS_COLNAMES):
                raise RuntimeError(self.ERR_MSG_TRAFFIC_RESULTS)

        links = self.links.copy()
        # Apply filters, including connectors
        links[self.FLTR_COLNAME] = True

        if filter_expression is None:
            links[self.FLTR_COLNAME] = True
        else:
            links[self.FLTR_COLNAME] = False
            fltr = links.eval(filter_expression).astype(bool)
            links.loc[fltr, self.FLTR_COLNAME] = True
            
        if include_connectors is False:
            links = self._filter_connectors_from_linktable(
                links, self.FLTR_COLNAME)
        #Evalulate expression
        links[self.EXPR_COLNAME] = links.eval(expression)       

        # This is the simple case, no geographic or attribute segmentation     
        if node_aggr is None and crosstab_columns is None:
            return links.loc[
                links[self.FLTR_COLNAME], self.EXPR_COLNAME].sum()
        # Apply geographic segmentation to nodes, merging to links as needed.
        if node_aggr is not None:
            aggr_colname = node_aggr().name
            nodes = self.nodes.merge(
                node_aggr(), how="inner", left_index=True, right_index=True)
            if ij_aggr in ['inode', 'ijnodes']:
                links = links.merge(
                    nodes[[aggr_colname]], left_on='inode', right_index=True)
            if ij_aggr in ['jnode', 'ijnodes']:
                links = links.merge(
                    nodes[[aggr_colname]], left_on='jnode', right_index=True,
                    suffixes=['_i', '_j'])
            if ij_aggr == 'ijnodes':
                # check for different node aggregations and set to 'N/A'
                # note that suffixes are applied in this case.
                links[aggr_colname] = 'N/A'
                fltr = links[aggr_colname + '_i'] == links[aggr_colname + '_j']
                links.loc[fltr, aggr_colname] = links.loc[
                    fltr, aggr_colname + '_i']
            # Now the geographical segmentation is prepared, treat
            # it the same as all others. 
            if crosstab_columns is None:
                crosstab_columns = [aggr_colname]
            elif isinstance(crosstab_columns, list):
                crosstab_columns = [aggr_colname] + crosstab_columns
            else:
                crosstab_columns=[aggr_colname, crosstab_columns]
        return links.loc[
            links[self.FLTR_COLNAME]].groupby(
                crosstab_columns)[self.EXPR_COLNAME].sum()       

    # def summarize_link_attrs_along_screenlines(
    #         self,
    #         expression: str,
    #         screenline_colname: str | list[str],
    #     ) -> pd.DataFrame:
    #     """ Summarize traffic volumes along a screenline.
        
    #     Arguments:
    #         expression: str
    #             Value to be aggregated. This is an expression that 
    #             will be evaluatated using pandas.eval.
    #         screenline_colname:
    #             Column in links table defining the screenline.
    #             Can be a single column name or a list of column names.
    #     Returns:
    #         pd.DataFrame
    #             Summary table of traffic volumes, by screenline

    #     """
    #     # see if we need traffic results and don't have them.
    #     if not self.has_traffic_results:
    #         if self._test_attrs_in_expression(
    #                 expression, self.TRAFFIC_RESULTS_COLNAMES):
    #             raise RuntimeError(self.ERR_MSG_TRAFFIC_RESULTS)

    #     #Evalulate expression
    #     links = self.links.copy()
    #     links[self.EXPR_COLNAME] = links.eval(expression)    
    #     # Groupby screenline attribute
    #     # Drop 0, as that will correspond to all links not on a screenline
    #     result = links.groupby(screenline_colname)[self.EXPR_COLNAME].sum()
    #     return result.drop(0, axis=0)
        

    def summarize_transit_segments(
            self, 
            expression: str,
            filter_expression: str | None = None,
            node_aggr: Type[sa.SpatialAggregator] | None = None,
            ij_aggr: str | None = 'ijnodes',
            crosstab_columns: str | List[str] | None = None
        ) -> float | pd.DataFrame:
        """ Summarizes an expression over a transit segment table.

        Can optionally choose to:
        - include connectors
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
                evaluatated using pandas.eval. If None then no link filter is 
                applied. Link, transit line and transit vehicle attributes can 
                also be used. Default is None.
            node_aggr: sa.SpatialAggregator or None
                Spatial aggregation applied to nodes
                If None, then all links are summarized together.
                Default is None.
            ij_aggr: str | None
                Must be defined if node_aggr is defined. One of 'i_node', 
                'j_node', 'ij_nodes'. If 'ij_nodes' is defined, then links
                straddling aggregation regions will be included in a 
                separate 'N/A' category.
            crosstab_columns: str | List[str] | None = None
                If None, will compute a single value per spatial aggregation
                area. Otherwise will segment calculations by defined columns.
                Default is None.

        """
        if self.is_hypernetwork:
            raise RuntimeError(self.ERR_MSG_NOT_HYPERNETWORK)
        # Look if traffic or transit results are required
        if not self.has_traffic_results:
            if self._test_attrs_in_expression(
                    expression, self.TRAFFIC_RESULTS_COLNAMES):
                raise RuntimeError(self.ERR_MSG_TRAFFIC_RESULTS)
        if not self.has_transit_results:
            if self._test_attrs_in_expression(
                    expression, self.TRANSIT_RESULTS_COLNAMES):
                raise RuntimeError(self.ERR_MSG_TRANSIT_RESULTS)
        if node_aggr is not None:
            if ij_aggr not in ['inode', 'jnode', 'ijnodes']:
                raise ValueError("Invalid parameter 'ij_aggr'.")
    
        # See if we need to merge in other tables
        # Don't merge if we don't have to improve performance
        tsegs = self.tsegments.reset_index()
        link_cols = self.links.columns
        if (self._test_attrs_in_expression(expression, link_cols) or 
                self._test_attrs_in_expression(filter_expression, link_cols)):
            tsegs = tsegs.merge(
                self.links, left_on=['inode', 'jnode'], right_index=True)
        tline_cols = self.tlines.columns
        if (self._test_attrs_in_expression(expression, tline_cols) or 
                self._test_attrs_in_expression(filter_expression, tline_cols)):
            tsegs = tsegs.merge(
                self.tlines, 
                left_on=['line'], 
                right_index=True, 
                suffixes=['', '_l']
            )
        tveh_cols = self.tvehicles.columns
        if (self._test_attrs_in_expression(expression, tveh_cols) or 
                self._test_attrs_in_expression(filter_expression, tveh_cols)
                ):
            # 'veh' comes from the merged in transit line
            tsegs = tsegs.merge(
                self.tvehicles, 
                left_on=['veh'], 
                right_index=True, 
                suffixes=['', '_v']
            )

        # Apply filter
        tsegs[self.FLTR_COLNAME] = True
        if filter_expression is not None:
            tsegs[self.FLTR_COLNAME] = tsegs.eval(
                filter_expression).astype(bool)

        #Evalulate expression
        tsegs[self.EXPR_COLNAME] = tsegs.eval(expression)     

        # This is the simple case, no geographic or attribute segmentation     
        if node_aggr is None and crosstab_columns is None:
            return tsegs.loc[
                tsegs[self.FLTR_COLNAME], self.EXPR_COLNAME].sum()
        # Apply geographic segmentation to nodes, merging to tsegs as needed.
        if node_aggr is not None:
            aggr_colname = node_aggr().name
            nodes = self.nodes.merge(
                node_aggr(), how="inner", left_index=True, right_index=True)
            if ij_aggr in ['inode', 'ijnodes']:
                tsegs = tsegs.merge(
                    nodes[[aggr_colname]], left_on='inode', right_index=True)
            if ij_aggr in ['jnode', 'ijnodes']:
                tsegs = tsegs.merge(
                    nodes[[aggr_colname]], left_on='jnode', right_index=True,
                    suffixes=['_i', '_j'])
            if ij_aggr in ['jnode', 'ijnodes']:
                tsegs = tsegs.merge(
                    nodes[[aggr_colname]], left_on='jnode', right_index=True,
                    suffixes=['_i', '_j'])
            if ij_aggr == 'ijnodes':
                # check for different node aggregations and set to 'N/A'
                # note that suffixes are applied in this case.
                tsegs[aggr_colname] = 'N/A'
                fltr = tsegs[aggr_colname + '_i'] == tsegs[aggr_colname + '_j']
                tsegs.loc[fltr, aggr_colname] = tsegs.loc[
                    fltr, aggr_colname + '_i']
            # Now the geographical segmentation is prepared, treat
            # it the same as all others. 
            if crosstab_columns is None:
                crosstab_columns = [aggr_colname]
            elif isinstance(crosstab_columns, list):
                crosstab_columns = [aggr_colname] + crosstab_columns
            else:
                crosstab_columns=[aggr_colname, crosstab_columns]
        return tsegs.loc[
            tsegs[self.FLTR_COLNAME]].groupby(
                crosstab_columns)[self.EXPR_COLNAME].sum()      

    def collapse_hypernetwork(
            self, aggregation_rules: dict) -> Self:
        """ Returns a new EmmeNetwork with equivalent single-layer network. 
        
        Arguments:
            aggregation_rules: dict
                Dictionary containing aggregration rules of extra
                attributes to apply when simplifying
                to a collapsed network. Expected keys include:'nodes', 'links',
                'transit_segments'.
                Under each key is another dictionary containing the attribute
                (or column) name and aggregation function to be applied 
                in a pandas.groupby.aggregate. See
                https://pandas.pydata.org/docs/reference/api/pandas.core.groupby.DataFrameGroupBy.aggregate.html
                Default is 'first'.

        Returns:
        EmmeNetwork:
            EmmeNetwork with collapsed hypernetwork.
    
        Notes:
            Transit lines do not appear to be modified in a hypernetwork, 
            we can leave unchanged.
        
        """
    
        # Complete the aggregation rules dictionary
        for key in ['nodes', 'links', 'transit_segments']:
            if key not in aggregation_rules:
                aggregation_rules[key] = {}
        aggregation_rules['nodes'] = self._complete_aggregation_dictionary(
            self.nodes, aggregation_rules['nodes'])
        aggregation_rules['links'] = self._complete_aggregation_dictionary(
            self.links, aggregation_rules['links'])
        aggregation_rules['transit_segments'] = \
            self._complete_aggregation_dictionary(
                self.tsegments, aggregation_rules['transit_segments'])
        if self.has_traffic_results:
            aggregation_rules['links']['auto_volume'] = 'sum'
            aggregation_rules['links']['additional_volume'] = 'sum'
            aggregation_rules['links']['auto_time'] = 'max'
        if self.has_transit_results:
            aggregation_rules['transit_segments']['boardings'] = 'sum'
            aggregation_rules['transit_segments']['alightings'] = 'sum'
            aggregation_rules['transit_segments']['volume'] = 'sum'
            
        
        new_network = deepcopy(self)
        if not self.is_hypernetwork:
            return new_network
    
        # Merge the base node into the links table and map hypernetwork nodes to 
        # base network nodes, this forms the basis of all following steps.
        links = self._merge_link_basenodes()
        hypntwk_node_mappings = self._find_hypernetwork_node_mapping(links)

        # Now collapse all the tables
        new_network.links = self._collapse_links(
            links, aggregation_rules['links'])
        new_network.nodes = self._collapse_nodes(
            hypntwk_node_mappings, aggregation_rules['nodes'])
        new_network.tsegments = self._collapse_tsegments(
            hypntwk_node_mappings, aggregation_rules['transit_segments'])
        new_network.is_hypernetwork = False
        return new_network

#endregion
#region Helper functions
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
    
    @staticmethod
    def _test_attrs_in_expression(expr: str | None, attributes: List):
        """ Check if attributes are in an expression. """
        if expr is None:
            return False
        for attr in attributes:
            if attr in expr:
                return True
        return False

    def _filter_connectors_from_linktable(
            self, 
            links: pd.DataFrame,
            filter_column
        ) -> pd.DataFrame:
        """ Filter connectors from provided link table. 
        
        Uses provided link table to allow more flexibility in 
        using this as part of larger calculations. 
        """
        has_ijnode_index=False
        if 'inode' in links.index.names:
            has_ijnode_index = True
            links = links.reset_index()
        links = links.merge(
            self.nodes[['is_centroid']],
            how="left",
            left_on='inode',
            right_index=True
        )
        links = links.merge(
            self.nodes[['is_centroid']],
            how="left",
            left_on='jnode',
            right_index=True,
            suffixes=['_i', '_j']
        )
        connector_fltr = (
            links['is_centroid_i'] != 0) | (links['is_centroid_j'] != 0)
        links.loc[connector_fltr, filter_column] = False
            
        # Reset index, if that's how the link table came in.
        if has_ijnode_index:
            links = links.set_index(['inode', 'jnode'])
        return links.drop(['is_centroid_i', 'is_centroid_j'], axis=1)

    def _collapse_tsegments(
        self,
            hypntwk_node_mappings: pd.Series, 
            aggregation_rules: dict, 
        ) -> pd.DataFrame:
        """ Creates new transit segment table collapsing results to base level.
    
        All transit segment are aggregated as per aggregation_rules argument.
    
        Arguments:
            hypntwk_node_mappings: pd.Series
                Mapping of hypernetwork nodes to base network nodes.
            aggregation_rules: dict
                Dictionary containing aggregration rules to apply when 
                simplifying to a collapsed network to be applied in a 
                pandas.groupby.aggregate. Must contain an entry for all columns. 
    
        Returns:
            pd.DataFrame
                Collapsed transit segment table.
        """
        tsegments = self.tsegments.reset_index()
        for orig_col, base_col in [
            ['inode','base_inode'], ['jnode', 'base_jnode']]:
            tsegments[base_col] = tsegments[orig_col].map(hypntwk_node_mappings)
            fltr = pd.isna(tsegments[base_col])
            tsegments.loc[fltr, base_col] = tsegments.loc[fltr, orig_col]
            tsegments[base_col] = tsegments[base_col].astype(np.int64)

        tsegments_final = tsegments.groupby(
            ['line', 'base_inode', 'base_jnode', 'loop']).aggregate(
                aggregation_rules)
        tsegments_final.index.names = ['line', 'inode', 'jnode', 'loop']
        # Revert to original column order
        tsegments_final = tsegments_final[self.tsegments.columns]
        return tsegments_final

    def _collapse_links(
            self, 
            links: pd.DataFrame, 
            aggregation_rules: dict
        ) -> pd.DataFrame:
        """Produces a new links table without the hypernetwork links.
        
        All link attributes are aggregated as per aggregation_rules argument.
    
        Arguments:
            links: pd.DataFrame
                Links table with the merged base nodes.
            aggregation_rules: dict
                Dictionary containing aggregration rules to apply when 
                simplifying to a collapsed network to be applied in a 
                pandas.groupby.aggregate. Must contain an entry for all columns. 
    
        Returns:
            pd.DataFrame
                modified links table
        
        """
        links2 = links.groupby(['base_inode', 'base_jnode']).aggregate(
            aggregation_rules)
        # Go back to the original column order
        links2 = links2[self.links.columns]
        links2.index.names = ['inode', 'jnode']
        return links2
    
    def _collapse_nodes(
            self, 
            hypntwk_node_mappings: pd.Series, 
            aggregation_rules: dict, 
        ) -> pd.DataFrame:
        """ Produces a new nodes table without the hypernetwork nodes.
    
        All node attributes are aggregated as per aggregation_rules argument.
    
        Arguments:
            hypntwk_node_mappings: pd.Series
                Mapping of hypernetwork nodes to base network nodes.
            aggregation_rules: dict
                Dictionary containing aggregration rules to apply when 
                simplifying to a collapsed network to be applied in a
                pandas.groupby.aggregate. Must contain an entry for all columns. 
    
        Returns:
            pd.DataFrame
                Collapsed node table
    
        """    
        nodes = self.nodes.reset_index()
        nodes['new_node'] = nodes['node'].map(hypntwk_node_mappings)
        fltr = pd.isna(nodes['new_node'])
        nodes.loc[fltr, 'new_node'] = nodes.loc[fltr, 'node']
        nodes['new_node'] = nodes['new_node'].astype(np.int64)
       
        nodes_final = nodes.groupby('new_node').aggregate(aggregation_rules)
        # Revert to original column order
        nodes_final = nodes_final[self.nodes.columns]
        return nodes_final
    
    def _merge_link_basenodes(self) -> pd.DataFrame:
        """ Merges base nodes for link i_nodes and j_nodes into links table. 
            
        Returns:
            pd.DataFrame
                Modified links table with added columnes of base_inode and 
                base_jnode. Note that the index is reset anticipate
                further operations on the returned links table.
            
        """
        links = self.links.reset_index()   
        links = links.merge(
            self.nodes[['x', 'y']], 
            how='left', 
            left_on='inode', 
            right_index=True
        )
        links = links.merge(
            self.nodes[['x', 'y']], 
            how='left', 
            left_on='jnode', 
            right_index=True, 
            suffixes=['_i', '_j']
        )
        # Get the base (non-hyper network) link
        # hypernetworks are always added at the end, so identify base using the minimum value
        base_link = links.groupby(['x_i', 'y_i', 'x_j', 'y_j'])[
            ['inode', 'jnode']].min()
        base_link.columns = ['base_inode', 'base_jnode']
        # Now merge in the base link and the number of links
        links = links.merge(
            base_link, left_on=['x_i', 'y_i', 'x_j', 'y_j'], right_index=True)
        links = links.drop(['x_i', 'y_i', 'x_j', 'y_j'], axis=1)
        return links
    
    def _find_hypernetwork_node_mapping(
            self, links_df: pd.DataFrame) -> pd.Series:
        """ From the links table, find all nodes that are hypernetwork nodes. 
    
        Arguments:
            links_df: pd.DataFrame
                Links table with the merged base nodes, 
                created by _merge_link_basenodes.
        
        Returns
            pd.Series
                Index is the node ID in the hypernetwork, value is the 
                corresponding base node ID.
            
        """
        # Get a list of the nodes to be removed from the final nodes file 
        # looking at both I nodes and J nodes.
        collapse_inodes = links_df.loc[
                links_df['inode'] != links_df['base_inode']
            ][['inode', 'base_inode']]
        collapse_inodes.columns = ['nodeid', 'base_nodeid']
        collapse_jnodes = links_df.loc[
                links_df['jnode'] != links_df['base_jnode']
            ][['jnode', 'base_jnode']]
        collapse_jnodes.columns = ['nodeid', 'base_nodeid']
        nodes_to_remove = pd.concat(
                [collapse_inodes, collapse_jnodes], 
                axis=0, 
                ignore_index=True
            ).drop_duplicates().set_index('nodeid').squeeze()
        nodes_to_remove.name = 'new_node'
        return nodes_to_remove
    
    def _complete_aggregation_dictionary(
            df: pd.DataFrame,
            aggregations: dict
        ) -> dict:
        """ Complete aggregation dictionary for all columns in a dataframe.
        
        Arguments:
            df: Dataframe for which to create the dictionary.
            aggregations: dict
                Original dictionary specifying aggregations in 
                GroupBy.aggregations function
    
        Returns:
            dict
                Modifified dictionary containing all columns. All entries
                not in the original dictionary are assigned 'first', which keeps
                the initial value (of least least the first entry) 
                during the aggregation.
        
        """
        for column in df.columns:
            if column not in aggregations:
                aggregations[column] = 'first'
        return aggregations



#endregion

