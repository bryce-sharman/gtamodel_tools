from importlib.resources import files
from pathlib import Path
import geopandas as gpd
import pandas as pd

import pytest
from shapely.lib import length

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


#region 1-level spatial aggregators
# These are included here as they are often a reference for the other 
# aggregator tests
@pytest.fixture
def szdict_zones() -> dict[int, int]:
    return {1: 3, 3: 2, 4: 2, 5: 1} 

@pytest.fixture
def szdict_zones_str() -> dict[int, str]:
    return {1: 'sz3', 3: 'sz2', 4: 'sz2', 5: 'sz1'} 

@pytest.fixture
def szdict_regnodes() -> dict[int, int]:
    return {
        101: 3, 103: 2, 104: 2, 105: 1, 200: 3, 201: 3, 202: 3, 203: 3, 
        204: 3, 205: 3, 206: 3, 207: 3, 208: 1, 209: 1, 210: 1, 
        211: 1, 212: 1, 213: 1, 214: 1
    }

@pytest.fixture
def szdict_regnodes_str() -> dict[int, str]:
    return {
        101: 'sz3', 103: 'sz2', 104: 'sz2', 105: 'sz1', 
        200: 'sz3', 201: 'sz3', 202: 'sz3', 203: 'sz3', 
        204: 'sz3', 205: 'sz3', 206: 'sz3', 207: 'sz3', 
        208: 'sz1', 209: 'sz1', 210: 'sz1', 211: 'sz1', 
        212: 'sz1', 213: 'sz1', 214: 'sz1'
    }

@pytest.fixture
def sa_1lvl_zones(szdict_zones)-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1lvl_zones', 
        lvl1_mapping=szdict_zones
    )

@pytest.fixture
def sa_1lvl_zones_str(szdict_zones_str)-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1lvl_zones_str', 
        lvl1_mapping=szdict_zones_str
    )

@pytest.fixture
def sa_1lvl_regnodes(szdict_regnodes)-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1lvl_regnodes', 
        lvl1_mapping=szdict_regnodes
    )

@pytest.fixture
def sa_1lvl_regnodes_str(szdict_regnodes_str)-> type[SpatialAggregator]:
    return create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1lvl_regnodes_str', 
        lvl1_mapping=szdict_regnodes_str
    )
#endregion





