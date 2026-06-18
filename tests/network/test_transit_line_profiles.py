""" Tests for network.Network.calculate_line_profiles and related methods. """

from copy import deepcopy
import pandas as pd
import pandas.testing as tm
import pytest


@pytest.fixture
def stn_labels() -> pd.Series:
    return pd.Series(
        index=pd.Index([103, 104, 105], name='stn'),
        data=['X', 'Y', 'B']
    )

@pytest.fixture
def ref_black_profile_no_stns() -> pd.DataFrame:
    mi = pd.MultiIndex.from_arrays(
        [
            [104, 105],
            [1, 1]
        ],
        names=['inode', 'loop']
    )
    return pd.DataFrame(
        index=mi,
        columns=['boardings', 'alightings', 'volume'],
        data=[
            [41.667, 0, 41.667],
            [0, 41.667, 0],
        ]
    )

@pytest.fixture
def ref_blue_profile_no_stns() -> pd.DataFrame:
    mi = pd.MultiIndex.from_arrays(
        [
            [103, 104, 105],
            [1, 1, 1]
        ],
        names=['inode', 'loop']
    )
    return pd.DataFrame(
        index=mi,
        columns=['boardings', 'alightings', 'volume'],
        data=[
            [0, 0, 0],
            [8.333, 0, 8.333],
            [0, 8.333, 0],
        ]
    )

@pytest.fixture
def ref_blueblack_profile_no_stns() -> pd.DataFrame:
    return pd.DataFrame(
        index=pd.Index([103, 104, 105], name='inode'),
        columns=['boardings', 'alightings', 'volume'],
        data=[
            [0, 0, 0],
            [50.0, 0, 50.0],
            [0, 50.0, 0],
        ]
    )


@pytest.fixture
def ref_blueblack_profile_wstns() -> pd.DataFrame:
    return pd.DataFrame(
        index=pd.Index(['X', 'Y', 'B'], name='stn'),
        columns=['boardings', 'alightings', 'volume'],
        data=[
            [0, 0, 0],
            [50.0, 0, 50.0],
            [0, 50.0, 0],
        ]
    )


def test_calc_line_profile_black_nostns(
        am_transit_network, ref_black_profile_no_stns):
    net = deepcopy(am_transit_network)
    test_res = net.calc_line_profile_1line('Black')
    tm.assert_frame_equal(test_res, ref_black_profile_no_stns)


def test_calc_line_profile_blue_nostns(
        am_transit_network, ref_blue_profile_no_stns):
    net = deepcopy(am_transit_network)
    test_res = net.calc_line_profile_1line('Blue')
    tm.assert_frame_equal(test_res, ref_blue_profile_no_stns)


def test_calc_line_profile_blueblack_nostns(
        am_transit_network, ref_blueblack_profile_no_stns):
    net = deepcopy(am_transit_network)
    test_res = net.calc_line_profile(['Blue', 'Black'])
    tm.assert_frame_equal(test_res, ref_blueblack_profile_no_stns)


def test_calc_line_profile_blueblack_wstns(
        am_transit_network, ref_blueblack_profile_wstns, stn_labels):
    test_res = am_transit_network.calc_line_profile(
        ['Blue', 'Black'], stn_labels)
    tm.assert_frame_equal(test_res, ref_blueblack_profile_wstns)