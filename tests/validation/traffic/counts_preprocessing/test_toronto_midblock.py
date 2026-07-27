""" Tests for validation.preprocess_traffic_counts.toronto_midblock_counts. """

from datetime import date
import geopandas as gpd
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest
from shapely import Point

from gtamodel_tools.common.gis import calculate_direction, \
    ensure_linestring
import gtamodel_tools.common.tcl as gis_tcl
from gtamodel_tools.validation.preprocess_traffic_counts.toronto_midblock_counts \
    import read_midblock_volume_counts, \
        read_midblock_speedvolume_counts, read_midblock_classvolume_counts

from gtamodel_tools.enums.common import TIME_PERIODS as TPS

idx = pd.IndexSlice
nan = np.nan
tot_cols = [
    'vtot_amper', 'vtot_ampkhr', 'vtot_mdper', 'vtot_mdpkhr', 
    'vtot_pmper', 'vtot_pmpkhr', 'vtot_evper', 'vtot_evpkhr', 
    'vtot_onper', 'vtot_onpkhr', 'vtot_weekday', 'vtot_weekend',
    'vtot_max15min', 'vtot_95th15min', 'vtot_98th15min'

]

@pytest.fixture
def to_midblock_path(testdata_path) -> Path:
    return testdata_path / 'Counts' / 'Toronto_midblock_counts'


@pytest.fixture
def tcl_midblock(to_midblock_path) -> gpd.GeoDataFrame:
    fp = to_midblock_path / 'tcl_trimmed_testmidblock_counts.gpkg'
    return gis_tcl.read_tcl(fp, include_direction_fields=True)


@pytest.fixture
def ref_cnts_1143576() -> pd.DataFrame:
    """ Validate counts for station 1143576.
    
    This dataset has been manually verified from the counts file.
    """ 
    mi = pd.MultiIndex.from_product(
        [
            ['TMBK'],
            ['1143576'],
            ['WB'],
            [date(2019,9,30), date(2019,10,1), date(2019,10,2), date(2019,10,3),
             date(2019,10,4), date(2019,10,5), date(2019,10,6)]
        ],
        names=['source', 'station_id', 'direction', 'date']
    )

    ref_tot = pd.DataFrame(
        index=mi,
        columns=tot_cols,
        data=[
            [674,319,2301,440,2228,632,1729,447,659,182,7591,  nan,168,149.5 ,155.7],
            [647,314,2302,476,2277,672,1756,409,636,194,7618,  nan,193,152.75,168.1],
            [701,323,2194,445,2183,635,1899,453,621,160,7598,  nan,174,146.5 ,159.1],
            [700,308,2354,484,2391,710,1791,421,737,212,7973,  nan,204,166.75,177.4],
            [674,305,2369,453,2225,680,2098,480,846,206,8212,  nan,177,144.25,167.4],
            [nan,nan, nan,nan, nan,nan, nan,nan,nan,nan, nan,10110,171,154.25,157.5],
            [nan,nan, nan,nan, nan,nan, nan,nan,nan,nan, nan, 9226,167,143.00,152.5],
        ],
        dtype=np.float32
    )
    return ref_tot


def check_midblock_1station(stns, ref_df, tcl_midblock, stn_id):
    stn = stns.loc[idx[:, str(stn_id), :], :].iloc[0]
    ref_df = ref_df.loc[ref_df['centreline_id'] == int(stn_id)].copy()
    first_row = ref_df.iloc[0]
    ls = ensure_linestring(tcl_midblock.at[stn_id, 'geometry'])

    assert np.isclose(stn['latitude'], first_row['latitude'])
    assert np.isclose(stn['longitude'], first_row['longitude'])
    assert stn['description'] == first_row['location_name']

    # Check the geometry
    stn_dir = stn.name[2]
    first_pt = Point(ls.coords[0][0], ls.coords[0][1])
    last_pt = Point(ls.coords[-1][0], ls.coords[-1][1])
    ft_dir = calculate_direction(first_pt, last_pt, 17)
    if ft_dir == stn_dir:
        assert ensure_linestring(stn['geometry']) == ls
    else:
        assert ensure_linestring(stn['geometry']) == ls.reverse()


def test_toronto_midblock_1143576(
        to_midblock_path, tcl_midblock, ref_cnts_1143576):
    fp = to_midblock_path / 'svc_raw_data_volume_2015_2019.csv_trimmed.csv'
    ref_df = pd.read_csv(fp)
    stns, cnts = read_midblock_volume_counts(fp, tcl_midblock)
    stn_id = 1143576
    cnts = cnts.loc[idx['TMBK', str(stn_id), :, :], :]
    check_midblock_1station(stns, ref_df, tcl_midblock, stn_id)
    tm.assert_frame_equal(cnts[tot_cols], ref_cnts_1143576, check_dtype=False)



def test_toronto_midblock_volume_only(to_midblock_path, tcl_midblock):
    fp = to_midblock_path / 'svc_raw_data_volume_2015_2019.csv_trimmed.csv'
    ref_df = pd.read_csv(fp)
    stn_ids = np.sort(ref_df['centreline_id'].unique())
    stns, _ = read_midblock_volume_counts(fp, tcl_midblock)
    for stn_id in stn_ids:
        check_midblock_1station(
            stns, ref_df, tcl_midblock, stn_id)
