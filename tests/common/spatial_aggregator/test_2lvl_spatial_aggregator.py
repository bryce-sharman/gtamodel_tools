""" Tests for gtamodel_tools.common.spatial_aggregator.TwoLevelMappingSpatialAggregator. """

import numpy as np
import pandas as pd
import pandas.testing as tm
import pytest

from gtamodel_tools.common.spatial_aggregator import create_spatial_aggregator
from gtamodel_tools.common.spatial_aggregator import SpatialAggregator



#region 2-level spatial aggregation test fixtures
@pytest.fixture
def sz2lvldict1_zones() -> dict[int, str]:
    return {1: '3a', 3: '2a', 4: '2b', 5: '1a'}


@pytest.fixture
def sz2lvldict2_zones() -> dict[str, int]:
    return {'1a': 1, '2a': 2, '2b': 2, '3a': 3}


@pytest.fixture
def sz2lvldict2_zones_str() -> dict[str, str]:
    return {'1a': 'sz1', '2a': 'sz2', '2b': 'sz2', '3a': 'sz3'}


@pytest.fixture
def sz2lvldict1_regnodes() -> dict[int, str]:
    return {
        101: '3a', 103: '2a', 104: '2b', 105: '1a', 200: '3a', 201: '3a', 
        202: '3a', 203: '3a', 204: '3b', 205: '3b', 206: '3b', 207: '3b', 
        208: '1b', 209: '1b', 210: '1b', 211: '1b', 212: '1b', 213: '1a', 
        214: '1a'
    } 


@pytest.fixture
def sz2lvldict2_regnodes() -> dict[str, int]:
    return {'1a': 1, '1b': 1, '2a': 2, '2b': 2, '3a': 3, '3b': 3} 


@pytest.fixture
def sz2lvldict2_regnodes_str() -> dict[str, str]:
    return {
        '1a': 'sz1', '1b': 'sz1', 
        '2a': 'sz2', '2b': 'sz2', 
        '3a': 'sz3', '3b': 'sz3'
    } 

@pytest.fixture
def sa_2lvl_zones(
        sz2lvldict1_zones, sz2lvldict2_zones
    )-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_2lvl_zones', 
        lvl1_mapping=sz2lvldict1_zones, 
        lvl2_mapping=sz2lvldict2_zones
     )


@pytest.fixture
def sa_2lvl_zones_str(
        sz2lvldict1_zones, sz2lvldict2_zones_str
    )-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_2lvl_zones', 
        lvl1_mapping=sz2lvldict1_zones, 
        lvl2_mapping=sz2lvldict2_zones_str
     )

@pytest.fixture
def sa_2lvl_regnodes(
        sz2lvldict1_regnodes, 
        sz2lvldict2_regnodes
    )-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_2lvl_regnodes', 
        lvl1_mapping=sz2lvldict1_regnodes, 
        lvl2_mapping=sz2lvldict2_regnodes
     )


@pytest.fixture
def sa_2lvl_regnodes_str(
        sz2lvldict1_regnodes, 
        sz2lvldict2_regnodes_str
    )-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_2lvl_regnodes', 
        lvl1_mapping=sz2lvldict1_regnodes, 
        lvl2_mapping=sz2lvldict2_regnodes_str
     )
#endregion

#region Tests
def test_sa_2lvl_zones(sa_2lvl_zones, sa_1lvl_zones):
    tm.assert_series_equal(
        sa_2lvl_zones.mapping, 
        sa_1lvl_zones.mapping, 
        check_names=False
    )


def test_sa_2lvl_zones_str(sa_2lvl_zones_str, sa_1lvl_zones_str):
    tm.assert_series_equal(
        sa_2lvl_zones_str.mapping, 
        sa_1lvl_zones_str.mapping, 
        check_names=False
    )


def test_sa_2lvl_zones_unique(sa_2lvl_zones, sa_1lvl_zones):
    assert np.array_equal(
        sa_2lvl_zones.unique_regions, 
        sa_1lvl_zones.unique_regions
    )  

def test_sa_2lvl_zones_unique_str(sa_2lvl_zones_str, sa_1lvl_zones_str):
    assert np.array_equal(
        sa_2lvl_zones_str.unique_regions, 
        sa_1lvl_zones_str.unique_regions
    ) 


def test_sa_2lvl_regnodes(sa_2lvl_regnodes, sa_1lvl_regnodes):
    tm.assert_series_equal(
        sa_2lvl_regnodes.mapping, 
        sa_1lvl_regnodes.mapping, 
        check_names=False
    )


def test_sa_2lvl_regnodes_str(sa_2lvl_regnodes_str, sa_1lvl_regnodes_str):
    tm.assert_series_equal(
        sa_2lvl_regnodes_str.mapping, 
        sa_1lvl_regnodes_str.mapping, 
        check_names=False
    )


def test_sa_2lvl_regnodes_unique(sa_2lvl_regnodes, sa_1lvl_regnodes):
    assert np.array_equal(
        sa_2lvl_regnodes.unique_regions, 
        sa_1lvl_regnodes.unique_regions
    )  

def test_sa_2lvl_regnodes_unique_str(
        sa_2lvl_regnodes_str, sa_1lvl_regnodes_str):
    assert np.array_equal(
        sa_2lvl_regnodes_str.unique_regions, 
        sa_1lvl_regnodes_str.unique_regions
    ) 
#endregion

