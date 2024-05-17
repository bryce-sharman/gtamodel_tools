""" Perform a test on the spatial aggregations. """

import numpy as np
import pandas as pd
import pandas.testing as tm

import tmg_tdm_tools.enums as enums
import tmg_tdm_tools.common.spatial_aggregator as sa

def test_modelregion_uint32_dtype():
    """ Tests model region spatial aggregator with 10 zones, defined using proper zone dtype. """
    ref_spat_aggr = pd.Series(
        index = pd.Index(data=range(0, 100), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = sa.ModelRegionSpatialAggregator.REGION_ID,
        name='sa_model_region'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        tazs=np.arange(0, 100, dtype=enums.ZONE_ATTR_TYPE)
    )
    tm.assert_series_equal(spat_aggr(), ref_spat_aggr)

def test_modelregion_other_integer_dtype():
    """ Tests model region spatial aggregator with 10 zones, defined using default integer dtype. """
    ref_spat_aggr = pd.Series(
        index = pd.Index(data=range(0, 100), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = sa.ModelRegionSpatialAggregator.REGION_ID,
        name='sa_model_region'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        tazs=pd.Series(range(0, 100))
    )
    tm.assert_series_equal(spat_aggr(), ref_spat_aggr)

def test_modelregion_unique():
    """ Tests unique method of ModelRegionSpatialAggregator. """
    ref_regions = np.array([sa.ModelRegionSpatialAggregator.REGION_ID])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='model_region', 
        name='sa_model_region', 
        tazs=pd.Series(range(0, 100))
    )
    assert np.array_equal(spat_aggr.unique_regions(), ref_regions)

def test_zoneaggregation_int_dict():
    """ Tests mapped zone spatial aggregator for 10 zones using integer superzones, defined using dictionary. """
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = [1, 2, 1, 2, 1, 2, 1, 2, 3, 3, 3, 4],
        name='sa_superzone'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_zones', 
        name='sa_superzone', 
        taz_mapping={0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 6:1, 7:2, 8:3, 9:3, 10:3, 11:4}
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_zoneaggregation_int_series():
    """ Tests mapped zone spatial aggregator for 10 zones using integer superzones, defined using Series. """
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = [1, 2, 1, 2, 1, 2, 1, 2, 3, 3, 3, 4],
        name='sa_superzone'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_zones', 
        name='sa_superzone', 
        taz_mapping=pd.Series({0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 6:1, 7:2, 8:3, 9:3, 10:3, 11:4})
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


def test_zoneaggregation_str_dict():
    """ Tests mapped zone spatial aggregator for 10 zones using string superzones, defined using Dict. """
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'c', 'c', 'c', 'd'],
        name='sa_superzone'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_zones', 
        name='sa_superzone', 
        taz_mapping={0:'a', 1:'b', 2:'a', 3:'b', 4:'a', 5:'b', 
                     6:'a', 7:'b', 8:'c', 9:'c', 10:'c', 11:'d'}
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_zoneaggregation_str_series():
    """ Tests mapped zone spatial aggregator for 10 zones using string superzones, defined using Series. """
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'c', 'c', 'c', 'd'],
        name='sa_superzone'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_zones', 
        name='sa_superzone', 
        taz_mapping=pd.Series({0:'a', 1:'b', 2:'a', 3:'b', 4:'a', 5:'b', 
                               6:'a', 7:'b', 8:'c', 9:'c', 10:'c', 11:'d'})
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


def test_zoneaggregation_int_unique():
    """ Tests unique method of ZoneMappingSpatialAggregator using string superzones. """
    ref_regions = np.array(['a', 'b', 'c', 'd'])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_zones', 
        name='sa_superzone', 
        taz_mapping={0:'a', 1:'b', 2:'a', 3:'b', 4:'a', 5:'b', 
                     6:'a', 7:'b', 8:'c', 9:'c', 10:'c', 11:'d'}
    )
    assert np.array_equal(spat_aggr.unique_regions(), ref_regions)

