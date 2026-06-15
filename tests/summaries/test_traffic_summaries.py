""" Tests for gtamodel_tools.summaries.traffic_summaries.py.

These tests test the front end for the traffic summaries tools, which are
convenience functions around the network summary methods, which can 
accept multiple networks to produce daily summaries.

The network summary methods are tested separately. These tests only cover
the convenience functions, scaling by peak-hr factors and summarizing over
multiple networks (time periods).

"""

from copy import deepcopy
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

from gtamodel_tools.summaries.traffic_summaries import summarize_traffic_vkt
from gtamodel_tools.summaries.traffic_summaries import summarize_traffic_vht
from gtamodel_tools.summaries.traffic_summaries import summarize_traffic_across_screenlines


@pytest.fixture
def screenlines_path(testdata_path) -> Path:
    return testdata_path / "Screenlines" / "Screenlines.shp"


def test_summarize_vkt_am_noclasses_notscaled(am_auto_network):
    test_result = summarize_traffic_vkt(
        networks=am_auto_network
    )
    ref_result = am_auto_network.summarize_link_attributes(
        'vkt'
    )
    assert np.isclose(test_result, ref_result)


def test_summarize_vkt_am_noclasses_scaled(am_auto_network):
    test_result = summarize_traffic_vkt(
        networks =am_auto_network, 
        scale_by_auto_phf=True
    )
    ref_result = am_auto_network.summarize_link_attributes(
        'vkt'
    ) * am_auto_network.auto_phf
    assert np.isclose(test_result, ref_result)


def test_summarize_vkt_pm_noclasses_notscaled(pm_auto_network):
    test_result = summarize_traffic_vkt(
        networks=pm_auto_network
    )
    ref_result = pm_auto_network.summarize_link_attributes(
        'vkt'
    )
    assert np.isclose(test_result, ref_result)


def test_summarize_vkt_pm_noclasses_scaled(pm_auto_network):
    test_result = summarize_traffic_vkt(
        networks =pm_auto_network, 
        scale_by_auto_phf=True
    )
    ref_result = pm_auto_network.summarize_link_attributes(
        'vkt'
    ) * pm_auto_network.auto_phf
    assert np.isclose(test_result, ref_result)


def test_summarize_vkt_dly(am_auto_network, pm_auto_network):
    test_result = summarize_traffic_vkt(
        networks=[am_auto_network, pm_auto_network],
        scale_by_auto_phf=True
    )
    ref_result = \
        am_auto_network.summarize_link_attributes(
            'vkt') * am_auto_network.auto_phf + \
        pm_auto_network.summarize_link_attributes(
            'vkt') * pm_auto_network.auto_phf
    print(test_result, ref_result)
    assert np.isclose(test_result, ref_result)


def test_summarize_vkt_am_nopeakhrfactor(am_auto_network):
    net = deepcopy(am_auto_network)
    net.auto_phf = None
    with pytest.raises(
        RuntimeError, match='Auto peak-hour factor'):
        summarize_traffic_vkt(
            networks=net, scale_by_auto_phf=True)


def test_summarize_vht_am_noclasses_notscaled(am_auto_network):
    test_result = summarize_traffic_vht(
        networks=am_auto_network
    )
    ref_result = am_auto_network.summarize_link_attributes(
        'vht'
    )
    assert np.isclose(test_result, ref_result)


def test_summarize_vht_am_noclasses_scaled(am_auto_network):
    test_result = summarize_traffic_vht(
        networks =am_auto_network, 
        scale_by_auto_phf=True
    )
    ref_result = am_auto_network.summarize_link_attributes(
        'vht'
    ) * am_auto_network.auto_phf
    assert np.isclose(test_result, ref_result)


def test_summarize_vht_pm_noclasses_notscaled(pm_auto_network):
    test_result = summarize_traffic_vht(
        networks=pm_auto_network
    )
    ref_result = pm_auto_network.summarize_link_attributes(
        'vht'
    )
    assert np.isclose(test_result, ref_result)


def test_summarize_vht_pm_noclasses_scaled(pm_auto_network):
    test_result = summarize_traffic_vht(
        networks =pm_auto_network, 
        scale_by_auto_phf=True
    )
    ref_result = pm_auto_network.summarize_link_attributes(
        'vht'
    ) * pm_auto_network.auto_phf
    assert np.isclose(test_result, ref_result)


