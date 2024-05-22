from abc import ABC, abstractmethod
import geopandas as gpd
import numpy as np
from numpy.typing import ArrayLike
import pandas as pd
from typing import Dict, List, Type

class SpatialAggregator(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def __call__(self) -> pd.Series:
        """ Returns pandas series of the mapping from zones to regions. """
        pass

    @abstractmethod
    def unique_regions(self) -> np.array:
        """ Returns sorted array of the spatial aggregation regions. """
        pass

class ModelRegionSpatialAggregator(SpatialAggregator):
    REGION_ID = "model_region"
    def __init__(self, name, ids, **_unused):
        if name is None or ids is None:
            raise ValueError(
                "ModelRegionSpatialAggregator must be defined using `name` " 
                "and `ids` parameters."
            )
        index = pd.Index(ids, dtype=np.uint32)
        self._spatial_aggregation = pd.Series(
            index=index, data=self.REGION_ID, name=name)

    def __call__(self):
        return self._spatial_aggregation
    
    def unique_regions(self):
        return np.sort(np.array([self.REGION_ID]))
    
    @property
    def name(self):
        return self._spatial_aggregation.name

class OneLevelMappingSpatialAggregator(SpatialAggregator):
    def __init__(self, name, lvl1_mapping, **_unused):
        if name is None or lvl1_mapping is None:
            raise ValueError(
                "OneLevelMappingSpatialAggregator must be defined using `name` "
                "and `lvl1_mapping` parameters."
            )
        # taz_mapping can be either a Dict or a pandas Series, convert to Series
        self._spatial_aggregation = pd.Series(lvl1_mapping)
        self._spatial_aggregation.name = name

    def __call__(self):
        return self._spatial_aggregation

    def unique_regions(self):
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self):
        return self._spatial_aggregation.name

class TwoLevelMappingSpatialAggregator(SpatialAggregator):
    def __init__(self, name, lvl1_mapping, lvl2_mapping, **_unused):
        if name is None or lvl1_mapping is None or lvl2_mapping is None:
            raise AttributeError(
                "TwoLevelMappingSpatialAggregator must be defined using "
                "'name', 'lvl1_mapping' and 'lvl2_mapping' parameters.")
        # lvl1_mapping and lvl2_mapping can be either a Dict or a 
        # pandas Series, convert to Series
        lvl1_mapping = pd.Series(lvl1_mapping)
        lvl2_mapping = pd.Series(lvl2_mapping)
        s = pd.Series(lvl1_mapping)
        s2 = s.map(lvl2_mapping)
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
    def __init__(self, name, ids, ranges, **_unused):
        if name is None or ids is None or ranges is None:
            raise AttributeError(
                "CustomRangesSpatialAggregator must be defined using `name, "
                "`ids` and `ranges` parameters."
            )
        index = pd.Index(ids)
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
    def __init__(self, name, geoms, region_shp, region_colname, **_unused):
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
    "one_level_mapping": OneLevelMappingSpatialAggregator,
    "two_level_mapping": TwoLevelMappingSpatialAggregator,
    "custom_ranges": CustomRangesSpatialAggregator,
    "shapefile": ShapefileSpatialAggregator,
}

def create_spatial_aggregator(
        aggregation_type: str, 
        name: str, 
        ids: pd.Series | pd.Index | List = None, 
        lvl1_mapping: Dict | pd.Series | None = None, 
        lvl2_mapping: Dict | pd.Series | None = None, 
        ranges: List | None = None, 
        geoms: gpd.GeoSeries | None = None, 
        region_shp: gpd.GeoDataFrame | None = None, 
        region_colname: str | None = None,
        ) -> Type[SpatialAggregator]:
    """ Creates a spatial aggregator. 
    
    Args:
    aggregation_type: str
        Must be one of: ["model_region", "one_level_mapping",  
            "two_level_mapping", "custom_ranges", "shapefile"]
    name: str
        Name to call the spatial aggregator
    tazs: List of traffic analysis zone IDs. Used for 'zone', 
        'model_region' and 'custom_ranges' aggregation type.
    lvl1_mapping: 
        Direct mapping between to desired aggregation regions. 
        Used for "one_level_mapping" and "two_level_mapping" aggregation types.
    lvl2_mapping: 
        Two-level mapping to desired aggregation regions. (e.g. zone 
        to super-zone, then super-zone to final regions).
        Used for "two_level_mapping" aggregation type.
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
        Instantiated spatialAggregator object containing zone to aggregation 
        region mapping.

    """
    if aggregation_type not in spatial_aggregators:
        raise ValueError("Invalid aggregation_type.")    
    sa = spatial_aggregators[aggregation_type]
    return sa(name, 
              ids=ids, 
              lvl1_mapping=lvl1_mapping, 
              lvl2_mapping=lvl2_mapping, 
              ranges=ranges,
              geoms=geoms, 
              region_shp=region_shp, 
              region_colname=region_colname
    )


