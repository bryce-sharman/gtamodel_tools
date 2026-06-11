""" Tests for gtamodel_tools.common.spatial_aggregator.CustomRangesSpatialAggregator """

from copy import deepcopy
import geopandas as gpd
import numpy as np
import pandas as pd
import pandas.testing as tm
import pytest

from gtamodel_tools.common.spatial_aggregator import create_spatial_aggregator
from gtamodel_tools.common.spatial_aggregator import SpatialAggregator


#region Fixtures
@pytest.fixture
def szcustomranges_zones() -> list[tuple[int, int, int]]:
    return [
        (3, 1, 2), 
        (2, 3, 5), 
        (1, 5, 6)
    ]


@pytest.fixture
def szcustomranges_zones_str() -> list[tuple[str, int, int]]:
    return [
        ('sz3', 1, 2), 
        ('sz2', 3, 5), 
        ('sz1', 5, 6)
    ]


@pytest.fixture
def szcustomranges_regnodes() -> list[tuple[int, int, int]]:
    return [
        (3, 101, 102), 
        (2, 103, 105), 
        (1, 105, 106),
        (3, 200, 208),
        (1, 208, 215),
    ]


@pytest.fixture
def szcustomranges_regnodes_str() -> list[tuple[str, int, int]]:
    return [
        ('sz3', 101, 102), 
        ('sz2', 103, 105), 
        ('sz1', 105, 106),
        ('sz3', 200, 208),
        ('sz1', 208, 215),
    ]



@pytest.fixture
def sa_customranges_zones(
        zone_ids, 
        szcustomranges_zones
    )-> type[SpatialAggregator]:   
    return create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges_zones', 
        ids=zone_ids,
        ranges=szcustomranges_zones
    )     


@pytest.fixture
def sa_customranges_zones_str(
        zone_ids, 
        szcustomranges_zones_str
    )-> type[SpatialAggregator]:   
    return create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges_zones', 
        ids=zone_ids,
        ranges=szcustomranges_zones_str
    )   


@pytest.fixture
def sa_customranges_regnodes(
        regnode_ids, 
        szcustomranges_regnodes
    )-> type[SpatialAggregator]:    
    return create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges_zones', 
        ids=regnode_ids,
        ranges=szcustomranges_regnodes
    )  


@pytest.fixture
def sa_customranges_regnodes_str(
        regnode_ids, 
        szcustomranges_regnodes_str
    )-> type[SpatialAggregator]:    
    return create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges_zones', 
        ids=regnode_ids,
        ranges=szcustomranges_regnodes_str
    )  


#region Custom ranges spatial aggregator tests
def test_sa_customranges_zones(sa_customranges_zones, sa_1lvl_zones):
    tm.assert_series_equal(
        sa_customranges_zones.mapping, 
        sa_1lvl_zones.mapping, 
        check_names=False
    )


def test_sa_customranges_zones_str(sa_customranges_zones_str, sa_1lvl_zones_str):
    print(sa_customranges_zones_str)
    print(sa_1lvl_zones_str)
    tm.assert_series_equal(
        sa_customranges_zones_str.mapping, 
        sa_1lvl_zones_str.mapping, 
        check_names=False
    )


def test_sa_customranges_regnodes(sa_customranges_regnodes, sa_1lvl_regnodes):
    tm.assert_series_equal(
        sa_customranges_regnodes.mapping, 
        sa_1lvl_regnodes.mapping, 
        check_names=False
    )


def test_sa_customranges_regnodes_str(
        sa_customranges_regnodes_str, sa_1lvl_regnodes_str):
    tm.assert_series_equal(
        sa_customranges_regnodes_str.mapping, 
        sa_1lvl_regnodes_str.mapping, 
        check_names=False
    )  


def test_sa_customranges_regnodes_unique(
        sa_customranges_regnodes, sa_1lvl_regnodes):
    assert np.array_equal(
        sa_customranges_regnodes.unique_regions, 
        sa_1lvl_regnodes.unique_regions
    ) 


def test_sa_customranges_regnodes_unique_str(
        sa_customranges_regnodes_str, sa_1lvl_regnodes_str):
    assert np.array_equal(
        sa_customranges_regnodes_str.unique_regions, 
        sa_1lvl_regnodes_str.unique_regions
    ) 
