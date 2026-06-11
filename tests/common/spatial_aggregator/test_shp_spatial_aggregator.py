""" Tests for gtamodel_tools.common.spatial_aggregator.ShapefileSpatialAggregator. """

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
def szgdf(testdata_path) -> gpd.GeoDataFrame:
    shp_path = testdata_path / "SZ_definition" / "SZ_definition.shp"
    gdf = gpd.read_file(shp_path)
    return gdf.set_index('id_int')


@pytest.fixture
def szgdf_str(testdata_path) -> gpd.GeoDataFrame:
    shp_path = testdata_path / "SZ_definition" / "SZ_definition.shp"
    gdf = gpd.read_file(shp_path)
    return gdf.set_index('id_str')


@pytest.fixture
def sa_shpfile_zones(szgdf, am_auto_network)-> type[SpatialAggregator]:   
    nodes = am_auto_network.nodes.copy()
    nodes = nodes.loc[nodes['is_centroid'] == True]
    return create_spatial_aggregator(
        aggregation_type='shapefile', 
        name='sa_shpfile_zones', 
        points=nodes,
        areas=szgdf
    )


@pytest.fixture
def sa_shpfile_zones_str(szgdf_str, am_auto_network)-> type[SpatialAggregator]:   
    nodes = am_auto_network.nodes.copy()
    nodes = nodes.loc[nodes['is_centroid'] == True]
    return create_spatial_aggregator(
        aggregation_type='shapefile', 
        name='sa_shpfile_zones', 
        points=nodes,
        areas=szgdf_str
    )


@pytest.fixture
def sa_shpfile_regnodes(szgdf, am_auto_network)-> type[SpatialAggregator]:   
    nodes = am_auto_network.nodes.copy()
    nodes = nodes.loc[nodes['is_centroid'] == False]
    return create_spatial_aggregator(
        aggregation_type='shapefile', 
        name='sa_shpfile_regnodes', 
        points=nodes,
        areas=szgdf
    )


@pytest.fixture
def sa_shpfile_regnodes_str(
        szgdf_str, am_auto_network)-> type[SpatialAggregator]:   
    nodes = am_auto_network.nodes.copy()
    nodes = nodes.loc[nodes['is_centroid'] == False]
    return create_spatial_aggregator(
        aggregation_type='shapefile', 
        name='sa_shpfile_regnodes', 
        points=nodes,
        areas=szgdf_str
    )
#endregion

#region shapefile spatial aggregator tests
def test_sa_shpfile_zones(sa_shpfile_zones, sa_1lvl_zones):
    tm.assert_series_equal(
        sa_shpfile_zones.mapping, 
        sa_1lvl_zones.mapping, 
        check_names=False
    )


def test_sa_shpfile_zones_str(sa_shpfile_zones_str, sa_1lvl_zones_str):
    tm.assert_series_equal(
        sa_shpfile_zones_str.mapping, 
        sa_1lvl_zones_str.mapping, 
        check_names=False
    )


def test_sa_shpfile_regnodes(sa_shpfile_regnodes, sa_1lvl_regnodes):
    tm.assert_series_equal(
        sa_shpfile_regnodes.mapping, 
        sa_1lvl_regnodes.mapping, 
        check_names=False
    )


def test_sa_shpfile_regnodes_str(sa_shpfile_regnodes_str, sa_1lvl_regnodes_str):
    print(sa_shpfile_regnodes_str.mapping)
    print(sa_1lvl_regnodes_str.mapping)
    tm.assert_series_equal(
        sa_shpfile_regnodes_str.mapping, 
        sa_1lvl_regnodes_str.mapping, 
        check_names=False
    )


def test_sa_shpfile_regnodes_unique(sa_shpfile_regnodes, sa_1lvl_regnodes):
    assert np.array_equal(
        sa_shpfile_regnodes.unique_regions, 
        sa_1lvl_regnodes.unique_regions
    ) 


def test_sa_shpfile_regnodes_unique_str(
        sa_shpfile_regnodes_str, sa_1lvl_regnodes_str):
    assert np.array_equal(
        sa_shpfile_regnodes_str.unique_regions, 
        sa_1lvl_regnodes_str.unique_regions
    ) 
#endregion