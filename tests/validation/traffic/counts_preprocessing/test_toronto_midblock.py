""" Tests for validation.preprocess_traffic_counts.toronto_midblock_counts. """

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

idx = pd.IndexSlice


@pytest.fixture
def tcl_midblock_path(testdata_path) -> Path:
    return testdata_path / 'Counts' / 'Toronto_midblock_counts'


@pytest.fixture
def tcl_midblock(tcl_midblock_path) -> gpd.GeoDataFrame:
    fp = tcl_midblock_path / 'tcl_trimmed_testmidblock_counts.gpkg'
    return gis_tcl.read_tcl(fp, include_direction_fields=True)


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

def test_toronto_midblock_volume_only_1cnt(tcl_midblock_path, tcl_midblock):
    fp = tcl_midblock_path / 'svc_raw_data_volume_2015_2019.csv_trimmed.csv'
    ref_df = pd.read_csv(fp)
    stns, cnts = read_midblock_volume_counts(fp, tcl_midblock)
    stn_id = 1143576

    check_midblock_1station(stns, ref_df, tcl_midblock, stn_id)
    print("Need to add verification of count data.")

def test_toronto_midblock_volume_only(tcl_midblock_path, tcl_midblock):
    fp = tcl_midblock_path / 'svc_raw_data_volume_2015_2019.csv_trimmed.csv'
    ref_df = pd.read_csv(fp)
    stn_ids = np.sort(ref_df['centreline_id'].unique())
    stns, cnts = read_midblock_volume_counts(fp, tcl_midblock)
    for stn_id in stn_ids:
        check_midblock_1station(
            stns, ref_df, tcl_midblock, stn_id)
