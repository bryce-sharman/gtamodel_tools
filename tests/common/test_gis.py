import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt
import pytest
import pandas.testing as tm

from tmg_tdm_tools.common.gis import areal_apportionment

@pytest.fixture
def from_gdf():
    from_df = pd.DataFrame(
        index=['a', 'b', 'c'],
        columns=['coordinates', 'population', 'area'],
        data=[
            ['POLYGON((0 0, 10500 0, 10500 20000, 0 20000, 0 0))', 126, 200],
            ['POLYGON((10500 10000, 30000 10000, 30000 20000, 10500 20000, 10500 10000))', 27, 200],
            ['POLYGON((10500 0, 30000 0, 30000 10000, 10500 10000, 10500 0))', 163, 200]
        ]
    )

    from_df['geometry'] = from_df['coordinates'].apply(wkt.loads)
    from_df = from_df.drop('coordinates', axis=1)
    from_gdf = gpd.GeoDataFrame(from_df, geometry='geometry')
    from_gdf.crs = "epsg:2952"
    yield from_gdf


@pytest.fixture
def to_gdf():
    to_df = pd.DataFrame(
        index=pd.Series([1, 2, 3], dtype=np.uint32),
        columns=['coordinates'],
        data=[
            'POLYGON((0 0, 10000 0, 10000 20000, 0 20000, 0 0))',
            'POLYGON((10000 0, 20000 0, 20000 12500, 10000 12500, 10000 0))',
            'POLYGON((20000 0, 30000 0, 30000 20000, 10000 20000, 10000 12500, 20000 12500, 20000 0))'
        ]
    )
    to_df['geometry'] = to_df['coordinates'].apply(wkt.loads)
    to_df = to_df.drop('coordinates', axis=1)
    to_gdf = gpd.GeoDataFrame(to_df, geometry='geometry')
    to_gdf.crs = "epsg:2952"
    yield to_gdf

def test_areal_apportionment_wtol_nocols(from_gdf, to_gdf):
    ref_gdf = to_gdf.copy()
    ref_gdf['area'] = [200.000000, 121.794872, 278.205128]
    ref_gdf['population'] = [126.000000, 82.698718, 107.301282]
    gdf = areal_apportionment(from_gdf, to_gdf, tolerance=0.1)
    tm.assert_frame_equal(gdf, ref_gdf)

def test_areal_apportionment_wtol_poponly(from_gdf, to_gdf):
    ref_gdf = to_gdf.copy()
    ref_gdf['population'] = [126.000000, 82.698718, 107.301282]
    gdf = areal_apportionment(
        from_gdf, to_gdf, columns=["population"], tolerance=0.1)
    tm.assert_frame_equal(gdf, ref_gdf)

def test_area_apportionment_notol_poponly(from_gdf, to_gdf):
    ref_gdf = to_gdf.copy()
    ref_gdf['population'] = [120.000000, 86.448718, 109.551282]
    gdf = areal_apportionment(
        from_gdf, to_gdf, columns=["population"], tolerance=0.002)
    tm.assert_frame_equal(gdf, ref_gdf)

def test_area_apportionment_notol(from_gdf, to_gdf):
    ref_gdf = to_gdf.copy()
    ref_gdf['area'] = [190.476190, 127.747253, 281.776558]
    ref_gdf['population'] = [120.000000, 86.448718, 109.551282]
    gdf = areal_apportionment(
        from_gdf, to_gdf, tolerance=0.002)
    tm.assert_frame_equal(gdf, ref_gdf)

