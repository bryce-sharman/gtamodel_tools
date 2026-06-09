from abc import ABC, abstractmethod
import geopandas as gpd
import numpy as np
from numpy.typing import ArrayLike
import pandas as pd
from pandas.api.types import is_numeric_dtype
from typing import Hashable

class SpatialAggregator(ABC):
    @abstractmethod
    def __init__(self):
        pass
    
    @property
    @abstractmethod
    def mapping(self) -> pd.Series:
        """ Returns pandas series of the mapping from zones to regions. """
        pass
    @property
    @abstractmethod
    def unique_regions(self) -> np.ndarray:
        """ Returns sorted array of the spatial aggregation regions. """
        pass

    @property
    @abstractmethod
    def name(self) -> Hashable:
        """ Returns the spatial aggregator name."""
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
        s = pd.Series(
            index=index, data=self.REGION_ID, name=name)
        self._spatial_aggregation = s.sort_index()
        
    @property
    def mapping(self) -> pd.Series:
        return self._spatial_aggregation
    @property
    def unique_regions(self) -> np.ndarray:
        return np.sort(np.array([self.REGION_ID]))
    
    @property
    def name(self) -> Hashable:
        return self._spatial_aggregation.name

class OneLevelMappingSpatialAggregator(SpatialAggregator):
    def __init__(self, name, lvl1_mapping, **_unused):
        if name is None or lvl1_mapping is None:
            raise ValueError(
                "OneLevelMappingSpatialAggregator must be defined using `name` "
                "and `lvl1_mapping` parameters."
            )
        # taz_mapping can be either a dict or a pandas Series, convert to Series
        s = pd.Series(lvl1_mapping, name=name)
        s.index = s.index.astype(np.uint32)
        self._spatial_aggregation = s.sort_index()

    @property
    def mapping(self) -> pd.Series:
        return self._spatial_aggregation
    
    @property
    def unique_regions(self) -> np.ndarray:
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self) -> Hashable:
        return self._spatial_aggregation.name

class TwoLevelMappingSpatialAggregator(SpatialAggregator):
    def __init__(self, name, lvl1_mapping, lvl2_mapping, **_unused):
        if name is None or lvl1_mapping is None or lvl2_mapping is None:
            raise AttributeError(
                "TwoLevelMappingSpatialAggregator must be defined using "
                "'name', 'lvl1_mapping' and 'lvl2_mapping' parameters.")
        # lvl1_mapping and lvl2_mapping can be either a dict or a 
        # pandas Series, convert to Series
        lvl1_mapping = pd.Series(lvl1_mapping)
        lvl2_mapping = pd.Series(lvl2_mapping)
        s = pd.Series(lvl1_mapping, name=name)
        s2 = s.map(lvl2_mapping)
        s2.index = s2.index.astype(np.uint32)
        self._spatial_aggregation = s2.sort_index()

    @property
    def mapping(self) -> pd.Series:
        return self._spatial_aggregation

    @property
    def unique_regions(self) -> np.ndarray:
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self) -> Hashable:
        return self._spatial_aggregation.name

class CustomRangesSpatialAggregator(SpatialAggregator):
    def __init__(self, name, ids, ranges, **_unused):
        if name is None or ids is None or ranges is None:
            raise AttributeError(
                "CustomRangesSpatialAggregator must be defined using `name, "
                "`ids` and `ranges` parameters."
            )
        index = pd.Index(ids, dtype=np.uint32)
        s = pd.Series(index=index, data=None, name=name)
        for r0, r1, r2 in ranges:
            r_label = r0
            r_min = r1
            r_max = r2
            fltr = (index>=r_min) & (index < r_max)
            s.loc[fltr] = r_label
        s = s.sort_index()
        # Convert to int if possible
        if is_numeric_dtype(s) and s.equals(s.round(0)):
            s = s.astype(np.int64)
        self._spatial_aggregation = s

    @property
    def mapping(self) -> pd.Series:
        return self._spatial_aggregation
    
    @property
    def unique_regions(self) -> np.ndarray:
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self) -> Hashable:
        return self._spatial_aggregation.name

