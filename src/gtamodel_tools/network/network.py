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
from math import fabs
import numpy as np
from os import PathLike
import pandas as pd
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
        if has_traffic_results:
            self.has_traffic_results = has_traffic_results
            self.autovol = en_ntcs.AUTOVOL_COL
            self.autoaddvol = en_ntcs.AUTOADDVOL_COL
            self.trafficvol = en_ntcs.TRAFFIC_VOL
            self.autotime = en_ntcs.AUTOTIME_COL
            self.traffic_results = en_ntcs.TRAFFIC_RESULTS_COLNAMES
        if has_transit_results:
            self.has_transit_results = has_transit_results
            self.transit_results = en_ntcs.TRANSIT_RESULTS_COLNAMES

        self.nodes = nodes
        self.links = links
        self.tvehicles = tvehicles
        self.tlines = tlines
        self.tsegments = tsegments

        self.err_msg_not_hypernetwork = "This method cannot be run on a hypernetwork."
        self.err_msg_no_traffic_results = "Network with traffic results required."
        self.err_msg_no_transit_results = "Network with transit results required."
        self.expr_colname = '_eval_'
        self.fltr_colname = '_filtered_'
        self.zone_ranges = en_ntcs.ZONE_RANGES
        self.node_ranges = en_ntcs.NODE_RANGES

        self.is_hypernetwork = self._test_if_hypernetwork()
        self.apply_link_classification()
        self.calculate_link_direction()


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

    def apply_link_classification(self):
        """ Add link classification column to links table. """
        self.links[self.linkclass] = ''
        for k, v in self.linkclass_exprs.items():
            fltr = self.links[v['attr']].isin(v['values'])
            self.links.loc[fltr, self.linkclass] = k  

    def calculate_link_direction(self) -> None:
        """ 
        Calculate link direction (NE, EB, SB, WB) based on node coordinates. 
        """
        self.links[self.link_dir_col] = self.links.apply(
            lambda x: calc_linestring_orientation(
                x['geometry'], self.grid_offset, 'cartesian'), axis=1)

    def summarize_links(
            self,
            summary: str,
            include_connectors: bool,
            *,
            filter_expression: str | None = None,
            congested_threshold: float | None = None,
            node_aggr: Type[sa.SpatialAggregator] | None = None,
            segment_by_linkclass: bool | None = None,
            **kwargs
        ):
        """ Calculate vehicle kilometers travelled.

        Arguments:
            include_connectors: Include VKT on connectors.
            summary: One of 'length', 'lane_length', 'vkt', 'vht'
                or a custom expression
            filter_expression: str or None
                Optional expression to filter links. This is an expression that 
                will be evaluatated using pandas.eval. If used, expression must
                evaluate to either True or False. Default is None. A congestion
                threshold filter is added on top of this expression using the
                congested_threshold parameter.
            congested_threshold: float or None
                If defined, will only calculate VKT on links whose volume/capacity
                ratio exceeds this treshold.
            node_aggr: Optional spatial aggregator. If defined will segment the VKT 
                by region. Default is None.
            segment_by_linkclass: bool
                If true, additionally segment VKT by link classification.
            kwargs: Additional arguments to be passed to _summarize_links
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
        if congested_threshold is not None:
            cong_fltr_expr = \
                f'{self.congested_filter_extr} > {congested_threshold}'
            if filter_expression is not None:
                filter_expression = f'{filter_expression} and {cong_fltr_expr}'
            else:
                filter_expression = cong_fltr_expr
        if segment_by_linkclass:  # add to cross_tabs kwargs argument
            if 'crosstab_columns' in kwargs:
                # Move crosstab columns out of kwargs to deal with 'officially'
                kw_crosstab = kwargs['crosstab_columns']
                if isinstance(kw_crosstab, Hashable):
                    kwargs['crosstab_columns'] = [kwargs['crosstab_columns']]
                kwargs['crosstab_columns'] = \
                    kwargs['crosstab_columns'] + [self.linkclass]
            else:
                kwargs['crosstab_columns'] = self.linkclass

        return self._summarize_links(
            expression=expression, 
            include_connectors=include_connectors, 
            filter_expression=filter_expression,
            node_aggr=node_aggr, 
            **kwargs
        )

    def _summarize_links(
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
                    expression, self.traffic_results):
                raise RuntimeError(self.err_msg_no_traffic_results)
            if self._test_attrs_in_expression(
                    filter_expression, self.traffic_results):
                raise RuntimeError(self.err_msg_no_traffic_results)

        links = self.links.copy()
        # Apply filters, start by including everything
        links[self.fltr_colname] = True
        if filter_expression is not None:
            fltr = links.eval(filter_expression).astype(bool)
            links.loc[~fltr, self.fltr_colname] = False
        if include_connectors is False:
            links = self._filter_connectors_from_linktable(
                links, self.fltr_colname)

        links[self.expr_colname] = links.eval(expression)       
        # This is the simple case, no geographic or attribute segmentation     
        if node_aggr is None and crosstab_columns is None:
            return links.loc[
                links[self.fltr_colname], self.expr_colname].sum()
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
            links[self.fltr_colname]].groupby(
                crosstab_columns)[self.expr_colname].sum()       

    def prepare_trafficvol_expr(self, vol_to_compare: str, phf: float) -> str:
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

    def summarize_traffic_across_screenlines(
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
                    expression, self.traffic_results):
                raise RuntimeError(self.ERR_MSG_TRAFFIC_RESULTS)
        if not self.has_transit_results:
            if self._test_attrs_in_expression(
                    expression, self.traffic_results):
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

#region properties

    @property
    def traffic_vkt_expr(self) -> str:
        return f'{self.length} * {self.trafficvol}'

    @property
    def traffic_vht_expr(self) -> str:
        return f'{self.autotime} * {self.trafficvol} / 60.0'

    @property
    def congested_filter_extr(self) -> str:
        return f'{self.trafficvol} / ({self.lanes} * {self.lanecap})'

#endregion