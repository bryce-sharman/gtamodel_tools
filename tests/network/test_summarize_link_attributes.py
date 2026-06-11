""" Tests for gtamodel_tools.network.network.summarize_link_attributes. """

import numpy as np

#region Different expressions and include_connectors
def test_summarize_linkattrs_length_1(am_auto_network):
    """ Test total link length, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('length', True)
    ref_result = am_auto_network.links['length'].sum()
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_length_2(am_auto_network):
    """ Test total link length without connectors, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('length', False)
    links = am_auto_network.links.copy()
    fltr = links['link_class'] != 'connector'
    links = links.loc[fltr]
    ref_result = links['length'].sum()
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_lanekm_1(am_auto_network):
    """ Test total lane-kms, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('lane_length', True)
    ref_result = (
        am_auto_network.links['length'] * am_auto_network.links['lanes']
    ).sum()
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_lanekm_2(am_auto_network):
    """ Test total lane-kms without connectors, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('lane_length', False)
    links = am_auto_network.links.copy()
    fltr = links['link_class'] != 'connector'
    links = links.loc[fltr]
    ref_result = (links['length'] * links['lanes']).sum()
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_vkt_1(am_auto_network):
    """ Test total VKT, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('vkt', True)
    ref_result = (
        am_auto_network.links['length'] * (
                am_auto_network.links['auto_volume'] + 
                am_auto_network.links['additional_volume']
            )
    ).sum()
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_vkt_2(am_auto_network):
    """ Test total VKT without connectors, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('vkt', False)
    links = am_auto_network.links.copy()
    fltr = links['link_class'] != 'connector'
    links = links.loc[fltr]
    ref_result = (
        links['length'] * (links['auto_volume'] + links['additional_volume'])
    ).sum()
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_vht_1(am_auto_network):
    """ Test total VHT, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('vht', True)
    ref_result = (
        am_auto_network.links['auto_time'] * (
                am_auto_network.links['auto_volume'] + 
                am_auto_network.links['additional_volume']
            )
    ).sum() / 60.0
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_vht_2(am_auto_network):
    """ Test total VHT without connectors, no segmentation and no filters."""
    test_result = am_auto_network.summarize_link_attributes('vht', False)
    links = am_auto_network.links.copy()
    fltr = links['link_class'] != 'connector'
    links = links.loc[fltr]
    ref_result = (
        links['auto_time'] * (links['auto_volume'] + links['additional_volume'])
    ).sum() / 60.0
    assert np.isclose(test_result, ref_result)
#endregion

#region additional attributes
def test_summarize_linkattrs_fltr(am_auto_network):
    """ Test a link filter, in this case vdf == 1.

    This result should match the result for include_connectors=False.
    """
    test_result = am_auto_network.summarize_link_attributes(
        'vht', True, filter_expression='vdf==1')
    ref_result = am_auto_network.summarize_link_attributes(
        'vht', False)
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_congested_threshold(am_auto_network):
    """ Test a link filter, in this case vdf == 1.

    This result should match the result for include_connectors=False.
    """
    test_result = am_auto_network.summarize_link_attributes(
        'vht', True, congested_threshold=0.3)
    links = am_auto_network.links.copy()
    links['vcr'] = (
            links['auto_volume'] + links['additional_volume']
        ) / links['auto_capacity']
    links = links.loc[links['vcr'] >= 0.3]
    ref_result = (
        links['auto_time'] * (links['auto_volume'] + links['additional_volume'])
    ).sum() / 60.0
    assert np.isclose(test_result, ref_result)


def test_summarize_linkattrs_nodeaggr_1(
        am_auto_network, sa_1lvl_regnodes_str):
    """ Testing spatial aggregation -- default test. """
    test_result = am_auto_network.summarize_link_attributes(
        'length', True, node_aggregation=sa_1lvl_regnodes_str
    )

    nodes = am_auto_network.nodes.copy()
    links = am_auto_network.links.copy()
    nodes['sz'] = nodes.index.get_level_values(0).map(
        sa_1lvl_regnodes_str.mapping)
    links['sz'] = links.index.get_level_values(0).map(nodes['sz'])
    ref_result = links.groupby('sz')['length'].sum()
    assert np.allclose(test_result, ref_result)


def test_summarize_linkattrs_nodeaggr_2(
        am_auto_network, sa_1lvl_regnodes_str):
    """ Testing spatial aggregation -- default specifies i_node. """
    test_result = am_auto_network.summarize_link_attributes(
        'length', True, node_aggregation=sa_1lvl_regnodes_str,
        aggregate_on_node='inode'
    )
    ref_result = am_auto_network.summarize_link_attributes(
        'length', True, node_aggregation=sa_1lvl_regnodes_str
    )
    assert np.allclose(test_result, ref_result)


def test_summarize_linkattrs_nodeaggr_3(
        am_auto_network, sa_1lvl_regnodes_str):
    """ Testing spatial aggregation -- test using j-node. """
    test_result = am_auto_network.summarize_link_attributes(
        'length', True, node_aggregation=sa_1lvl_regnodes_str,
        aggregate_on_node='inode'
    )
    nodes = am_auto_network.nodes.copy()
    links = am_auto_network.links.copy()
    nodes['sz'] = nodes.index.get_level_values(0).map(
        sa_1lvl_regnodes_str.mapping)
    links['sz'] = links.index.get_level_values(1).map(nodes['sz'])
    ref_result = links.groupby('sz')['length'].sum()
    assert np.allclose(test_result, ref_result)


def test_summarize_linkattrs_segmentlinkclass_1(am_auto_network):
    """ Testing link-class segmentation """
    test_result = am_auto_network.summarize_link_attributes(
        'length', True, segment_by_linkclass=True
    )
    links = am_auto_network.links.copy()
    ref_result = links.groupby('link_class')['length'].sum()
    print(test_result)
    assert np.allclose(test_result, ref_result)
