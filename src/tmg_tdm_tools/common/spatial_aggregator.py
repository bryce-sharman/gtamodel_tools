from abc import ABC, abstractmethod
import geopandas as gpd
import numpy as np
from numpy.typing import ArrayLike
import pandas as pd
from typing import Dict, List, Type, Union

import tmg_tdm_tools.enums as enums

class SpatialAggregator(ABC):
    @abstractmethod
    def __init__(self, name: str, tazs: ArrayLike):
        pass

    @abstractmethod
    def __call__(self) -> pd.Series:
        """ Returns a pandas series of the mapping from zones to spatial aggregation regions. """
        pass

    @abstractmethod
    def unique_regions(self) -> np.array:
        """ Returns a sorted array of the spatial aggregation regions. """
        pass

class ModelRegionSpatialAggregator(SpatialAggregator):
    REGION_ID = "model_region"
    def __init__(self, name, tazs, **_unused):
        if name is None or tazs is None:
            raise ValueError("ModelRegionSpatialAggregator must be defined using `name` and `tazs` parameters.")
        index = pd.Index(tazs, dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME)
        s = pd.Series(index=index, data=self.REGION_ID, name=name)
        self._spatial_aggregation = pd.Series(index=index, data=self.REGION_ID, name=name)

    def __call__(self):
        return self._spatial_aggregation
    
    def unique_regions(self):
        return np.sort(np.array([self.REGION_ID]))
    
    @property
    def name(self):
        return self._spatial_aggregation.name

class ZoneMappingSpatialAggregator(SpatialAggregator):
    def __init__(self, name, taz_mapping, **_unused):
        if name is None or taz_mapping is None:
            raise ValueError("ZoneMappingSpatialAggregator must be defined using `name` and `taz_mapping` parameters.")

        # taz_mapping can be either a Dict or a pandas Series, convert to Series
        taz_mapping = pd.Series(taz_mapping)
        index = pd.Index(taz_mapping.index, dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME)
        self._spatial_aggregation = pd.Series(index=index, data=taz_mapping, name=name)

    def __call__(self):
        return self._spatial_aggregation

    def unique_regions(self):
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self):
        return self._spatial_aggregation.name

class MappedCollectionSpatialAggregator(SpatialAggregator):
    def __init__(self, name, taz_mapping, collection_mapping, **_unused):
        if name is None or taz_mapping is None or collection_mapping is None:
            raise AttributeError(
                "ZoneMappingSpatialAggregator must be defined using "
                "`name`, `taz_mapping` and `collection_mapping` parameters.")
        # taz_mapping and collection_mapping can be either a Dict or a pandas Series, convert to Series
        taz_mapping = pd.Series(taz_mapping)
        collection_mapping = pd.Series(collection_mapping)

        index = pd.Index(taz_mapping.index, dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME)
        s = pd.Series(index=index, data=taz_mapping)
        s2 = s.map(collection_mapping)
        s2.name = name
        self._spatial_aggregation = s2

    def __call__(self):
        return self._spatial_aggregation
    
    def unique_regions(self):
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self):
        return self._spatial_aggregation.name

class CustomRangesSpatialAggregator(SpatialAggregator):
    def __init__(self, name, tazs, ranges, **_unused):
        if name is None or tazs is None or ranges is None:
            raise AttributeError(
                "CustomRangesSpatialAggregator must be defined using `name, `tazs` and `ranges` parameters.")
        index = pd.Index(tazs, dtype=enums.ZONE_ATTR_TYPE, name=enums.ZONE_INDEX_NAME)
        s = pd.Series(index=index, data=np.NaN, name=name)
        for r0, r1, r2 in ranges:
            r_label = r0
            r_min = r1
            r_max = r2
            fltr = (index>=r_min) & (index < r_max)
            s.loc[fltr] = r_label
        self._spatial_aggregation = s

    def __call__(self):
        return self._spatial_aggregation
    
    def unique_regions(self):
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self):
        return self._spatial_aggregation.name

class ShapefileSpatialAggregator(SpatialAggregator):
    def __init__(self, name, taz_geoms, region_shp, region_colname, **_unused):
        NotImplementedError("Not quite ready yet. ")

    def __call__(self):
        raise NotImplementedError("Not quite ready yet. ")
    
    def unique_regions(self):
        raise NotImplementedError("Not quite ready yet. ")
    
    @property
    def name(self):
        raise NotImplementedError("Not quite ready yet. ")

spatial_aggregators = {
    "model_region": ModelRegionSpatialAggregator,
    "mapped_zones": ZoneMappingSpatialAggregator,
    "mapped_collection": MappedCollectionSpatialAggregator,
    "custom_ranges": CustomRangesSpatialAggregator,
    "shapefile": ShapefileSpatialAggregator,
}

