from importlib.resources import files
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

import tmg_tdm_tools
from tmg_tdm_tools.calibration.synthetic_population_calibration \
    import summarize_total_households, summarize_hhld_dwellingtype_distn
from tmg_tdm_tools.common.spatial_aggregator import create_spatial_aggregator
from tmg_tdm_tools.synthetic_population.synthetic_population \
    import SyntheticPopulation
from tmg_tdm_tools.enums.synthetic_population import HOUSEHOLD_DTYPES


@pytest.fixture
def synthetic_population():
    src_path = files(tmg_tdm_tools)
    root_path = src_path.parents[1]
    popsyn_testdata_path = \
        root_path / "tests/test_data/synthetic_population/gtamodelv4_1_2"
    households_path = popsyn_testdata_path / "households.csv"
    persons_path = popsyn_testdata_path / "persons.csv"
    yield SyntheticPopulation(
        tmg_tdm_tools.ModelVersion.GTAModelv4_1_2, 
        households_path, 
        persons_path
    )

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
def sa_2lvl_aggr_tazs():
    lvl1_mapping = pd.Series({1:1, 2:2, 3:3})
    lvl2_mapping = pd.Series({1:1, 2:1, 3:2})

    yield create_spatial_aggregator(
        aggregation_type='two_level_mapping',
        name='sa_2lvl_aggr_tazs',
        lvl1_mapping=lvl1_mapping,
        lvl2_mapping=lvl2_mapping
    )


#region Test spatial aggregations
def test_total_households_spat_aggr_none(synthetic_population):
    ref_index = pd.Index(pd.Series([1, 2, 3]).astype(
        HOUSEHOLD_DTYPES['home_zone']))
    ref_index.name = 'home_zone'
    ref_df = pd.DataFrame(
        index=ref_index, 
        columns=["weight"], 
        data=[55.6, 87.6, 119.6], 
        dtype=HOUSEHOLD_DTYPES['weight']
    )
    ref_df.name = 'total_households'
    df = summarize_total_households(synthetic_population)
    tm.assert_frame_equal(df, ref_df)

def test_total_households_spat_aggr_modelregion(
        synthetic_population, sa_model_region):
    ref_df = pd.DataFrame(
        index=pd.Index(['model_region'], name='sa_model_region'), 
        columns=["weight"], 
        data=[262.8], 
        dtype=HOUSEHOLD_DTYPES['weight']
    )
    ref_df.name = 'total_households'
    df = summarize_total_households(
        synthetic_population, home_sa=sa_model_region)
    tm.assert_frame_equal(df, ref_df)

def test_total_households_spat_aggr_zonemapping(
        synthetic_population, sa_1lvl_aggr_tazs):
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_1_lvl_map_tazs'), 
        columns=["weight"], 
        data=[143.2, 119.6], 
        dtype=np.float32
    )
    ref_df.name = 'total_households'
    df = summarize_total_households(
        synthetic_population, home_sa=sa_1lvl_aggr_tazs
    )
    tm.assert_frame_equal(df, ref_df)

def test_total_households_spat_aggr_mappedcollection(
        synthetic_population, sa_2lvl_aggr_tazs):
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_2lvl_aggr_tazs'), 
        columns=["weight"], 
        data=[143.2, 119.6], 
        dtype=np.float32
    )
    ref_df.name = 'total_households'
    df = summarize_total_households(
        synthetic_population, home_sa=sa_2lvl_aggr_tazs)
    tm.assert_frame_equal(df, ref_df)
#endregion

#region Test household attributes

def test_household_dwelling_types_spat_aggr_none(
        synthetic_population, home_sa=None):
    zone_array = np.uint32([1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, ])
    dtype_array = pd.Series(
        [1, 3, 9, 1, 2, 3, 9, 1, 2, 3, 9],
        dtype=pd.CategoricalDtype(categories=[1, 2, 3, 9], ordered=False))
    ref_index = pd.MultiIndex.from_arrays(
        [zone_array, dtype_array],
        names=["home_zone", "dwelling_type"])
    ref_df = pd.DataFrame(
        index=ref_index,
        columns=["weight"], 
        data=[38.7, 13.36, 3.54, 9.2, 55.9, 14.82, 
              7.68, 38.22, 35.88, 32.1, 13.4],
        dtype=np.float32
    )
    ref_df.name = 'households_by_dwellingtype'
    df = summarize_hhld_dwellingtype_distn(synthetic_population, home_sa=None)
    tm.assert_frame_equal(df, ref_df)
#endregion

#region Test v0 inputs
