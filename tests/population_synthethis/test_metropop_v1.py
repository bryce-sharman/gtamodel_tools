from importlib.resources import files
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

import tmg_tdm_tools
from tmg_tdm_tools.population_synthethis.metropop_v1 import MetroPopV1Inputs
from tmg_tdm_tools.common.spatial_aggregator import create_spatial_aggregator
from tmg_tdm_tools.enums.population_synthesis.metropop_v1 import ZA_DTYPES, \
    ZA_POP, ZA_EMP_COLS, PERSCNTRLS_DTYPES, PERSCNTRLS_DWELLINGTYPE

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
    mapping = pd.Series(index=index, data=[1, 2], 
                        name='mapping', 
                        dtype=np.uint32
    )
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
        columns=['population'], 
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
        columns=['population'], 
        data=[211, 105], 
        dtype=ZA_DTYPES[ZA_POP]
    )
    df = metropop_v1.summarize_forecast_zone_attributes_population(
        sa_1lvl_aggr_tazs, 'taz')
    tm.assert_frame_equal(df, ref_df)


def test_zone_population_spat_aggr_1lvl1aggr_pd(
        metropop_v1, sa_1lvl_aggr_pds):
    """ Test population summary from zone attributes file. """
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_1_lvl_map_pds', dtype=np.uint32), 
        columns=['population'], 
        data=[126, 190],
        dtype=ZA_DTYPES[ZA_POP]
    )
    df = metropop_v1.summarize_forecast_zone_attributes_population(
        sa_1lvl_aggr_pds, 'pd')
    tm.assert_frame_equal(df, ref_df)


def test_zone_employment_spat_aggr_modelregion(metropop_v1, sa_model_region):

    ref_df = pd.DataFrame(
        index=pd.Index(['model_region'], name='sa_model_region'),
        columns=pd.Index(ZA_EMP_COLS),
        data=[[6, 2, 3, 4, 5, 6, 15, 9, 11, 9, 8, 10, 12,
              10, 13, 15, 14, 14, 8, 6]],
        dtype=np.float32
    )
    print(ref_df)

    df = metropop_v1.summarize_forecast_zone_attributes_employment(
        sa_model_region, 'taz')
    print(df)
    tm.assert_frame_equal(df, ref_df)

def test_zone_employment_spat_aggr_1lvl1aggr_pd(metropop_v1, sa_1lvl_aggr_pds):

    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_1_lvl_map_pds', dtype=np.uint32),
        columns=pd.Index(ZA_EMP_COLS),
        data=[
            [0, 0, 0, 0, 0, 0, 8, 1, 2, 3, 1, 2, 3, 0, 2, 3, 1, 0, 3, 1],
            [6, 2, 3, 4, 5, 6, 7, 8, 9, 6, 7, 8, 9, 10, 11, 12, 13, 14, 5, 5]
        ],
        dtype=np.float32
    )
    df = metropop_v1.summarize_forecast_zone_attributes_employment(
        sa_1lvl_aggr_pds, 'pd')
    tm.assert_frame_equal(df, ref_df)


def test_forecast_perscontrols_summary_nodtypes(metropop_v1):
    # Reference data taken from calculation done in Excel
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], dtype=np.float32, name='PD'),
        columns=['child', 'adult', 'senior'],
        data=[
            [0.305555556, 0.555555556, 0.138888889],
            [0.151020408, 0.702040816, 0.146938776]
        ]
    )

    df = metropop_v1.summarize_forecast_perscontrols(
        add_dwellingtype_segmentation=False
    )
    tm.assert_frame_equal(df, ref_df, check_exact=False, rtol=1e-5, atol=1e-8)

def test_forecast_perscontrols_summary_withdtypes(metropop_v1):
    # Reference data taken from calculation done in Excel
    ref_df = pd.DataFrame(
        index=pd.MultiIndex.from_arrays([
                pd.Series([1, 1, 2, 2], dtype=np.float32), 
                pd.Series([1, 2, 1, 2], dtype=PERSCNTRLS_DTYPES[
                    PERSCNTRLS_DWELLINGTYPE])
            ], 
            names=['PD', 'DwellingType']
        ),
        columns=['child', 'adult', 'senior'],
        data=[[0.305555556, 0.555555556, 0.138888889],
              [0.305555556, 0.555555556, 0.138888889],
              [0.149700599, 0.718562874, 0.131736527],
              [0.153846154, 0.666666667, 0.179487179]
        ]
    )

    df = metropop_v1.summarize_forecast_perscontrols(
        add_dwellingtype_segmentation=True
    )
    tm.assert_frame_equal(df, ref_df, check_exact=False, rtol=1e-5, atol=1e-8)

@pytest.mark.skip(reason="not implented")
def test_summarize_number_of_seeds_by_hhld_ipu_segment(self) -> pd.Series:

    assert 1 == 0  # Force failure for now


@pytest.mark.skip(reason="not implented")
def test_forecast_hhldcontrols_summary_nodtypes(metropop_v1):
    metropop_v1.summarize_forecast_hhldcontrols(False, 10)

@pytest.mark.skip(reason="not implented")
def test_forecast_hhldcontrols_summary_withdtypes(metropop_v1):
    metropop_v1.summarize_forecast_hhldcontrols(False, 10)



   

