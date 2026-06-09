from importlib.resources import files
from pathlib import Path
import geopandas as gpd
import pandas as pd

import pytest

import gtamodel_tools
from gtamodel_tools.common.spatial_aggregator import create_spatial_aggregator, SpatialAggregator
from gtamodel_tools.config import Config
from gtamodel_tools.network import Network

# Paths to test data directories and files

@pytest.fixture
def zone_ids() -> list[int]:
    return [1, 3, 4, 5]

@pytest.fixture
def regnode_ids() -> list[int]:
    return [
        101, 103, 104, 105, 200, 201, 202, 203, 204, 205, 206, 207, 208, 
        209, 210, 211, 212, 213, 214
    ]

@pytest.fixture
def szdict_zones() -> dict[int, int]:
    return {1: 3, 3: 2, 4: 2, 5: 1} 

@pytest.fixture
def szdict_regnodes() -> dict[int, int]:
    return {
        101: 3, 103: 2, 104: 2, 105: 1, 200: 3, 201: 3, 202: 3, 203: 3, 
        204: 3, 205: 3, 206: 3, 207: 3, 208: 1, 209: 1, 210: 1, 
        211: 1, 212: 1, 213: 1, 214: 1
    }


@pytest.fixture
def sz2lvldict1_zones() -> dict[int, str]:
    return {1: '3a', 3: '2a', 4: '2b', 5: '1a'}

@pytest.fixture
def sz2lvldict2_zones() -> dict[str, int]:
    return {'1a': 1, '2a': 2, '2b': 2, '3a': 3}


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
def szcustomranges_zones () -> list[tuple[int, int, int]]:
    return [
        (3, 1, 2), 
        (2, 3, 5), 
        (1, 5, 6)
    ]

@pytest.fixture
def szcustomranges_regnodes () -> list[tuple[int, int, int]]:
    return [
        (3, 101, 102), 
        (2, 103, 105), 
        (1, 105, 106),
        (3, 200, 208),
        (1, 208, 215),
    ]

@pytest.fixture
def sz_gdf(testdata_path) -> gpd.GeoDataFrame:
    shp_path = testdata_path / "SZ_definition" / "SZ_definition.shp"
    gdf = gpd.read_file(shp_path)
    return gdf.set_index('id')

3
@pytest.fixture
def testdata_path() -> Path:
    # This line creates a Path object starting at 
    # gtamodel_tools/src/gtamodel_tools
    src_path = files(gtamodel_tools)

    # files returns a importlib.resources.abc.Traversable, which is an object  
    # witha subset of pathlib.Path methods suitable for traversing directories  
    # and opening files. Convert to a full path to avoid typehinting issues.
    src_path = Path(str(src_path))

    # The test directory is at gtamodel_tools/tests, so we go up two levels 
    # (0 refers to first level) and then down into tests/test_data
    root_path = src_path.parents[1]
    return root_path / "tests" / "test_data"

@pytest.fixture
def model_output_path(testdata_path) -> Path:
    return testdata_path / 'Test_model_outputs'

@pytest.fixture
def demandmatrices_path(model_output_path) -> Path:
    return model_output_path / 'Demand'

@pytest.fixture
def losmatrices_path(model_output_path) -> Path:
    return model_output_path / 'LOS Matrices'

@pytest.fixture
def microsim_path(model_output_path) -> Path:
    return model_output_path / 'MicroSim Results'

@pytest.fixture
def networks_path(model_output_path) -> Path:
    return model_output_path / 'Networks'


# Summary config files
@pytest.fixture
def test_auto_summary_config(
        testdata_path, model_output_path
    ) -> Config:
    return Config(
        model_outputs_dir=model_output_path, 
        config_fp=testdata_path / 'auto_summary_config.yml'
    )

@pytest.fixture
def test_transit_summary_config(
        testdata_path, model_output_path
    ) -> Config:
    return Config(
        model_outputs_dir=model_output_path, 
        config_fp=testdata_path / 'transit_summary_config.yml'
    )

@pytest.fixture
def test_microsim_summary_config(
        testdata_path, model_output_path
    ) -> Config:
    return Config(
        model_outputs_dir=model_output_path, 
        config_fp=testdata_path / 'microsim_summary_config.yml'
    )


# Networks
@pytest.fixture
def am_auto_network(test_auto_summary_config) -> Network:
    net = Network(test_auto_summary_config)
    net.read_from_nwp(
        test_auto_summary_config.networks_subdir / 'AM_Auto.nwp'
    )
    return net

@pytest.fixture
def pm_auto_network(test_auto_summary_config) -> Network:
    net = Network(test_auto_summary_config)
    net.read_from_nwp(
        test_auto_summary_config.networks_subdir / 'PM_Auto.nwp'
    )
    return net

@pytest.fixture
def am_transit_network(test_transit_summary_config) -> Network:
    net = Network(test_transit_summary_config)
    net.read_from_nwp(
        test_transit_summary_config.networks_subdir / 'AM_Transit.nwp'
    )
    return net

@pytest.fixture
def pm_transit_network(test_transit_summary_config) -> Network:
    net = Network(test_transit_summary_config)
    net.read_from_nwp(
        test_transit_summary_config.networks_subdir / 'PM_Transit.nwp'
    )
    return net


#region Spatial aggregators
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

@pytest.fixture
def sa_1lvl_zones(szdict_zones)-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1lvl_zones', 
        lvl1_mapping=szdict_zones
    )

@pytest.fixture
def sa_1lvl_regnodes(szdict_regnodes)-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1lvl_regnodes', 
        lvl1_mapping=szdict_regnodes
    )

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
def sa_shpfile_zones(
        sz_gdf, 
        am_auto_network
    )-> type[SpatialAggregator]:   
    nodes = am_auto_network.nodes.copy()
    nodes = nodes.loc[nodes['is_centroid'] == True]
    return create_spatial_aggregator(
        aggregation_type='shapefile', 
        name='sa_shpfile_zones', 
        points=nodes,
        areas=sz_gdf
    )

@pytest.fixture
def sa_shpfile_regnodes(
        sz_gdf, 
        am_auto_network
    )-> type[SpatialAggregator]:   
    nodes = am_auto_network.nodes.copy()
    nodes = nodes.loc[nodes['is_centroid'] == False]
    return create_spatial_aggregator(
        aggregation_type='shapefile', 
        name='sa_shpfile_regnodes', 
        points=nodes,
        areas=sz_gdf
    )
