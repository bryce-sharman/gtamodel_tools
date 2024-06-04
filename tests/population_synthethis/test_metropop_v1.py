from importlib.resources import files
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

import tmg_tdm_tools
from tmg_tdm_tools.population_synthesis.metropop_v1 import MetroPopV1Inputs
from tmg_tdm_tools.common.spatial_aggregator import create_spatial_aggregator
import tmg_tdm_tools.enums.population_synthesis.metropop_v1  as empv1
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
        dtype=empv1.ZA_DTYPES[empv1.ZA_POP]
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
        dtype=empv1.ZA_DTYPES[empv1.ZA_POP]
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
        dtype=empv1.ZA_DTYPES[empv1.ZA_POP]
    )
    df = metropop_v1.summarize_forecast_zone_attributes_population(
        sa_1lvl_aggr_pds, 'pd')
    tm.assert_frame_equal(df, ref_df)


def test_zone_employment_spat_aggr_modelregion(metropop_v1, sa_model_region):
    ref_df = pd.DataFrame(
        index=pd.Index(['model_region'], name='sa_model_region'),
        columns=pd.Index(empv1.ZA_EMP_COLS),
        data=[[6, 2, 3, 4, 5, 6, 15, 9, 11, 9, 8, 10, 12,
              10, 13, 15, 14, 14, 8, 6]],
        dtype=np.float32
    )
    df = metropop_v1.summarize_forecast_zone_attributes_employment(
        sa_model_region, 'taz')
    tm.assert_frame_equal(df, ref_df)

def test_zone_employment_spat_aggr_1lvl1aggr_pd(metropop_v1, sa_1lvl_aggr_pds):
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], name='sa_1_lvl_map_pds', dtype=np.uint32),
        columns=pd.Index(empv1.ZA_EMP_COLS),
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
                pd.Series([1, 2, 1, 2], dtype=empv1.PERSCNTRLS_DTYPES[
                    empv1.PERSCNTRLS_DWELLINGTYPE])
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


def test_summarize_number_of_seeds_by_hhld_ipu_segment(metropop_v1):
    ref_index = pd.MultiIndex.from_product(
        [
            pd.Series(range(1, 33), 
                      dtype=empv1.SD_DTYPES[empv1.SD_HHLD_HHLDTYPE]),
            pd.Series([1, 2], dtype=empv1.PERSCNTRLS_DTYPES[
                empv1.PERSCNTRLS_DWELLINGTYPE]),
            pd.Series([1, 2], dtype=empv1.PDGR_DTYPES[empv1.PDGR_PDGROUP])
        ], names=['HhldType', 'DwellingType', 'PDGroup']
    )
    ref_s = pd.Series(data=5, index=ref_index, dtype=np.uint32, name='one')
    ref_s.loc[1, :, :] = 10
    ref_s.loc[16, :, :] = 10
    s = metropop_v1.summarize_number_of_seeds_by_hhld_ipu_segment()
    tm.assert_series_equal(s, ref_s, check_exact=False, rtol=1e-5, atol=1e-8)

def test_hhld_sizes_from_seeds_nodtypes(metropop_v1):
    """ Test expected household sizes with high seed threshold. 
    
        Will not allow any segmentation by dwelling type.
    """
    # Reference dataframe calculated in Excel from test_data seed table
    ref_df = pd.DataFrame(
        index=pd.Series(
            range(1, 33), dtype=empv1.SD_DTYPES[empv1.SD_HHLD_HHLDTYPE]),
        data = [
            [1.00, 0.00, 0.00],
            [1.00, 0.00, 1.00],
            [1.00, 0.00, 2.45],
            [2.00, 0.00, 0.00],
            [2.00, 0.00, 1.00],
            [2.00, 0.00, 2.00],
            [2.00, 0.00, 3.25],
            [3.00, 0.00, 0.00],
            [3.00, 0.00, 1.00],
            [3.00, 0.00, 2.25],
            [4.00, 0.00, 0.00],
            [4.00, 0.00, 1.00],
            [4.00, 0.00, 2.20],
            [5.30, 0.00, 0.00],
            [5.40, 0.00, 1.30],
            [0.00, 1.00, 0.00],
            [0.00, 1.00, 1.20],
            [1.00, 1.00, 0.00],
            [1.00, 1.00, 1.55],
            [2.00, 1.00, 0.00],
            [2.00, 1.00, 1.55],
            [3.70, 1.00, 0.00],
            [3.35, 1.00, 1.45],
            [0.00, 2.00, 0.00],
            [0.00, 2.00, 1.35],
            [1.00, 2.00, 0.00],
            [1.00, 2.00, 1.60],
            [2.00, 2.00, 0.00],
            [2.00, 2.00, 1.95],
            [3.70, 2.00, 0.00],
            [3.25, 2.00, 1.70],
            [0.55, 3.10, 0.10],
        ],
        columns=['adult', 'senior', 'child'],
        dtype=np.float64
    )

    df = metropop_v1.calculate_expected_hhld_sizes_by_dtype_from_seeds(20)
    # As the values are constant by household type, I only entered
    # that in this function. reindex the ref_df to broadcasting to all other 
    # levels.
    ref_df = ref_df.reindex(df.index, axis=0, level=0)
    tm.assert_frame_equal(df, ref_df, check_exact=False, rtol=1e-5, atol=1e-8)

