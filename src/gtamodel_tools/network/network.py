""" 
Module to read Emme network from network packages, and offer low-level
analysis tools called from other tools in this package.

Network packages are a development of the TravelModellingGroup at the 
University of Toronto that extends Emme's text output to include 
assignment results.
 
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import geopandas as gpd
from math import fabs
import numpy as np
from os import environ, PathLike
import pandas as pd
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Hashable, Self, Type


from gtamodel_tools.common.gis import calc_linestring_orientation
import gtamodel_tools.common.spatial_aggregator as sa
import gtamodel_tools.enums.validation.traffic.traffic as en_traffic

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
        coding_standard: str
            Currently must be one of ['ncs11', 'ncs16', 'ncs22'], but it is
            anticipated to add more in the future.
        has_traffic_results: bool
            True if network includes traffic results
        has_transit_results: bool
            True if network includes transit results

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
        self.coding_standard = coding_standard
        self.crs = en_ntcs.CRS
        self.grid_offset = en_ntcs.GRID_OFFSET
        self.link_dir_col = 'link_dir'

        self.min_regnode_id = en_ntcs.MIN_REGNODE_ID
        self.auto_mode = en_ntcs.AUTO_MODE
        self.length = en_ntcs.LENGTH_COL
        self.modes = en_ntcs.MODES_COL
        self.type = en_ntcs.TYPE_COL
        self.lanes = en_ntcs.LANES_COL
        self.ffspd = en_ntcs.FFSPD_COL
        self.lanecap = en_ntcs.LANECAP_COL
        self.linkclass = 'link_class'
        self.linkclass_exprs = en_ntcs.LINK_CLASSIFICATION_EXPRS

        self.nodes = nodes
        self.links = links
        self.tvehicles = tvehicles
        self.tlines = tlines
        self.tsegments = tsegments
        self.transit_operator_regexpr = en_ntcs.TRANSIT_OPERATOR_REGEXPR

        self.apply_link_classification()
        self.calculate_link_direction()
        self.apply_transit_operator()
        self.toperator = "operator"

        self.has_traffic_results = has_traffic_results
        self.autovol = en_ntcs.AUTOVOL_COL
        self.autoaddvol = en_ntcs.AUTOADDVOL_COL
        self.trafficvol = 'traffic_volume'
        self.trafficvol_expr = en_ntcs.TRAFFIC_VOL
        self.autotime = en_ntcs.AUTOTIME_COL
        self.traffic_results = en_ntcs.TRAFFIC_RESULTS_COLNAMES
        self.has_transit_results = has_transit_results
        self.transit_results = en_ntcs.TRANSIT_RESULTS_COLNAMES
        self.transit_boardings = en_ntcs.TRBOARDINGS_COL
        self.transit_alightings = en_ntcs.TRALIGHTINGS_COL
        self.transit_volume = en_ntcs.TRVOLUME
        
        if self.has_traffic_results:
            self.links[self.trafficvol] = self.links.eval(self.trafficvol_expr)
            
        self.err_msg_not_hypernetwork = \
            "This method cannot be run on a hypernetwork."
        self.err_msg_no_traffic_results = \
            "Network with traffic results required."
        self.err_msg_no_transit_results = \
            "Network with transit results required."
        self.expr_colname = '_eval_'
        self.fltr_colname = '_filtered_'

        self.zone_ranges = sa.create_spatial_aggregator(
            'custom_ranges', 
            ranges=en_ntcs.ZONE_RANGES,
            ids=self.nodes.loc[self.nodes['is_centroid']].index,
            name='zone_regions'
        )
        self.node_ranges = sa.create_spatial_aggregator(
            'custom_ranges', 
            ranges=en_ntcs.NODE_RANGES,
            ids=self.nodes.index,
            name='zone_regions'
        )          

    def apply_link_classification(self):
        """ 
        Add link classification column, as defined in network coding standard
        to links table. 
        """
        self.links[self.linkclass] = ''
        for k, v in self.linkclass_exprs.items():
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

    def filter_link_connectors(self):
        """ Returns copy of links table with connectors removed"""
        fltr_inode_is_cntrd = self.links.index.get_level_values(
            'inode').isin(self.zone_ranges().index)
        fltr_jnode_is_cntrd = self.links.index.get_level_values(
            'jnode').isin(self.zone_ranges().index)
        return self.links.loc[
            (~fltr_inode_is_cntrd) & (~fltr_jnode_is_cntrd)].copy()

    def apply_transit_operator(self):
        """ 
        Apply the operator regex, defined in the enumeration,to append
        the transit operator to the transit lines and transit segments tables.
        """
        tlines_index = self.tlines.index
        tsegments_index = self.tsegments.index.get_level_values(0)
        self.tlines['operator'] = ''
        self.tsegments['operator'] = ''
        for operator, regex_expr in self.transit_operator_regexpr.items():
            fltr = tlines_index.str.match(regex_expr)
            self.tlines.loc[fltr, 'operator'] = operator
            fltr = tsegments_index.str.match(regex_expr)
            self.tsegments.loc[fltr, 'operator'] = operator

#region Auto traffic summary methods
    def summarize_link_attributes(
            self,
            summary: str,
            include_connectors: bool=False,
            *,
            filter_expression: str | None = None,
            congested_threshold: float | None = None,
            node_aggregation: Type[sa.SpatialAggregator] | None = None,
            aggregate_on_node: str='inode',
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
            aggregate_on_node: Must be defined if node_aggregation is defined.
                Used to define if node aggregation is defined using 
                I-node ('inode')  or J-node ('jnode').  Default is 'inode'
            segment_by_linkclass: bool
                If True, additionally segment VKT by link classification.
        """
        # Lookup the expression
        if summary == 'length':
            expression = self.length
        elif summary == 'lane_length':
            expression = f'{self.length} * {self.lanes}'
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
            if aggregate_on_node not in ['inode', 'jnode']:
                raise ValueError("Invalid parameter 'aggregate_on_node'.")
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
        linkcap_col = 'link_cap'
        screenlines = screenlines.to_crs(self.links.crs)

        # Filter out the connectors
        links = self.filter_link_connectors()

        # Remove non-auto-links
        fltr = links['modes'].str.contains(self.auto_mode)
        links = links.loc[fltr]
        # Calculate lane capacity
        links[linkcap_col] = links.eval(f'{self.lanes} * {self.lanecap}')
        summary_columns = ['n_links', 'n_lanes', 'capacity']
        # Set the aggregation dictionary, which will be used in the 
        # .groupby command
        aggr_dict = {
            self.lanes: ['count', 'sum'], # of links and number of lanes
            linkcap_col: 'sum',           # vehicle capacity
        }
        if self.has_traffic_results:
            aggr_dict[self.autovol] = 'sum'
            aggr_dict[self.autoaddvol] = 'sum'
            aggr_dict[self.trafficvol] = 'sum'
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

