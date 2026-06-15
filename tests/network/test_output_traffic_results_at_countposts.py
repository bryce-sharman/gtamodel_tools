""" Tests for gtamodel_tools.network.network.output_traffic_results_at_countposts. """

from copy import deepcopy
import numpy as np
import pandas as pd
import pytest


def test_traffic_at_countposts_undefined(am_auto_network):
    net = deepcopy(am_auto_network)
    net.traffic_countposts = None  # Remove defined countposts
    with pytest.raises(RuntimeError, match='No traffic countposts'):
        net.output_traffic_results_at_countposts()


def test_traffic_at_countposts(am_auto_network):
    test_results = am_auto_network.output_traffic_results_at_countposts()

    mi = pd.MultiIndex.from_arrays(
            [
                ['link_103_104', 'link_103_104', 'link_104_105', 'link_104_105',
                 'link_101_103', 'link_101_103', 'link_105_214', 'link_105_214'
                ],
                ['EB', 'WB', 'WB', 'EB', 'SB', 'NB', 'NB', 'SB']
            ],
            names=['countpost',	'link_dir']
    )
    # I'd really rather not hard-code these test results, maybe
    # change this later to something a bit more maintainable.
    ref_results = pd.DataFrame(
        index=mi,
        columns=[
            'auto_volume', 'additional_volume', 'traffic_volume', 
            'auto_capacity', 'vcr'
        ],
        data = [
            [100, 0.0, 100, 500, 0.2], 
            [0.0, 0.0, 0.0, 500, 0.0], 
            [0.0, 0.0, 0.0, 500, 0.0], 
            [100, 0.0, 100, 500, 0.2], 
            [200, 0.0, 200, 500, 0.4], 
            [0.0, 0.0, 0.0, 500, 0.0], 
            [0.0, 0.0, 0.0, 1000, 0.0], 
            [0.0, 0.0, 0.0, 1000, 0.0] 
        ],
        dtype=np.float64
    )
    pd.testing.assert_frame_equal(test_results, ref_results)


def test_traffic_at_countposts_incl_invld(am_auto_network):
    """ Traffic countposts, increase distance to include invalid point. """
    with pytest.raises(
                RuntimeError, 
                match='Links were connected to multiple countposts.'
            ):
        test_results = am_auto_network.output_traffic_results_at_countposts(
            max_distance=1500.0
        )

