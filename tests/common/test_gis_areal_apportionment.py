""" Tests for common.gis.areal_apportionment. """

from copy import deepcopy
import geopandas as gpd
import pandas as pd
from pathlib import Path
import pytest
import pandas.testing as tm

from gtamodel_tools.common.gis import areal_apportionment


PROJSTR_NAD83UTM17 = 'EPSG:26917'
PROJSTR_COT = 'EPSG:2952'
PROJSTR_WGS84 = 'EPSG:4326'

@pytest.fixture
def from_gdf_path(testdata_path) -> Path:
    """ 
    Using the superzone definitions as the polygon system to project from. 
    """
    return testdata_path / "SZ_definition" / "SZ_definition.shp"


@pytest.fixture
def to_gdf_1_path(testdata_path) -> Path:
    """ 
    Using the superzone definitions as the polygon system to project from. 
    """
    return testdata_path / "Areal_tests" / "Areal_test_1.shp"


@pytest.fixture
def from_gdf(from_gdf_path):
    gdf = gpd.read_file(from_gdf_path)
    gdf.to_clipboard()
    gdf['population'] = [500, 200, 300]
    gdf = gdf.to_crs('EPSG:2952')
    return gdf


@pytest.fixture
def to_gdf_1(to_gdf_1_path):
    gdf = gpd.read_file(to_gdf_1_path)
    gdf = gdf.set_index('id')
    gdf = gdf.to_crs('EPSG:2952')
    return gdf


def test_areal_apportionment_inv_crs(from_gdf, to_gdf_1):
    """ Test with an invalid (non-projected) CRS. """
    test_from_gdf = deepcopy(from_gdf)  
    test_from_gdf = test_from_gdf.to_crs(PROJSTR_WGS84)
    test_to_gdf = deepcopy(to_gdf_1)  
    test_to_gdf = test_to_gdf.to_crs(PROJSTR_WGS84)
    with pytest.raises(AttributeError, 
                       match='CRS must be a projected coordinate system.'    
        ):
        test_res = areal_apportionment(
            test_from_gdf, test_to_gdf, tolerance=0.1)


def test_areal_apportionment_diff_crs(from_gdf, to_gdf_1):
    """ Test when the from_gdf and to_gdf have different CRS. """
    test_from_gdf = deepcopy(from_gdf)  
    test_from_gdf = test_from_gdf.to_crs(PROJSTR_NAD83UTM17)
    test_to_gdf = deepcopy(to_gdf_1)  
    test_to_gdf = test_to_gdf.to_crs(PROJSTR_COT)
    with pytest.raises(
            AttributeError, 
            match='CRS must match between from_gdf and to_gdf inputs.'    
    ):
        test_res = areal_apportionment(
            test_from_gdf, test_to_gdf, tolerance=0.1)

def test_areal_apportionment_intindex_togdf1(from_gdf, to_gdf_1):
    test_from_gdf = deepcopy(from_gdf)
    test_from_gdf = test_from_gdf.set_index('id_int')
    test_from_gdf = test_from_gdf.drop('id_str', axis=1)
    test_from_gdf.to_clipboard()
    test_res = areal_apportionment(test_from_gdf, to_gdf_1, tolerance=0.1)

    target_pop = test_from_gdf.loc[2]['population'] \
            * to_gdf_1.loc[1].geometry.area \
                / test_from_gdf.loc[2].geometry.area
    ref_res = pd.DataFrame(
        index=pd.Index([1], name='id'),
        columns=['population'],
        data=[target_pop]
    )
    tm.assert_frame_equal(test_res, ref_res)