#region Auto validation
    def prepare_trafficvol_expr(
            self, vol_to_compare: str, phf: float | None) -> str:
        """ 
        Convert vol_to_compare to an expression that can be run in pandas.eval.
        
        Args:
            vol_to_compare: one of 'auto', 'total', or an expression
                using link attributes.
            phf: peak-hour factor used by model to convert period to
                peak-hour demand. If not specified then a peak-hour
                validation is performed (equivalent to phf = 1.0).
        
        """
        if isinstance(phf, float) or isinstance(phf, int):
            phf_inv = 1.0 / phf
        else:
            phf_inv = 1.0
        
        if vol_to_compare == 'total':
            compare_expr = self.trafficvol
        elif vol_to_compare == 'auto':
            compare_expr = self.autovol
        else:
            compare_expr = vol_to_compare
        return f'({compare_expr}) * {phf_inv}'

    def match_links_to_auto_count_stations(
            self, stns: gpd.GeoDataFrame) -> None:
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
            self.modes].str.contains(self.auto_mode)
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

    def save_link_auto_cntstation_mappings(self, fp: PathLike) -> None:
        """ Output link mappings to csv file. 
        
        Args:
            fp: File in which to save link mappings
        """
        fltr = self.links['source'] != ''
        self.links.loc[
                fltr, 
                [en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR]
            ].to_csv(fp)

    def read_and_apply_link_auto_cntstation_mappings(
            self, fp: PathLike) -> None:
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

    def prepare_link_validation_table(
            self, 
            counts: pd.Series, 
            vol_to_compare: str,
            phf: float | None = None, 
        ) -> pd.DataFrame:
        """ Prepare a table comparing link volumes vs period traffic counts.

        Links must be matched to count stations before running this method.

        Args:
            counts: pd.Series containing traffic counts against which,
                the modelled volumes are to be compared. 
            vol_to_compare: one of 'auto', 'total', or an expression
                using link attributes.
            phf: peak-hour factor used by model to convert period to
                peak-hour demand. If not specified then a peak-hour
                validation is performed (equivalent to phf = 1.0).
                
        Returns:
            links pandas DataFrame with the following columns:
                - link class
                - traffic count source
                - traffic count direction
                - count volume in column 'count_vol'
                - model volume in column 'model_vol'

        """
        modelvol_attr = 'model_vol'
        vdtnvol_attr = 'count_vol'
        compare_expr = self.prepare_trafficvol_expr(vol_to_compare, phf)
            
        links = self.links.copy()
        # Calculate modelled volume
        links[modelvol_attr] = links.eval(compare_expr)  
        # Merge in count volume
        counts = counts.copy()
        counts.name = vdtnvol_attr
        links = links.merge(
            counts,
            left_on=[en_traffic.SOURCE, en_traffic.STN_ID, en_traffic.DIR],
            right_index=True
        )
        return links[[self.linkclass, en_traffic.SOURCE, en_traffic.DIR, 
                    modelvol_attr, vdtnvol_attr]]

    def validate_traffic_across_screenlines(
            self,
            screenlines: gpd.GeoSeries,
            comparisons: Dict,
        ) -> pd.DataFrame:
        """ Summarize traffic volumes and capacity across screenlines:
    
        Args:
            screenlines: gpd.GeoSeries with one row per screenline.
                Index is considered as the screenline name while
                the geometry defines the screenline.
            comparisons: Dict
                - key is the comparison name
                - the value is another dictionary defined as follows:
                    model_volumes: str 
                        Can be one of:
                        - 'auto': auto volumes only
                        - 'total': total volumnes, or 
                        - an expression using link attributes.
                    counts: pd.Series
                        Traffic counts against which, the modelled volumes 
                        are to be compared.
                    phf: float | None
                        peak-hour factor used by model to convert period to
                        peak-hour demand. If not specified then a peak-hour
                        validation is performed (equivalent to phf = 1.0).
        Returns:
            pd.DataFrame
                Outputs one row per combination of screenline and direction
                that contains the following:
                - n_links: number of links in direction
                - n_lanes: total number of lanes crossing screenline
                - capacity: total link capacity crossing screenline
                - modelled_vol: modelled volume on all links
                - n_obsv_links: number of links with counts
                - n_obsv_lanes: number of lanes on links with counts
                - link_porosity: proportion of observed links
                - lane_porosity: proportion of observed lanes
                - capacity_porosity: proportion of observed link capacity
                - count: traffic counts on observed links
                - obsv_modelled_vol: modelled volume on observed links

    
        """
        linkcap_col = 'link_cap'
        is_cntstn_col = 'is_cnt_stn'
        model_vol_col = 'model_vol'
        screenlines = screenlines.to_crs(self.links.crs)
        for k_cmp, v_cmp in comparisons.items():
            if 'phf' not in v_cmp.keys():
                comparisons[k_cmp]['phf'] = None

        # Prepare links table
        links = self.links
        links[linkcap_col] = links.eval(f'{self.lanes} * {self.lanecap}')
        links[is_cntstn_col] = 0
        links.loc[links[en_traffic.SOURCE] != '', is_cntstn_col] = 1
        fltr_inode_is_cntrd = \
            links.index.get_level_values('inode') < self.min_regnode_id
        fltr_jnode_is_cntrd = \
            links.index.get_level_values('jnode') < self.min_regnode_id
        links = links.loc[(~fltr_inode_is_cntrd) & (~fltr_jnode_is_cntrd)]
        results_list = []
        for scrn_idx, scrn_row in screenlines.iterrows():
            if 'index_right' in links.columns:
                links = links.drop('index_right', axis=1)
            screenline_gdf = gpd.GeoDataFrame(
                geometry=[scrn_row.geometry],
                index=[scrn_idx],
                crs=screenlines.crs
            )
            links2 = links.sjoin(screenline_gdf)

            for k_cmp, v_cmp in comparisons.items():
                counts_col = f'{k_cmp}_counts'
                modelvol_eval_str = self.prepare_trafficvol_expr(
                    v_cmp['model_volumes'], v_cmp['phf'])
                links2[model_vol_col] = links2.eval(modelvol_eval_str)
                # Merge in the counts
                counts = v_cmp['counts']
                
                counts.name = counts_col
                links2 = links2.merge(
                    v_cmp['counts'], how='left', 
                    left_on=en_traffic.STN_INDEX_COLS, right_index=True,
                )
                all = links2.groupby(self.link_dir_col).agg({
                    self.lanes: ['count', 'sum'], 
                    linkcap_col: 'sum',
                    model_vol_col: 'sum'
                })
                all.columns = ['n_links', 'n_lanes', 'capacity', 'modelled_vol']
                
                obsv_fltr = links2[en_traffic.SOURCE] != ''
                links_obsv = links2.loc[obsv_fltr]
                obsvd = links_obsv.groupby(self.link_dir_col).agg({
                    self.lanes: ['count', 'sum'], 
                    linkcap_col: 'sum',
                    counts_col: 'sum', 
                    model_vol_col: 'sum'
                })
                obsvd.columns = ['n_obsv_links', 'n_obsv_lanes', 'obsv_linkcap', 
                                 'count', 'obsv_modelled_vol']
                combined = pd.concat([all, obsvd], axis=1)
                combined['link_porosity'] = \
                    combined['n_obsv_links'] / combined['n_links']
                combined['lane_porosity'] = \
                    combined['n_obsv_lanes'] / combined['n_lanes']
                combined['capacity_porosity'] = \
                    combined['obsv_linkcap'] / combined['capacity']
                combined = combined.reset_index()
                combined['screenline'] = scrn_idx
                combined['comparison'] = k_cmp
                combined = combined.set_index(
                    ['screenline', 'link_dir', 'comparison']).fillna(0)
                results_list.append(combined)
                
        return pd.concat(results_list, axis=0)

    @staticmethod
    def _test_attrs_in_expression(expr: str | None, attributes: List):
        """ Check if attributes are in an expression. """
        if expr is None:
            return False
        for attr in attributes:
            if attr in expr:
                return True
        return False
