""" Perform a test on the spatial aggregations. """

import numpy as np
import pandas as pd
import pandas.testing as tm
import pytest

import gtamodel_tools.common.spatial_aggregator as sa


def test_sa_model_region_zones(sa_model_region_zones, zone_ids):
    ref = pd.Series(
        index = pd.Index(data=zone_ids, dtype=np.uint32),
        data = sa.ModelRegionSpatialAggregator.REGION_ID,
        name = 'sa_modelregion_zones'
    )
    tm.assert_series_equal(sa_model_region_zones.mapping, ref)


def test_sa_model_region_regnodes(sa_model_region_regnodes, regnode_ids):
    ref = pd.Series(
        index = pd.Index(data=regnode_ids, dtype=np.uint32),
        data = sa.ModelRegionSpatialAggregator.REGION_ID,
        name = 'sa_modelregion_regnodes'
    )
    tm.assert_series_equal(sa_model_region_regnodes.mapping, ref)

def test_sa_model_region_unique(sa_model_region_regnodes):
    assert sa_model_region_regnodes.unique_regions == np.array(
        [sa.ModelRegionSpatialAggregator.REGION_ID])

def test_sa_1lvl_zones(sa_1lvl_zones, szdict_zones):
    ref = pd.Series(
        index=pd.Index(data=szdict_zones.keys(), dtype=np.uint32),
        data = szdict_zones.values(),
        name='sa_1lvl_zones'
    )
    tm.assert_series_equal(sa_1lvl_zones.mapping, ref)

def test_sa_1lvl_regnodes(sa_1lvl_regnodes, szdict_regnodes):
    ref = pd.Series(
        index=pd.Index(data=szdict_regnodes.keys(), dtype=np.uint32),
        data = szdict_regnodes.values(),
        name='sa_1lvl_regnodes'
    )
    tm.assert_series_equal(sa_1lvl_regnodes.mapping, ref)

def test_sa_1lvl_unique(sa_1lvl_regnodes):
    ref = np.sort(np.array(list(set(sa_1lvl_regnodes.mapping))))
    assert np.array_equal(sa_1lvl_regnodes.unique_regions, ref)   

def test_sa_2lvl_zones(sa_2lvl_zones, sa_1lvl_zones):
    tm.assert_series_equal(
        sa_2lvl_zones.mapping, 
        sa_1lvl_zones.mapping, 
        check_names=False
    )

def test_sa_2lvl_regnodes(sa_2lvl_regnodes, sa_1lvl_regnodes):
    tm.assert_series_equal(
        sa_2lvl_regnodes.mapping, 
        sa_1lvl_regnodes.mapping, 
        check_names=False
    )

def test_sa_2lvl_unique(sa_2lvl_regnodes, sa_1lvl_regnodes):
    assert np.array_equal(
        sa_2lvl_regnodes.unique_regions, 
        sa_1lvl_regnodes.unique_regions
    )  


def test_sa_customranges_zones(sa_customranges_zones, sa_1lvl_zones):
    tm.assert_series_equal(
        sa_customranges_zones.mapping, 
        sa_1lvl_zones.mapping, 
        check_names=False
    )


def test_sa_customranges_regnodes(sa_customranges_regnodes, sa_1lvl_regnodes):
    tm.assert_series_equal(
        sa_customranges_regnodes.mapping, 
        sa_1lvl_regnodes.mapping, 
        check_names=False
    )

def test_sa_customranges_unique(sa_customranges_regnodes, sa_1lvl_regnodes):
    assert np.array_equal(
        sa_customranges_regnodes.unique_regions, 
        sa_1lvl_regnodes.unique_regions
    ) 

def test_sa_shpfile_zones(sa_shpfile_zones, sa_1lvl_zones):
    tm.assert_series_equal(
        sa_shpfile_zones.mapping, 
        sa_1lvl_zones.mapping, 
        check_names=False
    )

def test_sa_shpfile_regnodes(sa_shpfile_regnodes, sa_1lvl_regnodes):
    tm.assert_series_equal(
        sa_shpfile_regnodes.mapping, 
        sa_1lvl_regnodes.mapping, 
        check_names=False
    )

def test_sa_shpfile_unique(sa_shpfile_regnodes, sa_1lvl_regnodes):
    assert np.array_equal(
        sa_shpfile_regnodes.unique_regions, 
        sa_1lvl_regnodes.unique_regions
    ) 