def test_zoneaggregation_str_unique():
    """ Tests unique method of ZoneMappingSpatialAggregator using integer superzones. """
    ref_regions = np.array([1, 2, 3, 4])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_zones', 
        name='sa_superzone', 
        taz_mapping={0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 
                     6:1, 7:2, 8:3, 9:3, 10:3, 11:4}
    )
    assert np.array_equal(spat_aggr.unique_regions(), ref_regions)

def test_mappedcollection_int_dict_mappings():
    """ Tests mapped mapped collection aggregator.
    
    Zone mapping is defined using dictionaries to integer superzones.
    Collection mapping is defined using dictionary to integer "super-super zone".

    """
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = [5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 5],
        name='sa_mappedcollection'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_collection', 
        name='sa_mappedcollection', 
        taz_mapping={0:1, 1:2, 2:1, 3:2, 4:1, 5:2, 6:1, 7:2, 8:3, 9:3, 10:3, 11:4},
        collection_mapping={1: 5, 2: 5, 3: 6, 4: 5}
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


def test_mappedcollection_str_series_mappings():
    """ Tests mapped mapped collection aggregator.
    
    Zone mapping is defined using dictionaries to str superzones.
    Collection mapping is defined using dictionary to str "super-super zone".

    """
    ref_mapping = pd.Series(
        index=pd.Index(data=range(0, 12), dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME),
        data = ['m', 'm', 'm', 'm', 'm', 'm', 'm', 'm', 'n', 'n', 'n', 'm'],
        name='sa_mappedcollection'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_collection', 
        name='sa_mappedcollection', 
        taz_mapping=pd.Series({0:'aa', 1:'bb', 2:'aa', 3:'bb', 4:'aa', 5:'bb', 6:'aa', 7:'bb', 8:'cc', 9:'cc', 10:'cc', 11:'dd'}),
        collection_mapping=pd.Series({'aa': 'm', 'bb': 'm', 'cc': 'n', 'dd': 'm'})
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_mappedcollection_str_unique():
    """ Tests unique method of MappedCollectionSpatialAggregator. """
    ref_regions = np.array(['m', 'n'])
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='mapped_collection', 
        name='sa_mappedcollection', 
        taz_mapping=pd.Series({0:'aa', 1:'bb', 2:'aa', 3:'bb', 4:'aa', 5:'bb', 6:'aa', 7:'bb', 8:'cc', 9:'cc', 10:'cc', 11:'dd'}),
        collection_mapping=pd.Series({'aa': 'm', 'bb': 'm', 'cc': 'n', 'dd': 'm'})
    )
    assert np.array_equal(spat_aggr.unique_regions(), ref_regions)

def test_customranges_int_regions():
    """ Tests Custom Ranges spatial aggregation creation. """
    ref_mapping = pd.Series(
        index=pd.Index(data=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25], 
                       dtype=enums.ZONE_ATTR_TYPE, 
                       name=enums.ZONE_INDEX_NAME),
        data = ['r1', 'r1', 'r1', 'r1', 'r1', 'r2', 'r2', 'r2', 'r2', 'r2', 'r3', 'r3', 'r3', 'r3', 'r3'],
        name='sa_customranges'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges', 
        tazs=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25],
        ranges=[
            ("r1", 1, 10),
            ("r2", 11, 20),
            ("r3", 21, 30)     
        ]
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)

def test_customranges_int_regions_exclupper():
    """ Tests Custom Ranges spatial aggregation creation, testing that upper bound is exclusive """
    ref_mapping = pd.Series(
        index=pd.Index(data=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25], 
                       dtype=enums.ZONE_ATTR_TYPE, 
                       name=enums.ZONE_INDEX_NAME),
        data = ['r1', 'r1', 'r1', 'r1', 'r1', 'r2', 'r2', 'r2', 'r2', 'r2', 'r3', 'r3', 'r3', 'r3', 'r3'],
        name='sa_customranges'
    )
    spat_aggr = sa.create_spatial_aggregator(
        aggregation_type='custom_ranges', 
        name='sa_customranges', 
        tazs=[1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25],
        ranges=[
            ("r1", 1, 11),
            ("r2", 11, 22),
            ("r3", 21, 31)     
        ]
    )
    tm.assert_series_equal(spat_aggr(), ref_mapping)


