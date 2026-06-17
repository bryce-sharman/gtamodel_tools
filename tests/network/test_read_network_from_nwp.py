""" Tests for gtamodel_tools.network.network.read_from_nwp. """

from copy import deepcopy
import pandas as pd
import pytest

from gtamodel_tools.network import Network

@pytest.fixture
def required_node_cols() -> list[str]:
    return [
        'x', 'y', 'data1', 'data2', 'data3', 'label', 'is_centroid', 'geometry'
    ]

@pytest.fixture
def required_link_cols() -> list[str]:
    return [
        'length', 'modes', 'type', 'lanes', 'vdf', 'ul1', 'ul2', 'ul3', 
        'geometry', 'auto_capacity', 'link_class', 'link_dir'
    ]

@pytest.fixture
def required_tvehicle_cols() -> list[str]:
    return [
        'description', 'mode', 'fleet_size', 'seated_capacity', 
        'total_capacity', 'cost_time_coeff', 'cost_distance_coeff', 
        'energy_time_coeff', 'energy_distance_coeff', 'auto_equivalent'
    ]

@pytest.fixture
def required_tlines_cols() -> list[str]:
    return [
        'mode', 'veh', 'headway', 'speed', 'description', 'ut1', 'ut2', 'ut3'
    ]

@pytest.fixture
def required_tsegment_cols() -> list[str]:
    return [
        'seg_seq', 'dwt', 'ttf', 'us1', 'us2', 'us3'
    ]


def _basic_nodes_tests(net, zone_ids, regnode_ids, required_cols):
    assert net.nodes is not None
    assert net.nodes.shape[0] == len(zone_ids) + len(regnode_ids)
    centroids = net.nodes.loc[net.nodes['is_centroid'] == True]
    assert centroids.shape[0] == len(zone_ids) 
    reg_nodes = net.nodes.loc[net.nodes['is_centroid'] == False]
    assert reg_nodes.shape[0] == len(regnode_ids)  
    required_node_colnames = pd.Index(required_cols)
    assert required_node_colnames.isin(net.nodes.columns).all()

def _basic_links_tests(net, required_cols):
    assert net.links is not None
    assert net.links.shape[0] > 0
    required_link_colnames = pd.Index(required_cols)
    assert required_link_colnames.isin(net.links.columns).all()
    assert net.links['link_dir'].isin(['NB', 'SB', 'EB', 'WB']).all()
    if net.link_cldefs is not None:
        assert net.links['link_class'].isin(
            net.link_cldefs.keys()).all()

def _basic_transit_tests(
        net, 
        required_tveh_cols, 
        required_tline_cols, 
        required_tseg_cols
    ):
    assert net.tvehicles is not None
    assert net.tvehicles.shape[0] > 0
    req_cols = pd.Index(required_tveh_cols)
    assert req_cols.isin(net.tvehicles.columns).all()

    assert net.tlines is not None
    assert net.tlines.shape[0] > 0
    req_cols = pd.Index(required_tline_cols)
    assert req_cols.isin(net.tlines.columns).all()

    assert net.tsegments is not None
    assert net.tsegments.shape[0] > 0
    req_cols = pd.Index(required_tseg_cols)
    assert req_cols.isin(net.tsegments.columns).all()


def test_read_road_network_from_nwp(
        am_auto_network,
        zone_ids, 
        regnode_ids, 
        required_node_cols, 
        required_link_cols
    ):
    net = deepcopy(am_auto_network)
    _basic_nodes_tests(net, zone_ids, regnode_ids, required_node_cols)
    _basic_links_tests(net, required_link_cols)


def test_read_transit_network_from_nwp(
        am_auto_network, 
        zone_ids, 
        regnode_ids, 
        required_node_cols, 
        required_link_cols,
        required_tvehicle_cols,  
        required_tlines_cols, 
        required_tsegment_cols
    ):
    net = deepcopy(am_auto_network)
    _basic_nodes_tests(net, zone_ids, regnode_ids, required_node_cols)
    _basic_links_tests(net, required_link_cols)
    _basic_transit_tests(
        net, required_tvehicle_cols, required_tlines_cols, 
        required_tsegment_cols
    )


def test_read_network_invalid_config_crs(test_auto_summary_config):
    c = deepcopy(test_auto_summary_config)
    c.network_crs = None
    net = Network(c)
    with pytest.raises(RuntimeError, match="Network CRS"):
        net.read_from_nwp(c.networks_subdir / 'AM_Auto.nwp')

def test_read_network_invalid_config_offset(test_auto_summary_config):
    c = deepcopy(test_auto_summary_config)
    c.grid_offset = None
    net = Network(c)
    with pytest.raises(RuntimeError, match="Grid offset"):
        net.read_from_nwp(c.networks_subdir / 'AM_Auto.nwp')

def test_read_network_invalid_config_autmode(test_auto_summary_config):
    c = deepcopy(test_auto_summary_config)
    c.automode_id = None
    net = Network(c)
    with pytest.raises(RuntimeError, match="Automode ID"):
        net.read_from_nwp(c.networks_subdir / 'AM_Auto.nwp')

def test_read_network_invalid_config_fflowspd(test_auto_summary_config):
    c = deepcopy(test_auto_summary_config)
    c.link_freeflow_speed_col = None
    net = Network(c)
    with pytest.raises(RuntimeError, match="Link freeflow speed"):
        net.read_from_nwp(c.networks_subdir / 'AM_Auto.nwp')

def test_read_network_invalid_config_lanecap(test_auto_summary_config):
    c = deepcopy(test_auto_summary_config)
    c.link_lane_capacity_col = None
    net = Network(c)
    with pytest.raises(RuntimeError, match="Link lane capacity"):
        net.read_from_nwp(c.networks_subdir / 'AM_Auto.nwp')