def summarize_table_with_spatial_aggregation(    
        df: pd.DataFrame,
        values: str,
        geom_id: str | List[str],
        spatial_aggregations: Type[SpatialAggregator] | List[
            Type[SpatialAggregator] | None | False] | None, 
        crosstabs: str | List[str] | None = None,
        crosstab_segments: Dict | List[Dict] | None = None
    ) -> pd.DataFrame:
    """ Applies creates summary for table given spatial aggrgations(s).

    Args:
        df: panadas.DataFrame 
            Data on which to apply spatial aggregation
        values: str
            Mathematical expression to be evaluated, will be calculated 
            using pd.eval.
        geom_id: str or List[str]
            Column name or list of column names to use for the geometries 
            to be aggregated.
        spatial_aggregations: Subclass of SpatialAggregator, or List of
            spatial aggregators or None. A list can be provided to denote
            multiple aggregation summaries.  If None (or any level in a list 
            is None), then that level is output at the TAZ level. If any level 
            in a list is False, then this will not be included in summary  
            aggregation. Cannot be False for a single-level aggregation.
        crosstabs: str or List[str]
            Column or list of columns to be used to used create 
            cross-tabulations tables.
        crosstab_segments: Dict or List[dict] 
            Define crosstab segmentation.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    # Convert geographical aggregations and crosstab definitions to lists 
    # if they are not already in this form. Doing this as list(x) isn't happy 
    # with the spatial_aggregations object as it's not an iterable.
    geom_id = geom_id if isinstance(geom_id, list) else [geom_id]
    spatial_aggregations = spatial_aggregations if isinstance(
        spatial_aggregations, list) else [spatial_aggregations]
    if len(geom_id) != len(spatial_aggregations):
        raise ValueError("Number of zones columns and spatial_aggregation "
                         "defintions must match."
    )
        
    if crosstabs is not None:
        crosstabs = crosstabs if isinstance(crosstabs, list) else [crosstabs]
        crosstab_segments = crosstab_segments if isinstance(
            crosstab_segments, list) else [crosstab_segments]
        if not len(crosstabs) == len(crosstab_segments):
            raise ValueError("Number of crosstabs columns and "
                             "crosstab_segments must match.")
                             
    aggr_colnames = []
    i = 1
    for zn, sa in zip(geom_id, spatial_aggregations):
        if sa == False:
            continue
        elif sa is None:
            aggr_colnames.append(zn)
        else:
            if not sa.name in df.columns:
                df = df.merge(sa(), how="inner", left_on=zn, right_index=True)
                aggr_colnames.append(sa.name)
            else:
                df = df.merge(sa(), how="inner", left_on=zn, right_index=True, 
                              suffixes=["", f"_{i}"]
                )
                aggr_colnames.append(f"{sa.name}_{i}")
                i = i + 1

    if crosstabs is not None:
        for ct, cts in zip(crosstabs, crosstab_segments):
            if cts is not None:
                df[ct] = df[ct].map(cts)
            aggr_colnames.append(ct)

    # Calculate the value which will be summed
    df["_TEMP_VALUES_COL"] = df.eval(values, engine="numexpr")
    pt = pd.pivot_table(df, 
                        index=aggr_colnames, 
                        values="_TEMP_VALUES_COL", 
                        aggfunc="sum", 
                        observed=True
    )
    pt.columns = ["total"]
    return pt
