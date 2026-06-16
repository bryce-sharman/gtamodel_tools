""" Tests for network.summarize_transit_segments. """

from copy import deepcopy
import numpy as np
import pandas.testing as tm
import pytest


def test_summarize_length(am_transit_network):
    """ 
    Test that summarizes the length of all transit segments with no filters
    or segmentation.
    """
    test_res = am_transit_network.summarize_transit_segments('length')
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    ref_res = tsegsm['length'].sum()
    assert np.isclose(test_res, ref_res)


def test_summarize_vkt_nostartendtimes(am_transit_network):
    """
    Test that summarizes the vehicle kilometers travelled of all transit
    segments, when network start-end times are not defined.
    """
    net = deepcopy(am_transit_network)
    net.start_time = None
    with pytest.raises(
            ValueError, 
            match='Network period start and end times must be defined'
        ):
        test_res = net.summarize_transit_segments('vkt')

    net = deepcopy(am_transit_network)
    net.end_time = None
    with pytest.raises(
            ValueError, 
            match='Network period start and end times must be defined'
        ):
        test_res = net.summarize_transit_segments('vkt')


def test_summarize_vkt(am_transit_network):
    """
    Test that summarizes the vehicle kilometers travelled of all transit
    segments with no filters or segmentation. 
    """
    net = deepcopy(am_transit_network)
    test_res = net.summarize_transit_segments('vkt')
    tsegsm = net.tsegments.reset_index(
        ).merge(
            net.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    t_hdw = net.tlines[['headway']]
    l_length = net.links[['length']]
    tsegsm = net.tsegments.reset_index().merge(
            l_length, left_on=['inode', 'jnode'], right_index=True).merge(
                t_hdw, left_on='line', right_index=True)
    tsegsm['nvehs'] = (net.end_time - net.start_time) / tsegsm['headway']
    ref_res = (tsegsm['nvehs'] * tsegsm['length']).sum()
    assert np.isclose(test_res, ref_res)


def test_summarize_vht(am_transit_network):
    """
    Test that summarizes the vehicle hours travelled of all transit
    segments with no filters or segmentation. 
    """
    with pytest.raises(
            NotImplementedError, 
            match='Cannot calculate transit VHT.'):
        am_transit_network.summarize_transit_segments('vht')
                

def test_summarize_pht(am_transit_network):
    """
    Test that summarizes the passenger hours travelled of all transit
    segments with no filters or segmentation. 
    """
    with pytest.raises(
            NotImplementedError, 
            match='Cannot calculate transit PHT.'):
        am_transit_network.summarize_transit_segments('pht')


def test_summarize_pkt(am_transit_network):
    """
    Test that summarizes the passenger kilometers travelled of all transit
    segments with no filters or segmentation. 
    """
    test_res = am_transit_network.summarize_transit_segments('pkt')
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    ref_res = (tsegsm['volume'] * tsegsm['length']).sum()
    assert np.isclose(test_res, ref_res)


def test_summarize_pkt_linkfilter(am_transit_network):
    """
    Test that summarizes the passenger kilometers travelled of all transit
    segments with link filter, no segmentation. 
    """
    test_res = am_transit_network.summarize_transit_segments(
        'pkt', filter_expression='length >= 1.0')
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    tsegsm = tsegsm.loc[tsegsm['length'] >= 1.0]
    ref_res = (tsegsm['volume'] * tsegsm['length']).sum()
    assert np.isclose(test_res, ref_res)


def test_summarize_pkt_segmentfilter(am_transit_network):
    """
    Test that summarizes the passenger kilometers travelled of all transit
    segments with transit segment filter, no segmentation. 
    """
    test_res = am_transit_network.summarize_transit_segments(
        'pkt', filter_expression='volume >= 50.0')
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    tsegsm = tsegsm.loc[tsegsm['volume'] >= 50.0]
    ref_res = (tsegsm['volume'] * tsegsm['length']).sum()
    assert np.isclose(test_res, ref_res)


def test_summarize_pkt_nodeaggr(am_transit_network, sa_1lvl_regnodes_str):
    """
    Test that summarizes the passenger kilometers travelled of all transit
    segments with no filter, node aggregation to superzones. 
    """
    test_res = am_transit_network.summarize_transit_segments(
        'pkt', node_aggregation=sa_1lvl_regnodes_str)
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    tsegsm['sz'] = tsegsm['inode'].map(sa_1lvl_regnodes_str.mapping)
    tsegsm['pkt'] = tsegsm['volume'] * tsegsm['length']
    ref_res = tsegsm.groupby('sz')['pkt'].sum()
    tm.assert_series_equal(test_res, ref_res, check_names=False)


def test_summarize_pkt_crosstab(am_transit_network):
    """
    Test that summarizes the passenger kilometers travelled of all transit
    segments with no filter or node aggregation, with crosstab column.
    """
    test_res = am_transit_network.summarize_transit_segments(
        'pkt', crosstab_columns=['operator'])
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    tsegsm['pkt'] = tsegsm['volume'] * tsegsm['length']
    ref_res = tsegsm.groupby('operator')['pkt'].sum()
    tm.assert_series_equal(test_res, ref_res, check_names=False)


def test_summarize_pkt_nodeaggr_crosstab(
        am_transit_network, sa_1lvl_regnodes_str):
    """
    Test that summarizes the passenger kilometers travelled of all transit
    segments with no filter, node aggregation to superzones and crosstab column.
    """
    test_res = am_transit_network.summarize_transit_segments(
        'pkt', 
        node_aggregation=sa_1lvl_regnodes_str, 
        crosstab_columns=['operator']
    )
    tsegsm = am_transit_network.tsegments.reset_index(
        ).merge(
            am_transit_network.links, 
            left_on=['inode', 'jnode'], 
            right_index=True
        )
    tsegsm['sz'] = tsegsm['inode'].map(sa_1lvl_regnodes_str.mapping)
    tsegsm['pkt'] = tsegsm['volume'] * tsegsm['length']
    ref_res = tsegsm.groupby(['sz', 'operator'])['pkt'].sum()
    tm.assert_series_equal(test_res, ref_res, check_names=False)
