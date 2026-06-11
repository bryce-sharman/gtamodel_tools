""" Tests for gtamodel_tools.common.spatial_aggregator.OneLevelMappingSpatialAggregator. """

import numpy as np
import pandas as pd
import pandas.testing as tm
import pytest

from gtamodel_tools.common.spatial_aggregator import create_spatial_aggregator
from gtamodel_tools.common.spatial_aggregator import SpatialAggregator

# Fixtures for this test are in conftest.py as they are also used in
# other aggregator tests

#region Tests
def test_sa_1lvl_zones(sa_1lvl_zones, szdict_zones):
    ref = pd.Series(
        index=pd.Index(data=szdict_zones.keys(), dtype=np.uint32),
        data = szdict_zones.values(),
        name='sa_1lvl_zones'
    )
    tm.assert_series_equal(sa_1lvl_zones.mapping, ref)

def test_sa_1lvl_zones_str(sa_1lvl_zones_str, szdict_zones_str):
    ref = pd.Series(
        index=pd.Index(data=szdict_zones_str.keys(), dtype=np.uint32),
        data = szdict_zones_str.values(),
        name='sa_1lvl_zones_str'
    )
    tm.assert_series_equal(sa_1lvl_zones_str.mapping, ref)


def test_sa_1lvl_regnodes(sa_1lvl_regnodes, szdict_regnodes):
    ref = pd.Series(
        index=pd.Index(data=szdict_regnodes.keys(), dtype=np.uint32),
        data = szdict_regnodes.values(),
        name='sa_1lvl_regnodes'
    )
    tm.assert_series_equal(sa_1lvl_regnodes.mapping, ref)


def test_sa_1lvl_regnodes_str(sa_1lvl_regnodes_str, szdict_regnodes_str):
    ref = pd.Series(
        index=pd.Index(data=szdict_regnodes_str.keys(), dtype=np.uint32),
        data = szdict_regnodes_str.values(),
        name='sa_1lvl_regnodes_str'
    )
    tm.assert_series_equal(sa_1lvl_regnodes_str.mapping, ref)


def test_sa_1lvl_unique(sa_1lvl_regnodes):
    ref = np.sort(np.array(list(set(sa_1lvl_regnodes.mapping))))
    assert np.array_equal(sa_1lvl_regnodes.unique_regions, ref)   


def test_sa_1lvl_unique_str(sa_1lvl_regnodes_str):
    ref = np.sort(np.array(list(set(sa_1lvl_regnodes_str.mapping))))
    assert np.array_equal(sa_1lvl_regnodes_str.unique_regions, ref) 

#endregion