class ShapefileSpatialAggregator(SpatialAggregator):
    def __init__(self, name, points, areas, **_unused):
        if not isinstance(points, gpd.GeoDataFrame) or not \
                np.all(points.geom_type == 'Point'):
            raise TypeError("points must be a Points geopandas.GeoDataFrame.")
        if not isinstance(areas, gpd.GeoDataFrame) or not \
                np.all(areas.geom_type.isin(['Polygon', 'MultiPolygon'])):
            raise TypeError("points must be a Polygon geopandas.GeoDataFrame.")
        if points.crs is None or areas.crs is None:
            raise ValueError("Both points and areas must have a defined CRS.")
        # Dont' mess with the original dataframes
        points = points.copy()
        areas = areas.copy()
        # Perform the spatial join between points and areas
        areas = areas.to_crs(points.crs)
        areas.index.name = name
        points2 = points.sjoin(areas, how='left')
        if len(points2) > len(points):
            points2 = points2.loc[~points2.index.duplicated(keep='first')]
        self._spatial_aggregation = points2[name]
        self._spatial_aggregation.name = name
        self._spatial_aggregation.index = \
            self._spatial_aggregation.index.astype(np.uint32)

    @property
    def mapping(self) -> pd.Series:
        return self._spatial_aggregation
    
    @property
    def unique_regions(self) -> np.ndarray:
        unique = self._spatial_aggregation.unique()
        return np.sort(unique)
    
    @property
    def name(self) -> Hashable:
        return self._spatial_aggregation.name

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
        ids: pd.Series | pd.Index | list | None = None, 
        lvl1_mapping: dict | pd.Series | None = None, 
        lvl2_mapping: dict | pd.Series | None = None, 
        ranges: list | None = None, 
        points: gpd.GeoDataFrame | None = None, 
        areas: gpd.GeoDataFrame | None = None, 
        ) -> type[SpatialAggregator]:
    """ Creates a spatial aggregator. 
    
    Args:
    aggregation_type: str
        Must be one of: ["model_region", "one_level_mapping",  
            "two_level_mapping", "custom_ranges", "shapefile"]
    name:
        Name to call the spatial aggregator
    tazs: 
        List of traffic analysis zone IDs. Used for 'zone', 
        'model_region' and 'custom_ranges' aggregation type.
    lvl1_mapping: 
        Direct mapping between to desired aggregation regions. 
        Used for "one_level_mapping" and "two_level_mapping" aggregation types.
    lvl2_mapping: 
        Two-level mapping to desired aggregation regions. (e.g. zone 
        to super-zone, then super-zone to final regions).
        Used for "two_level_mapping" aggregation type.
    ranges: 
        List of tuples defined ranges. Each tuple is defined as:
            label: aggregation region label
            range_min: lower value in the range, inclusive
            range_max: uppder value in the range, exclusive
        Used for "custom_ranges" aggregation type
    points=geopandas.GeoDataFrame, optional
        geopandas.GeoDataFrame containing the point geometries of each 
        item to be aggregations
    areas: geopandas.GeoDataFrame, optional
        Polygon GeoDataFrame containing region boundaries, must contain
        a 'geometry' column. The index will be applied as the aggregator.
        Used for "shapefile" aggregation type


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
              points=points, 
              areas=areas
    )

def summarize_table_with_spatial_aggregation(    
        df: pd.DataFrame,
        values: str | list[str],
        geom_id: str | list[str],
        spatial_aggregations: type[SpatialAggregator] | None | bool | list[
            type[SpatialAggregator] | None | bool] , 
        crosstabs: str | list[str] | None = None,
        crosstab_segments: dict | list[dict] | None = None
    ) -> pd.DataFrame | pd.Series:
    """ Applies creates summary for table given spatial aggrgations(s).

    Args:
        df:
            Data on which to apply spatial aggregation
        values: 
            Mathematical expression to be evaluated, will be calculated 
            using pd.eval.
        geom_id: 
            Column name or list of column names to use for the geometries 
            to be aggregated.
        spatial_aggregations: 
            SpatialAggregator object or list of SpatialAggregator objects to.
            apply. A list can be provided to denote
            multiple aggregation summaries.  If None (or any level in a list 
            is None), then that level is output at the TAZ level. If any level 
            in a list is False, then this will not be included in summary  
            aggregation. Cannot be False for a single-level aggregation.
        crosstabs: 
            Column or list of columns to be used to used create 
            cross-tabulations tables.
        crosstab_segments: 
            Define crosstab segmentation.

    Returns:
        pd.DataFrame: Summary pandas DataFrame

    """
    # Convert geographical aggregations and crosstab definitions to lists 
    # if they are not already in this form.
    geom_id = geom_id if isinstance(geom_id, list) else [geom_id]
    spatial_aggregations = spatial_aggregations if isinstance(
        spatial_aggregations, list) else [spatial_aggregations]
    if len(geom_id) != len(spatial_aggregations):
        raise ValueError("Number of zones columns and spatial_aggregation "
                         "defintions must match."
    )
    if crosstabs is not None:
        crosstabs = crosstabs if isinstance(crosstabs, list) else [crosstabs]
    if crosstab_segments is not None:
        crosstab_segments = crosstab_segments if isinstance(
            crosstab_segments, list) else [crosstab_segments]
    if crosstabs is not None and crosstab_segments is not None and \
            len(crosstabs) != len(crosstab_segments):
        raise ValueError("Number of crosstabs columns and "
                        "crosstab_segments must match.")
    df = df.copy()  # to not mess with input DataFrame                
    aggr_colnames = []
    i = 1
    for zn, sa in zip(geom_id, spatial_aggregations):
        if sa == False:
            continue
        elif sa is None:
            aggr_colnames.append(zn)
        elif isinstance(sa, SpatialAggregator):
            if not sa.name in df.columns:
                df = df.merge(
                    sa.mapping, how="inner", left_on=zn, right_index=True)
                aggr_colnames.append(sa.name)
            else:
                df = df.merge(
                    sa.mapping,
                    how="inner", 
                    left_on=zn, 
                    right_index=True, 
                    suffixes=["", f"_{i}"]
                )
                aggr_colnames.append(f"{sa.name}_{i}")
                i = i + 1

    if crosstabs is not None:
        if crosstab_segments is not None:
            # Extend using crosstab_segments
            for ct, cts in zip(crosstabs, crosstab_segments):
                if cts is not None:
                    df[ct] = df[ct].map(cts)
                aggr_colnames.append(ct)
        else:
            # Extend using the different crosstab values
            aggr_colnames.extend(crosstabs)

    if not isinstance(values, list):
        # Summarizing a single variable or expression
        temp_col = "_TEMP_VALUES_COL"
        df[temp_col] = df.eval(values, engine="numexpr")
        pt = pd.pivot_table(df, 
                            index=aggr_colnames, 
                            values=temp_col, 
                            aggfunc="sum", 
                            observed=True
        )
        pt.columns = [values]
    else:
        # Multiple variables or expressions to summarize
        temp_cols = []
        for i, value in enumerate(values):
            temp_col = f"_TEMP_{i:03d}"
            df[temp_col] = df.eval(value, engine="numexpr")
            temp_cols.append(temp_col)
        pt = pd.pivot_table(df, 
                            index=aggr_colnames, 
                            values=temp_cols, 
                            aggfunc="sum", 
                            observed=True
        )
        pt.columns = values

    if pt.index.nlevels > 1:
        pt = pt.unstack(fill_value=0)
        pt.columns = pt.columns.droplevel(0)
    return pt

def create_integer_crosstab_segment_dict(
        min_value: int, 
        max_separate_value: int, 
        max_value: int, 
        prefix: str='',
        suffix: str=''
    ) -> dict:
    """ Create a crosstab_segmentation dictionary for integer values.
    
    Args:
        min_value: int
            Minimum value to include
        max_separate_value: int
            Maximum value that is enumerated separately. Anything beyond
            this is placed into a single category.
        max_value: int, 
            Maximum value to include in the dictionary.
        prefix: str
            Text to add to the start of the category name
        suffix: str
            Text to add to the end of the category name

    """
    d = {}
    for i in range(min_value, max_separate_value+1):
        d[i] = f'{prefix}{i}{suffix}'
    for i in range(max_separate_value+1, max_value + 1):
        d[i] = f'{prefix}{max_separate_value + 1}+{suffix}'
    return d