def test_summarize_vht_dly(am_auto_network, pm_auto_network):
    test_result = summarize_traffic_vht(
        networks=[am_auto_network, pm_auto_network],
        scale_by_auto_phf=True
    )
    ref_result = \
        am_auto_network.summarize_link_attributes(
            'vht') * am_auto_network.auto_phf + \
        pm_auto_network.summarize_link_attributes(
            'vht') * pm_auto_network.auto_phf
    print(test_result, ref_result)
    assert np.isclose(test_result, ref_result)


def test_summarize_vht_am_nopeakhrfactor(am_auto_network):
    net = deepcopy(am_auto_network)
    net.auto_phf = None
    with pytest.raises(RuntimeError, match='Auto peak-hour factor'):
        summarize_traffic_vht(
            networks=net, scale_by_auto_phf=True)


def test_summarize_screenlines_am(am_auto_network, screenlines_path):
    test_res = summarize_traffic_across_screenlines(
            am_auto_network, screenlines_path, 'Name', scale_by_auto_phf=False
        )
    ref_res = am_auto_network.summarize_traffic_across_screenlines(
        screenlines_path, 'Name', 
    )
    tm.assert_frame_equal(test_res, ref_res)


def test_summarize_screenlines_am_scaled(am_auto_network, screenlines_path):
    summary_results_cols = [
        'capacity', 'auto_vol', 'additional_vol', 'traffic_vol']
    test_res = summarize_traffic_across_screenlines(
            am_auto_network, screenlines_path, 'Name', scale_by_auto_phf=True
        )
    ref_res = am_auto_network.summarize_traffic_across_screenlines(
        screenlines_path, 'Name', 
    )
    ref_res[summary_results_cols] = \
        ref_res[summary_results_cols] * am_auto_network.auto_phf
    tm.assert_frame_equal(test_res, ref_res)


def test_summarize_screenlines_pm(pm_auto_network, screenlines_path):
    test_res = summarize_traffic_across_screenlines(
            pm_auto_network, screenlines_path, 'Name', scale_by_auto_phf=False
        )
    ref_res = pm_auto_network.summarize_traffic_across_screenlines(
        screenlines_path, 'Name', 
    )
    tm.assert_frame_equal(test_res, ref_res)


def test_summarize_screenlines_pm_scaled(pm_auto_network, screenlines_path):
    summary_results_cols = [
        'capacity', 'auto_vol', 'additional_vol', 'traffic_vol']
    test_res = summarize_traffic_across_screenlines(
            pm_auto_network, screenlines_path, 'Name', scale_by_auto_phf=True
        )
    ref_res = pm_auto_network.summarize_traffic_across_screenlines(
        screenlines_path, 'Name', 
    )
    ref_res[summary_results_cols] = \
        ref_res[summary_results_cols] * pm_auto_network.auto_phf
    tm.assert_frame_equal(test_res, ref_res)


def test_summarize_screenlines_dly(
        am_auto_network, pm_auto_network, screenlines_path):
    summary_results_cols = [
        'capacity', 'auto_vol', 'additional_vol', 'traffic_vol']
    test_result = summarize_traffic_across_screenlines(
            [am_auto_network, pm_auto_network], 
            screenlines_path, 
            'Name', 
            scale_by_auto_phf=True
        )
    am_result = am_auto_network.summarize_traffic_across_screenlines(
            screenlines_path, 'Name')
    am_result[summary_results_cols] = \
        am_result[summary_results_cols] * am_auto_network.auto_phf
    am_result.to_clipboard()

    pm_result = pm_auto_network.summarize_traffic_across_screenlines(
            screenlines_path, 'Name') 
    pm_result[summary_results_cols] = \
        pm_result[summary_results_cols] * pm_auto_network.auto_phf
    pm_result.to_clipboard()
    ref_result = am_result
    ref_result[summary_results_cols] = \
        am_result[summary_results_cols] + pm_result[summary_results_cols]
    ref_result['vcr'] = ref_result['traffic_vol'] / ref_result['capacity']
    tm.assert_frame_equal(test_result, ref_result, check_dtype=False)


def test_summarize_screenlines_am_nopeakhrfactor(
        am_auto_network, screenlines_path):
    net = deepcopy(am_auto_network)
    net.auto_phf = None
    with pytest.raises(RuntimeError, match='Auto peak-hour factor'):
        summarize_traffic_across_screenlines(
            net, screenlines_path, 'Name', scale_by_auto_phf=True
        )