def test_hhld_sizes_from_seeds_dtypes(metropop_v1):
    """ Test expected household sizes with low seed threshold. 
    
        All hhld_types will be further segmented by dwelling types.
        
    """

    # Due to its size, read in the reference dataframe from a file,
    # which is also saved in test_data.
    src_path = files(tmg_tdm_tools)
    root_path = src_path.parents[1]
    popsyn_testdata_path = \
        root_path / "tests/test_data/population_synthesis/metropop_v1/"
    dtypes = {
        "HouseholdType": empv1.SD_DTYPES[empv1.SD_HHLD_HHLDTYPE],
        "DwellingType": empv1.SD_DTYPES[empv1.SD_HHLD_DWELLINGTYPE],
        "PDGroup": empv1.PDGR_DTYPES[empv1.PDGR_PDGROUP],
        "adult": np.float64,
        "senior": np.float64,
        "child": np.float64
    }
    ref_df = pd.read_csv(
        popsyn_testdata_path / "SeedData" / 
                "expected_hhld_sizes_full_segmentation.csv",
        dtype=dtypes,
        usecols=dtypes.keys(),
        index_col=["HouseholdType", "DwellingType", "PDGroup"]
    )
    df = metropop_v1.calculate_expected_hhld_sizes_by_dtype_from_seeds(2)
    tm.assert_frame_equal(df, ref_df, check_exact=False, rtol=1e-5, atol=1e-8)


def test_forecast_hhldcontrols_summary_nodtypes(metropop_v1):
    """ Test expected household sizes with high seed threshold. 
    
        Will not allow any segmentation by dwelling type when calculating
        expected household size.

    """
    # Reference calculations done separately in Excel
    ref_df = pd.DataFrame(
        index=pd.Index([1, 2], dtype=empv1.PDMAP_DTYPES[empv1.PDMAP_TO],
                       name='PD'),
        columns=['child', 'adult', 'senior'],
        data=[
            [0.234633886, 0.577231427, 0.188134687],
            [0.18872267, 0.619485999, 0.191791331]
        ],
        dtype=np.float64
    )

    df = metropop_v1.summarize_forecast_hhldcontrols(False, 2)
    tm.assert_frame_equal(df, ref_df, check_exact=False, rtol=1e-5, atol=1e-8)


def test_forecast_hhldcontrols_summary_withdtypes(metropop_v1):
    """ Test expected household sizes with low seed threshold. 
    
        All hhld_types will be further segmented by dwelling types when
        calculating expected household size.
        
    """
    ref_df = pd.DataFrame(
        index=pd.MultiIndex.from_arrays(
            [pd.Series([1, 1, 2, 2], dtype=empv1.PDMAP_DTYPES[empv1.PDMAP_TO]),
             pd.Series([1, 2, 1, 2], dtype=empv1.HHLDCNTRLS_DTYPES[
                 empv1.HHLDCNTRLS_DWELLINGTYPE])
            ],
            names = ['PD', 'DwellingType']
        ),
        columns=['child', 'adult', 'senior'],
        dtype=np.float64,
        data=[
            [0.23216187, 0.58146965, 0.18636848],
            [0.23712446, 0.57296137, 0.18991416],
            [0.18586790, 0.62211982, 0.19201229],
            [0.19157088, 0.61685824, 0.19157088]
        ]
    )

    df = metropop_v1.summarize_forecast_hhldcontrols(True, 2)
    tm.assert_frame_equal(df, ref_df, check_exact=False, rtol=1e-5, atol=1e-8)

