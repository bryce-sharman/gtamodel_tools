from importlib.resources import files
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

import tmg_tdm_tools
from tmg_tdm_tools.population_synthethis.metropop_v1 import MetroPopV1Inputs
from tmg_tdm_tools.common.spatial_aggregator import create_spatial_aggregator
from tmg_tdm_tools.enums.population_synthesis.metropop_v1 import ZA_DTYPES, ZA_POP

@pytest.fixture
def metropop_v1():
    mpv1 = MetroPopV1Inputs()
    src_path = files(tmg_tdm_tools)
    root_path = src_path.parents[1]
    popsyn_testdata_path = \
        root_path / "tests/test_data/population_synthesis/metropop_v1"
    mpv1.read_input_files(
        popsyn_testdata_path, 
        popsyn_testdata_path / "Scenarios"
    )
    yield mpv1

@pytest.fixture
def sa_model_region():
    yield create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        ids=pd.Series([1, 2, 3])
    )

@pytest.fixture
def sa_1lvl_aggr_tazs():
    index = pd.Index(pd.Series([1, 2, 3]), name='taz')
    mapping = pd.Series(index=index, data=[1, 1, 2], name='mapping')
    yield create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1_lvl_map_tazs',
        lvl1_mapping=mapping
    )

@pytest.fixture
def sa_1lvl_aggr_pds():
    # Note that due to zone mapping file changing PD3 to PD2, this is
    # equivalent to zone mapping {1: 1, 2: 2, 3: 2}
    index = pd.Index(pd.Series([1, 2]), name='pd')
    mapping = pd.Series(index=index, data=[1, 2], name='mapping')
    yield create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_1_lvl_map_pds',
        lvl1_mapping=mapping
    )

@pytest.fixture
def sa_2lvl_aggr_tazs():
    taz_mapping = pd.Series({1:1, 2:2, 3:3})
    collection_mapping = pd.Series({1:1, 2:1, 3:2})

    yield create_spatial_aggregator(
        aggregation_type='2_level_mapping',
        name='sa_2_lvl_map_tazs',
        lvl1_mapping=taz_mapping,
        lvl2_mapping=collection_mapping
    )


def test_zone_population_spat_aggr_modelregion(metropop_v1, sa_model_region):
    """ Test population summary from zone attributes file. """
    ref_df = pd.DataFrame(
        index=pd.Index(['model_region'], name='sa_model_region'), 
        columns=['total'], 
        data=316, 
        dtype=ZA_DTYPES[ZA_POP]
    )
    df = metropop_v1.summarize_forecast_zone_attributes_population(
        sa_model_region, 'taz')
    tm.assert_frame_equal(df, ref_df)


def test_zone_population_spat_aggr_1lvl1aggr_taz(
        metropop_v1, sa_1lvl_aggr_tazs):
    """ Test population summary from zone attributes file. """
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_1_lvl_map_tazs'), 
        columns=['total'], 
        data=[211, 105], 
        dtype=ZA_DTYPES[ZA_POP]
    )
    df = metropop_v1.summarize_forecast_zone_attributes_population(
        sa_1lvl_aggr_tazs, 'taz')
    tm.assert_frame_equal(df, ref_df)


def test_zone_population_spat_aggr_zoneaggr_pd(
        metropop_v1, sa_1lvl_aggr_pds):
    """ Test population summary from zone attributes file. """
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_1_lvl_map_pds'), 
        columns=['total'], 
        data=[126, 190],
        dtype=ZA_DTYPES[ZA_POP]
    )
    df = metropop_v1.summarize_forecast_zone_attributes_population(
        sa_1lvl_aggr_pds, 'pd')
    tm.assert_frame_equal(df, ref_df)


@pytest.mark.skip(reason="not implemented")
def test_zone_employment_spat_aggr_modelregion(metropop_v1):
    assert 1 == 0  # Force failure for now


@pytest.mark.skip(reason="not implented")
def test_summarize_number_of_seeds_by_hhld_ipu_segment(self) -> pd.Series:
    assert 1 == 0  # Force failure for now


@pytest.mark.skip(reason="not implented")
def test_forecast_hhldcontrols_summary(metropop_v1):
    assert 1 == 0  # Force failure for now

   
@pytest.mark.skip(reason="not implented")
def test_forecast_perscontrols_summary(metropop_v1):
    assert 1 == 0  # Force failure for now