def create_spatial_aggregator(
        aggregation_type: str, 
        name: str, 
        tazs: Union[pd.Series, pd.Index, List] = None, 
        taz_mapping: Union[Dict, pd.Series, None] = None, 
        collection_mapping: Union[Dict, pd.Series, None] = None, 
        ranges: Union[List, None] = None, 
        taz_geoms: Union[gpd.GeoSeries, None] = None, 
        region_shp: Union[gpd.GeoDataFrame, None] = None, 
        region_colname: Union[str, None] = None,
        ) -> Type[SpatialAggregator]:
    """ Creates a spatial aggregator. 
    
    Args:
        aggregation_type: Must be one of: 
            ["model_region", "mapped_zones", "mapped_collection", "custom_ranges", "shapefile"]
        name: name to call the spatial aggregator
        tazs: List of traffic analysis zone IDs. Used for 'zone', 'model_region' and 'custom_ranges' aggregation type.
        taz_mapping: Mapping between zones and desired aggregation regions. 
            Used for "zone_mapping" and "mapped_collection" aggregation types
        collection_mapping: Mapping between a collection, defined using taz_mapping parameter and 
            desired aggregation regions. Used for "mapped_collection" aggregation type.
        ranges: list of tuples defined ranges
            each tuple is defined as:
                label: aggregation region label
                range_min: lower value in the range, inclusive
                range_max: uppder value in the range, exclusive
            Used for "custom_ranges" aggregation type
        taz_geoms=geopandas.GeoSeries, optional
            taz x, y coordinates 
            Used for "shapefile" aggregation type

        region_shp: geopandas.GeoDataFrame, optional
            Polygon GIS shapefile containing region boundaries.
            Used for "Shapefile" aggregation type
        
        region_colname: str, optional
            column name from the shapefile to use for aggregation region definition.
            Used for "Shapefile" aggregation type

    Returns
    -------
    subclass of SpatialAggregator
        Instantiated spatialAggregator object containing zone to aggregation region mapping.

    """
    if aggregation_type not in spatial_aggregators:
        raise ValueError("Invalid aggregation_type.")    
    sa = spatial_aggregators[aggregation_type]
    return sa(name, tazs=tazs, taz_mapping=taz_mapping, collection_mapping=collection_mapping, ranges=ranges,
              taz_geoms=taz_geoms, region_shp=region_shp, region_colname=region_colname)


def summarize_table_with_spatial_aggregation(    
        df: pd.DataFrame,
        values: str,
        zones: Union[str, List[str]],
        spatial_aggregations: Union[Type[SpatialAggregator], List[Union[Type[SpatialAggregator], None, False]], None], 
        crosstabs: Union[str, List[str], None] = None,
        crosstab_segments: Union[Dict, List[Dict], None] = None
    ) -> pd.DataFrame:
    """ Applies creates summary for table given spatial aggrgations(s).

    Args:
        df: DataFrame on which to apply spatial aggregation
        values: values expression, will be calculated using pd.eval.
        zones: column name or list of column names  to use for the zones to be aggregated
        spatial_aggregations: Spatial aggregation(s) to apply to zone_column
            If None (or any level in a list is None), then that level is output at the TAZ level.
            If any level in a list is False, then this will not be included in summary aggregation. 
            Cannot be False for a single-level aggregation.
        crosstabs: column or list of columns to be used to used create cross-tabulations tables
        crosstab_segments = dictionary, or list of dictionaries, that define crosstab segmentation

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    # Convert geographical aggregations and crosstab definitions to lists if they are not 
    # Using this form of casting to a list, as list(x) isn't happy with the spatial_aggregations object as it's not an iterable.
    zones = zones if isinstance(zones, list) else [zones]
    spatial_aggregations = spatial_aggregations if isinstance(spatial_aggregations, list) else [spatial_aggregations]
    if len(zones) != len(spatial_aggregations):
        raise ValueError("Number of zones columns and spatial_aggregation defintions must match.")
        
    if crosstabs is not None:
        crosstabs = crosstabs if isinstance(crosstabs, list) else [crosstabs]
        crosstab_segments = crosstab_segments if isinstance(crosstab_segments, list) else [crosstab_segments]
        if not len(crosstabs) == len(crosstab_segments):
            raise ValueError("Number of crosstabs columns and crosstab_segments must match.")
                             
    aggr_colnames = []
    i = 1
    for zn, sa in zip(zones, spatial_aggregations):
        if sa == False:
            continue
        elif sa is None:
            aggr_colnames.append(zn)
        else:
            if not sa.name in df.columns:
                df = df.merge(sa(), how="inner", left_on=zn, right_index=True)
                aggr_colnames.append(sa.name)
            else:
                df = df.merge(sa(), how="inner", left_on=zn, right_index=True, suffixes=["", f"_{i}"])
                aggr_colnames.append(f"{sa.name}_{i}")
                i = i + 1

    if crosstabs is not None:
        for ct, cts in zip(crosstabs, crosstab_segments):
            if cts is not None:
                df[ct] = df[ct].map(cts)
            aggr_colnames.append(ct)

    # Calculate the value which will be summed
    df["_TEMP_VALUES_COL"] = df.eval(values, engine="numexpr")
            
    pt = pd.pivot_table(df, index=aggr_colnames, values="_TEMP_VALUES_COL", aggfunc="sum", observed=True)
    pt.columns = ["total"]
    return pt