#endregion
#region Transit


    def calc_line_profile(
            self, tline_ids: str|List[str], 
            stn_labels: pd.Series | Dict | None=None
        ) -> pd.DataFrame:
        """ 
        Calculate boardings, alightings and on-board riders along transit lines. 
        If multiple lines are defined, one line must be a shorter version of the 
        other line (This function cannot currently handle branching).
        
        Args:
            tline_id: str or List[str]
                Transit line id(s)
            stn_labels: pd.Series | Dict } None
                Optional mapping between node ID and station label.
                If None, then node IDs are returned, else maps in stop
                labels to node id. Default is None.

        Returns:
            pd.DataFrame
                - Index is the station label
                - Contains the following columns:
                    - boardings: Number of boardings at the station
                    - alightings: Number of alightings at the station
                    - volume: Passenger volume leaving the station
        """
        def _sum_results_for_multiple_lineprofiles(
                current, new, merge_type, suffixes):
            df = current.merge(
                new, how=merge_type, left_index=True, 
                right_index=True, suffixes=suffixes
            ).fillna(0)
            for col in self.transit_results:
                df[col] = df[col + suffixes[0]] + df[col + suffixes[1]]
                df = df.drop([col + suffixes[0], col + suffixes[1]], axis=1)
            return df
            
        suffixes=['_x', '_y']
        if isinstance(tline_ids, list) and len(tline_ids) == 1:
            tline_ids = tline_ids[0]
            
        # Case 1: single line
        if isinstance(tline_ids, str):
            tsegs = self._calc_line_profile_1line(tline_ids)
            return tsegs
        # Case 2: multiple lines
        tsegs_list = []
        for tline_id in tline_ids:
            tsegs_list.append(self._calc_line_profile_1line(tline_id))

        current = tsegs_list[0]
        for i in range(1, len(tline_ids)):
            new = tsegs_list[i]
            if current.index.equals(new.index):
                # Two lines have the exact same index
                current = _sum_results_for_multiple_lineprofiles(
                    current, new, 'inner', suffixes)
            else:
                current_minus_new = current.index.difference(new.index)
                new_minus_current = new.index.difference(current.index)
                if len(current_minus_new) > 0 and len(new_minus_current) == 0:
                    # new_tsegs is entirely within current_tsegs
                    current = _sum_results_for_multiple_lineprofiles(
                        current, new, 'left', suffixes)
                elif len(current_minus_new) == 0 and len(new_minus_current) > 0:
                    # Current is 
                    current = _sum_results_for_multiple_lineprofiles(
                        new, current, 'left', suffixes)
                else:
                    print('No transit line is a subset of the other, '
                        'Cannot create joint line profile. Returning None')
                    return None
        final = current
        if isinstance(stn_labels, pd.Series) or isinstance(stn_labels, dict):
            final = final.reset_index()
            final['stn'] = final['inode'].map(stn_labels)
            fltr = pd.isna(final['stn'])
            final.loc[fltr, 'stn'] = final.loc[fltr, 'inode']
            final = final.set_index(['stn', 'loop'])
            final = final.drop('inode', axis=1)
        return final

    def _calc_line_profile_1line(self, tline_id) -> pd.DataFrame:
        """ 
        Helper function to get the boardings, alightings and volume along 
        the line. 
        """
        if tline_id not in self.tlines.index:
            print(f'Transit line {tline_id} does not exist, returning None.')
            return None
        tsegs = self.tsegments.loc[
            idx[tline_id, :, :, :, :], self.transit_results]
        # add the hidden segment
        # all passengers onboard at the end on train must alight
        last_tseg = tsegs.iloc[-1]
        tsegs.loc[tline_id, last_tseg.name[2], 0, last_tseg.name[3]] = [
            0, last_tseg['volume'], 0]
        tsegs = tsegs.reset_index(['line', 'jnode'], drop=True)
        return tsegs

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
            expression, filter_expression, self.transit_results)
        reqs_traffic_results = test_attrs_in_expr_or_filter(
            expression, filter_expression, self.traffic_results)
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
                self.links, left_on=['inode', 'jnode'], right_index=True)
        if reqs_tlines_columns or reqs_tvehs_columns:
            # Transit vehicles are defined in the 'veh' transit line field
            tsegs = tsegs.merge(
                self.tlines, left_on=['line'], 
                right_index=True, suffixes=['', '_l'])
            if reqs_tvehs_columns:
                tsegs = tsegs.merge(
                    self.tvehicles, left_on=['veh'], 
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
        agrls = self._create_aggregation_dictionary(aggregation_rules)
        new_network = deepcopy(self)
        if not self.is_hypernetwork:
            return new_network

        # Create a working links table by identifying and merging in
        # base network nodes
        links = self._merge_link_basenodes()
        
        # Create node mapping from the working links table
        inode_mapping = links[['inode', 'base_inode']]
        inode_mapping .columns = ['node', 'base_node']
        jnode_mapping = links[['jnode', 'base_jnode']]
        jnode_mapping .columns = ['node', 'base_node']
        node_mappings = pd.concat([inode_mapping, jnode_mapping], axis=0)
        node_mappings = node_mappings.drop_duplicates().set_index(
            'node').squeeze().sort_index()
        
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
                'auto_volume', 'additional_volume'])
        return agg_rules

    def _collapse_links(
            self, links: pd.DataFrame, agrls: Dict) -> pd.DataFrame:
        """ Produces collapsed link table.  """
        fltr = links['base_inode'] != links['base_jnode']
        links2 = links.loc[fltr].groupby(
            ['base_inode', 'base_jnode']).aggregate(agrls)
        links2.index.names = self.links.index.names
        return links2
    
    def _collapse_nodes(
            self, node_mappings: pd.Series, agrls: Dict) -> pd.DataFrame:
        """ Produces collapsed node table. """
        nodes = self.nodes.reset_index()
        nodes['new_node'] = nodes['node'].map(node_mappings)
        nodes2 = nodes.groupby('new_node').aggregate(agrls)
        nodes2.index.name = self.nodes.index.name
        return nodes2
    
    def _collapse_tsegments(self, node_mappings: pd.Series) -> pd.DataFrame:
        """ Produces transit segment table using collapsed links.  
        
        Note that this function involves simply swapping out the base network
        node ids, switching the links to the base network links. 
        
        """
        tsegments = self.tsegments.reset_index()
        tsegments['inode'] = tsegments['inode'].map(node_mappings)
        tsegments['jnode'] = tsegments['jnode'].map(node_mappings)
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
        links = self.links.reset_index()   
        n_links_before_merge = len(links)
        links = links.merge(
            self.nodes[['x', 'y']], left_on='inode', right_index=True)
        links = links.merge(
            self.nodes[['x', 'y']], 
            left_on='jnode', 
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
            (links['inode'].isin(non_hypntwk_nodes)) & 
            (links['jnode'].isin(non_hypntwk_nodes))
        ]
        # Groupby X and Y coordinates
        base_links = base_links.groupby(['x_i', 'y_i', 'x_j', 'y_j'])[
            ['inode', 'jnode']].first()
        base_links.columns = ['base_inode', 'base_jnode']

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
            pd.isna(links['base_inode']) | pd.isna(links['base_jnode'])
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
        inodes = links[['inode', 'x_i', 'y_i']]
        inodes.columns = ['node_id', 'x', 'y']
        jnodes = links[['jnode', 'x_j', 'y_j']]
        jnodes.columns = ['node_id', 'x', 'y']
        tnodes = pd.concat([inodes, jnodes], axis=0)
        tnodes = tnodes.drop_duplicates()
        tnodes = tnodes.sort_values('node_id')
        # Identify base-network nodes
        base_tnodes = tnodes.loc[tnodes['node_id'].isin(non_hypntwk_nodes)]
        # Merge in the base transfer node by X and Y location
        tnodes2 = tnodes.merge(
            base_tnodes, how='left', on=['x', 'y'], suffixes=['', '_b'])
        tnodes2 = tnodes2.drop(['x', 'y'], axis=1).set_index(
            'node_id').squeeze()
        # Use a mapping to apply the base node (easier than a merge)
        links.loc[fltr_tlinks, 'base_inode'] = links.loc[
            fltr_tlinks, 'inode'].map(tnodes2)
        links.loc[fltr_tlinks, 'base_jnode'] = links.loc[
            fltr_tlinks, 'jnode'].map(tnodes2)

        # Now clean up the links table for all links
        links = links.drop(['x_i', 'y_i', 'x_j', 'y_j'], axis=1)
        links['base_inode'] = links['base_inode'].astype(np.uint32)
        links['base_jnode'] = links['base_jnode'].astype(np.uint32)
        return links
    
