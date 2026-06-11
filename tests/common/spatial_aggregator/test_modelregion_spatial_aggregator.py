""" Tests for gtamodel_tools.common.spatial_aggregator.ModelRegionSpatialAggregator """

import numpy as np
import pandas as pd
import pandas.testing as tm
import pytest

from gtamodel_tools.common.spatial_aggregator import create_spatial_aggregator
from gtamodel_tools.common.spatial_aggregator import ModelRegionSpatialAggregator
from gtamodel_tools.common.spatial_aggregator import SpatialAggregator

#region fixtures
@pytest.fixture
def sa_model_region_zones(zone_ids) -> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_modelregion_zones', 
        ids=zone_ids
    )

@pytest.fixture
def sa_model_region_regnodes(regnode_ids) -> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_modelregion_regnodes', 
        ids=regnode_ids
    )
#endregion

#region Tests
def test_sa_model_region_zones(sa_model_region_zones, zone_ids):
    ref = pd.Series(
        index = pd.Index(data=zone_ids, dtype=np.uint32),
        data = ModelRegionSpatialAggregator.REGION_ID,
        name = 'sa_modelregion_zones'
    )
    tm.assert_series_equal(sa_model_region_zones.mapping, ref)


def test_sa_model_region_regnodes(sa_model_region_regnodes, regnode_ids):
    ref = pd.Series(
        index = pd.Index(data=regnode_ids, dtype=np.uint32),
        data = ModelRegionSpatialAggregator.REGION_ID,
        name = 'sa_modelregion_regnodes'
    )
    tm.assert_series_equal(sa_model_region_regnodes.mapping, ref)


def test_sa_model_region_unique(sa_model_region_regnodes):
    assert sa_model_region_regnodes.unique_regions == np.array(
        [ModelRegionSpatialAggregator.REGION_ID])
#endregion

