""" Tests for validation.preprocess_traffic_counts.toronto_midblock_counts. """

from datetime import date
import geopandas as gpd
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

from gtamodel_tools.common.gis import calculate_direction, find_ls_vertex_by_index
import gtamodel_tools.common.tcl as gis_tcl
from gtamodel_tools.validation.preprocess_traffic_counts.toronto_midblock_counts \
    import read_midblock_counts, read_midblock_volume_counts, \
        read_midblock_speedvolume_counts, read_midblock_classvolume_counts

from gtamodel_tools.enums.common import TIME_PERIODS as TPS

idx = pd.IndexSlice

nan = np.nan


@pytest.fixture
def tcl_midblock_path(testdata_path) -> Path:
    return testdata_path / 'Counts' / 'Toronto_midblock_counts'


@pytest.fixture
def tcl_midblock(tcl_midblock_path) -> gpd.GeoDataFrame:
    fp = tcl_midblock_path / 'tcl_trimmed_testmidblock_counts.gpkg'
    return gis_tcl.read_tcl(fp, include_direction_fields=True)


@pytest.fixture
def ref_cnts_stn_1143576() -> pd.DataFrame:

    # This dataset has been manually verified from the counts file
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
    return pd.DataFrame(
        index=mi,
        columns=[
            'vtot_amper', 'vtot_ampkhr', 'vtot_mdper', 'vtot_mdpkhr', 
            'vtot_pmper', 'vtot_pmpkhr', 'vtot_evper', 'vtot_evpkhr', 
            'vtot_onper', 'vtot_onpkhr', 'vtot_weekday', 'vtot_weekend'
        ],
        data=[
            [674, 319, 2301, 440, 2228, 632, 1729, 447, 659, 182, 7591, nan],
            [647, 314, 2302, 476, 2277, 672, 1756, 409, 636, 194, 7618, nan],
            [701, 323, 2194, 445, 2183, 635, 1899, 453, 621, 160, 7598, nan],
            [700, 308, 2354, 484, 2391, 710, 1791, 421, 737, 212, 7973, nan],
            [674, 305, 2369, 453, 2225, 680, 2098, 480, 846, 206, 8212, nan],
            [nan, nan,  nan, nan,  nan, nan,  nan, nan, nan, nan,  nan, 10110],
            [nan, nan,  nan, nan,  nan, nan,  nan, nan, nan, nan,  nan,  9226],
        ],
        dtype=np.float32
    )


def check_midblock_1station(stns, ref_df, tcl_midblock, stn_id):
    stn = stns.loc[idx[:, str(stn_id), :], :].iloc[0]
    ref_df = ref_df.loc[ref_df['centreline_id'] == int(stn_id)].copy()
    first_row = ref_df.iloc[0]
    ls = tcl_midblock.at[stn_id, 'geometry']

    assert np.isclose(stn['latitude'], first_row['latitude'])
    assert np.isclose(stn['longitude'], first_row['longitude'])
    assert stn['description'] == first_row['location_name']

    # Check the geometry
    stn_dir = stn.name[2]
    first_pt = find_ls_vertex_by_index(ls, 0)
    last_pt = find_ls_vertex_by_index(ls, -1)
    ft_dir = calculate_direction(first_pt, last_pt, 17)
    if ft_dir == stn_dir:
        assert stn['geometry'] == ls
    else:
        assert stn['geometry'] == ls.reverse()


def test_toronto_midblock_volume_only_1cnt(
        tcl_midblock_path, tcl_midblock, ref_cnts_stn_1143576):
    fp = tcl_midblock_path / 'svc_raw_data_volume_2015_2019.csv_trimmed.csv'
    ref_df = pd.read_csv(fp)
    stns, cnts = read_midblock_volume_counts(fp, tcl_midblock)
    stn_id = 1143576

    check_midblock_1station(stns, ref_df, tcl_midblock, stn_id)
    # Limit test test to one station and totals-only columns
    cnts = pd.DataFrame(
        cnts.loc[idx[:, str(stn_id), :, :], ref_cnts_stn_1143576.columns]
    )
    tm.assert_frame_equal(cnts, ref_cnts_stn_1143576)


def test_toronto_midblock_volume_only(tcl_midblock_path, tcl_midblock):
    fp = tcl_midblock_path / 'svc_raw_data_volume_2015_2019.csv_trimmed.csv'
    ref_df = pd.read_csv(fp)
    stn_ids = np.sort(ref_df['centreline_id'].unique())
    stns, cnts = read_midblock_volume_counts(fp, tcl_midblock)
    for stn_id in stn_ids:
        check_midblock_1station(
            stns, ref_df, tcl_midblock, stn_id)
