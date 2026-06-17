""" Tests for gtamodel_tools.network.network.summarize_transit_across_screenlines. """

from copy import deepcopy
import pandas as pd
from pathlib import Path
import pytest


@pytest.fixture
def screenlines_path(testdata_path) -> Path:
    return testdata_path / "Screenlines" / "Screenlines.shp"


@pytest.fixture
def expected() -> pd.DataFrame:
    # I'd really rather not hard-code these test results, maybe
    # change this later to something a bit more maintainable.
    # Note that I have manually checked this test result.
    mi = pd.MultiIndex.from_arrays(
        [
            ['EW', 'EW', 'NS', 'NS', 
             'NS', 'NS', 'NS2', 'NS2', 
             'X',  'X', 'X',  'X'
            ],
            ['NB', 'SB', 'EB', 'EB', 
             'WB', 'WB', 'EB', 'WB', 
             'EB', 'EB', 'WB', 'WB'
            ],
            ['b', 'b', 'b', 'l', 
             'b', 'l', 'b', 'b',
             'b', 'l', 'b', 'l'
            ]

        ],
        names=['screenline', 'dir', 'mode']
    )
    return pd.DataFrame(
        index=mi,
        columns=[
            'n_routes', 'capacity', 'volume'
        ],
        data=[
            [2, 1800.0, 0.0],
            [2, 1800.0, 100.0],
            [3, 3060.0, 58.333],
            [1, 3000.0, 41.667],
            [3, 3060.0, 0.0],
            [1, 3000.0, 0.0],
            [4, 3600.0, 100.0],
            [4, 3600.0, 100.0],
            [3, 3060.0, 58.333],
            [1, 3000.0, 41.667],
            [3, 3060.0, 0.0],
            [1, 3000.0, 0.0],
        ],
    )


def test_transit_across_screenlines(
        am_transit_network, screenlines_path, expected):
    """ Test transit across screenlines. """
    
    test_res = am_transit_network.summarize_transit_across_screenlines(
        screenlines_path, 'Name')
    ref_res = expected.copy()
    ref_res['vcr'] = ref_res['volume'] / ref_res['capacity']
    pd.testing.assert_frame_equal(test_res, ref_res, check_names=False)


def test_transit_across_screenlines_nocap(
        am_transit_network, screenlines_path, expected):
    """ Test transit across screenlines. """
    net = deepcopy(am_transit_network)
    net.start_time = None
    test_res = net.summarize_transit_across_screenlines(
        screenlines_path, 'Name')
    test_res.to_clipboard()
    ref_res = expected.copy()
    ref_res = ref_res.drop('capacity', axis=1)
    pd.testing.assert_frame_equal(test_res, ref_res, check_names=False)