#endregion


#region Export to NWP
    # def to_nwp(self, fp: PathLike, header_comment_lines: List | None = None
    #     ) -> None:
    #     """ Export package to Emme-based NWP format. 
        
    #     Args:
    #         fp: PathLike
    #             Filepath of exported .NWP file
    #         header_comment_lines:
    #             A list of comments to be added as headers to all 
    #             Emme transactation files. Max 78 characters per entry.
            
    #     """
        
    #     # Find the Windows temp directory, clear if it already exists
    #     temp_dir = Path(environ['TMP']) / 'GTAModel_Tools'
    #     if temp_dir.exists():
    #         rmtree(temp_dir)
    #     temp_dir.mkdir()
        
    #     self._write_base_network(temp_dir / 'base.211', header_comment_lines)
    #     pass

    # def _prepare_node_base_output(node: pd.Series):
    #     pass

    # def _write_base_network(
    #     self, fp: PathLike, header_comment_lines: List | None = None) -> None:
    #     with open(fp, 'w') as f:
    #         f.write('c Emme Modeller - Base Network Transaction')
    #         f.write('')
    #         if hcl is not None:
    #             for hcl in header_comment_lines:
    #                 f.write(f'c {hcl}')
    #             f.write('')
    #         f.write('t nodes')
    #         f.write('c   Node          X-coord          Y-coord   Data1   Data2   Data3 Label')
    #         for 
#endregion




#region properties

    @property
    def traffic_vkt_expr(self) -> str:
        return f'{self.length} * {self.trafficvol}'

    @property
    def traffic_vht_expr(self) -> str:
        return f'{self.autotime} * {self.trafficvol} / 60.0'

    @property
    def vcr_extr(self) -> str:
        return f'{self.trafficvol} / ({self.lanes} * {self.lanecap})'

    @property
    def transit_vkt_expr(self) -> str:
        return f'{self.length} * {self.transit_volume}'

    @property
    def is_hypernetwork(self) -> bool:
        return self._test_if_hypernetwork()

#endregion