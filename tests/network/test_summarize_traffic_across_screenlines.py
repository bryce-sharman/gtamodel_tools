""" Tests for gtamodel_tools.network.network.summarize_traffic_across_screenlines. """

import geopandas as gpd
import pandas as pd
from pathlib import Path
import pytest


@pytest.fixture
def screenlines_path(testdata_path) -> Path:
    return testdata_path / "Screenlines" / "Screenlines.shp"


def test_traffic_across_screenlines(am_auto_network, screenlines_path):
    """ Test traffic across screenlines. """
    
    test_res = am_auto_network.summarize_traffic_across_screenlines(
        screenlines_path, 'Name')
    test_res.to_clipboard()
    print(type(test_res))

    # I'd really rather not hard-code these test results, maybe
    # change this later to something a bit more maintainable.
    mi = pd.MultiIndex.from_arrays(
        [
            ['EW', 'EW', 'NS', 'NS', 'NS2', 'NS2', 'X',  'X'],
            ['EB', 'WB', 'NB', 'SB', 'EB', 'WB', 'EB', 'WB']
        ],
        names=['screenline', 'dir']
    )
    ref_res = pd.DataFrame(
        index=mi,
        columns=[
            'n_links', 'n_lanes', 'capacity', 'auto_vol', 
            'additional_vol', 'traffic_vol', 'vcr'
        ],
        data=[
            [2, 3.0, 1500.0, 100.0, 0.0, 100.0, 0.066667],
            [2, 3.0, 1500.0,   0.0, 0.0,   0.0, 0.0],
            [2, 3.0, 1500.0,   0.0, 0.0,   0.0, 0.0],
            [2, 3.0, 1500.0, 200.0, 0.0, 200.0, 0.133333],
            [4, 8.0, 4000.0,   0.0, 0.0,   0.0, 0.0],
            [4, 8.0, 4000.0,   0.0, 0.0,   0.0, 0.0],
            [2, 3.0, 1500.0, 100.0, 0.0, 100.0, 0.066667],
            [2, 3.0, 1500.0,   0.0, 0.0,   0.0, 0.0]
        ],
    )
    pd.testing.assert_frame_equal(test_res, ref_res, check_names=False)
