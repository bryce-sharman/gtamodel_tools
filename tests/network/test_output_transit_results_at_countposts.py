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
            ['link_103_104', 'link_103_104', 'link_104_105_b', 'link_104_105_b', 
            'link_104_105_l', 'link_104_105_l', 'link_101_103', 'link_101_103', 
            'link_105_214', 'link_105_214'],
            ['EB', 'WB', 'WB', 'EB', 'WB', 'EB', 'SB', 'NB', 'NB', 'SB']
        ],
        names=['countpost', 'link_dir']
    )
    return pd.DataFrame(
        index=mi,
        columns=['volume', 'capacity'],
        data=[
            [50.0, 1260.0],
            [0.0, 1260.0],
            [0.0, 2160.0],
            [8.333, 2160.0],
            [0.0, 3000.0],
            [41.667, 3000.0],
            [50.0, 900.0],
            [0.0, 900.0],
            [0.0, 900.0],
            [50.0, 900.0],
        ]
    )


def test_transit_at_countposts_undefined(am_transit_network):
    """ Test if transit countposts are not defined. """
    net = deepcopy(am_transit_network)
    net.transit_countposts = None  # Remove defined countposts
    with pytest.raises(RuntimeError, match='No transit countposts'):
        net.output_transit_results_at_countposts()


def test_transit_at_countposts(am_transit_network, expected):
    """ Test if network start/end times defined. """
    net = deepcopy(am_transit_network)
    test_res = net.output_transit_results_at_countposts()
    test_res.to_clipboard()
    ref_res = expected.copy()
    ref_res['vcr'] = ref_res['volume'] / ref_res['capacity']
    tm.assert_frame_equal(test_res, ref_res)

def test_transit_at_countposts_nocapacity(am_transit_network, expected):
    """ Test transit countposts if network start/end times not defined.
    
    Period-level capacaties cannot be computed in this case.
    """
    net = deepcopy(am_transit_network)
    net.start_time = None
    test_res = net.output_transit_results_at_countposts()
    ref_res = expected.copy()
    ref_res = ref_res.drop('capacity', axis=1)
    tm.assert_frame_equal(test_res, ref_res)


