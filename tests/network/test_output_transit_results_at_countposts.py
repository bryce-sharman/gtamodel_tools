""" Tests for network.output_transit_results_at_countposts. """

from copy import deepcopy
import pandas as pd
import pandas.testing as tm
import pytest

@pytest.fixture
def expected() -> pd.DataFrame:
    # This test result has been manually verified
    mi = pd.MultiIndex.from_arrays(
        [
            ['link_103_104', 'link_103_104', 'link_104_105', 'link_104_105', 
            'link_101_103', 'link_101_103', 'link_105_214', 'link_105_214'],
            ['EB', 'WB', 'WB', 'EB', 'SB', 'NB', 'NB', 'SB']
        ],
        names=['countpost', 'link_dir']
    )
    return pd.DataFrame(
        index=mi,
        columns=['volume', 'capacity'],
        data=[
            [50.0, 1260.0],
            [0.0, 1260.0],
            [0.0, 3960.0],
            [50.0, 3960.0],
            [50.0, 900.0],
            [0.0, 900.0],
            [0.0, 900.0],
            [50.0, 900.0],
        ]
    )


def test_transit_at_countposts_undefined(am_transit_network):
    net = deepcopy(am_transit_network)
    net.transit_countposts = None  # Remove defined countposts
    with pytest.raises(RuntimeError, match='No transit countposts'):
        net.output_transit_results_at_countposts()


def test_transit_at_countposts_no_transitphf(am_transit_network, expected):
    test_res = am_transit_network.output_transit_results_at_countposts()
    ref_res = expected.copy()
    ref_res['vcr'] = ref_res['volume'] / ref_res['capacity']
    tm.assert_frame_equal(test_res, ref_res)
