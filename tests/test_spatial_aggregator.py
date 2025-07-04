""" Perform a test on the spatial aggregations. """

import numpy as np
import pandas as pd
import pandas.testing as tm

import gtamodel_tools.common.spatial_aggregator as sa

def test_modelregion_uint32_dtype():
    ref_spat_aggr = pd.Series(
        index = pd.Index(data=range(0, 100), 
                         dtype=np.uint32),
        data = sa.ModelRegionSpatialAggregator.REGION_ID,
        name='sa_model_region'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        ids=np.arange(0, 100, dtype=np.uint32)
    )
    tm.assert_series_equal(spat_aggr(), ref_spat_aggr)

def test_modelregion_other_integer_dtype():
    ref_spat_aggr = pd.Series(
        index = pd.Index(data=range(0, 100), dtype=np.uint32),
        data = sa.ModelRegionSpatialAggregator.REGION_ID,
        name='sa_model_region'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        ids=pd.Series(range(0, 100))
    )
    tm.assert_series_equal(spat_aggr(), ref_spat_aggr)

def test_modelregion_unique():
    ref_regions = np.array([sa.ModelRegionSpatialAggregator.REGION_ID])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        ids=pd.Series(range(0, 100))
    )
    assert np.array_equal(spat_aggr.unique_regions, ref_regions)

def test_1lvl_mapping_int_dict():
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12)),
        data = [1, 2, 1, 2, 1, 2, 1, 2, 3, 3, 3, 4],
        name='sa_superzone'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_superzone', 
        lvl1_mapping={0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 6:1, 
                      7:2, 8:3, 9:3, 10:3, 11:4
        }
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_1lvl_mapping_int_series():
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=np.uint32, name='taz'),
        data = [1, 2, 1, 2, 1, 2, 1, 2, 3, 3, 3, 4],
        name='sa_superzone'
    )
    mapping = pd.Series(
        index=pd.Index([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 
                       dtype=np.uint32, name='taz'),
        data=[1, 2, 1, 2, 1, 2, 1, 2, 3, 3, 3, 4]
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_superzone', 
        lvl1_mapping=mapping
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


def test_1lvl_mapping_str_dict():
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12)),
        data = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'c', 'c', 'c', 'd'],
        name='sa_superzone'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_superzone', 
        lvl1_mapping={0:'a', 1:'b', 2:'a', 3:'b', 4:'a', 5:'b', 
                     6:'a', 7:'b', 8:'c', 9:'c', 10:'c', 11:'d'}
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_1lvl_mapping_str_series():
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=np.uint32, name='taz'),
        data = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'c', 'c', 'c', 'd'],
        name='sa_superzone'
    )
    mapping = pd.Series(
        index=pd.Index(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            dtype=np.uint32, name='taz'),
        data=['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'c', 'c', 'c', 'd']
    )

    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_superzone', 
        lvl1_mapping=mapping
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


def test_1lvl_mapping_int_unique():
    ref_regions = np.array(['a', 'b', 'c', 'd'])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_superzone', 
        lvl1_mapping={0:'a', 1:'b', 2:'a', 3:'b', 4:'a', 5:'b', 
                     6:'a', 7:'b', 8:'c', 9:'c', 10:'c', 11:'d'}
    )
    assert np.array_equal(spat_aggr.unique_regions, ref_regions)

def test_1lvl_mapping_str_unique():
    ref_regions = np.array([1, 2, 3, 4])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='one_level_mapping', 
        name='sa_superzone', 
        lvl1_mapping={0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 
                     6:1, 7:2, 8:3, 9:3, 10:3, 11:4}
    )
    assert np.array_equal(spat_aggr.unique_regions, ref_regions)

def test_2lvl_mapping_int_dict_mappings():
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12)),
        data = [5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 5],
        name='sa_mappedcollection'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_mappedcollection', 
        lvl1_mapping={0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 
                      6:1, 7:2, 8:3, 9:3, 10:3, 11:4
                      },
        lvl2_mapping={1: 5, 2: 5, 3: 6, 4: 5}
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


def test_2lvl_mapping_str_series_mappings():
    ref_mapping = pd.Series(
        index=pd.Index(
            data=range(0, 12), 
            dtype=np.uint32, 
            name='taz'
        ),
        data = ['m', 'm', 'm', 'm', 'm', 'm', 'm', 'm', 'n', 'n', 'n', 'm'],
        name='sa_mappedcollection'
    )
    lvl1_mapping = pd.Series(
        index=pd.Index(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            dtype=np.uint32,
            name='taz'
        ),
        data=['aa','bb', 'aa','bb','aa','bb','aa','bb','cc','cc','cc', 'dd']
    )
    lvl2_mapping = pd.Series(
        index=pd.Index(['aa', 'bb', 'cc', 'dd']),
        data=['m', 'm', 'n', 'm']
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_mappedcollection', 
        lvl1_mapping=lvl1_mapping,
        lvl2_mapping=lvl2_mapping)
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_2lvl_mapping_str_unique():
    """ Tests unique method of MappedCollectionSpatialAggregator. """
    ref_regions = np.array(['m', 'n'])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='two_level_mapping', 
        name='sa_mappedcollection', 
        lvl1_mapping=pd.Series({
            0:'aa', 1:'bb', 2:'aa', 3:'bb', 4:'aa', 5:'bb', 
            6:'aa', 7:'bb', 8:'cc', 9:'cc', 10:'cc', 11:'dd'
            }),
        lvl2_mapping=pd.Series({'aa': 'm', 'bb': 'm', 'cc': 'n', 'dd': 'm'})
    )
    assert np.array_equal(spat_aggr.unique_regions, ref_regions)

def test_customranges_int_regions():
    ref_mapping = pd.Series(
        index=pd.Index(
            data=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]),
        data = ['r1', 'r1', 'r1', 'r1', 'r1', 
                'r2', 'r2', 'r2', 'r2', 'r2', 
                'r3', 'r3', 'r3', 'r3', 'r3'],
        name='sa_customranges'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges', 
        ids=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25],
        ranges=[
            ("r1", 1, 10),
            ("r2", 11, 20),
            ("r3", 21, 30)     
        ]
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_customranges_int_regions_exclupper():
    """ Tests Custom Ranges spatial aggregation creation, 
        testing that upper bound is exclusive.
    """
    ref_mapping = pd.Series(
        index=pd.Index(
            data=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]),
        data = ['r1', 'r1', 'r1', 'r1', 'r1', 
                'r2', 'r2', 'r2', 'r2', 'r2', 
                'r3', 'r3', 'r3', 'r3', 'r3'],
        name='sa_customranges'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges', 
        ids=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25],
        ranges=[
            ("r1", 1, 11),
            ("r2", 11, 22),
            ("r3", 21, 31)     
        ]
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


