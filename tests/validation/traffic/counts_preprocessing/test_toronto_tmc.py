""" 
Tests for validation.preprocess_traffic_counts.toronto_turning_movement_counts. 
"""

from datetime import date
import geopandas as gpd
import numpy as np
import pandas as pd
import pandas.testing as tm
from pathlib import Path
import pytest

import gtamodel_tools.common.tcl as gis_tcl
from gtamodel_tools.validation.preprocess_traffic_counts.toronto_turning_movement_counts \
    import read_turning_movement_counts_from_file, _read_intersection_legs

idx = pd.IndexSlice
nan = np.nan

tot_cols = [
    'vtot_amper', 'vtot_ampkhr', 'vtot_mdper', 'vtot_mdpkhr', 
    'vtot_pmper', 'vtot_pmpkhr', 'vtot_evper', 'vtot_evpkhr', 
    'vtot_onper', 'vtot_onpkhr', 'vtot_weekday', 'vtot_weekend',
    'vtot_max15min'
]

car_cols = [
    'vcar_amper', 'vcar_ampkhr', 'vcar_mdper', 'vcar_mdpkhr', 
    'vcar_pmper', 'vcar_pmpkhr', 'vcar_evper', 'vcar_evpkhr', 
    'vcar_onper', 'vcar_onpkhr', 'vcar_weekday', 'vcar_weekend'
]

bus_cols = [
    'vbus_amper', 'vbus_ampkhr', 'vbus_mdper', 'vbus_mdpkhr', 
    'vbus_pmper', 'vbus_pmpkhr', 'vbus_evper', 'vbus_evpkhr', 
    'vbus_onper', 'vbus_onpkhr', 'vbus_weekday', 'vbus_weekend'
]

trk_cols = [
    'vtrk_amper', 'vtrk_ampkhr', 'vtrk_mdper', 'vtrk_mdpkhr', 
    'vtrk_pmper', 'vtrk_pmpkhr', 'vtrk_evper', 'vtrk_evpkhr', 
    'vtrk_onper', 'vtrk_onpkhr', 'vtrk_weekday', 'vtrk_weekend'
]


@pytest.fixture
def to_tmc_path(testdata_path) -> Path:
    return testdata_path / 'Counts' / 'Toronto_turningmovement_counts'


@pytest.fixture
def tcl_totmc_13465260(to_tmc_path) ->gpd.GeoDataFrame:
    # Test TCL file for station 13465260 (Dufferin St / Bloor St W)
    tcl_fp = to_tmc_path / 'tcl_testtmc_13465260.gpkg'
    return gis_tcl.read_tcl(tcl_fp, include_direction_fields=True)


@pytest.fixture
def tcl_totmc_13464621(to_tmc_path) ->gpd.GeoDataFrame:
    # Test TCL file for station 13465260 (Dufferin St / Bloor St W)
    tcl_fp = to_tmc_path / 'tcl_testtmc_13464621.gpkg'
    return gis_tcl.read_tcl(tcl_fp, include_direction_fields=True)


@pytest.fixture
def tmc_13465260_fp(to_tmc_path) -> gpd.GeoDataFrame:
    # Test TMC filepath for station 13465260 (Dufferin St / Bloor St W)
    return to_tmc_path / "tmc_raw_data_2020_2029_13465260.csv"


@pytest.fixture
def tmc_13464621_fp(to_tmc_path) -> gpd.GeoDataFrame:
    # Test TMC filepath for station 13465260 (Dufferin St / Bloor St W)
    return to_tmc_path / "tmc_raw_data_2020_2029_13464621.csv"


@pytest.fixture
def tmc_13465260(tmc_13465260_fp) -> pd.DataFrame:
    # Test TMC file for station 13465260 (Dufferin St / Bloor St W)
    df = pd.read_csv(tmc_13465260_fp)
    return df


@pytest.fixture
def tmc_13464621(tmc_13464621_fp) -> pd.DataFrame:
    # Test TMC file for station 13465260 (Dufferin St / Bloor St W)
    df = pd.read_csv(tmc_13464621_fp)
    return df


@pytest.fixture
def tcl_leg_dir_13465260_fp(to_tmc_path) -> Path:
    # Test intersection - leg direction file for station 13465260 
    # (Dufferin St / Bloor St W)
    return to_tmc_path / 'centreline_leg_directions_13465260.csv'


@pytest.fixture
def tcl_leg_dir_13464621_fp(to_tmc_path) -> Path:
    # Test intersection - leg direction file for station 13465260 
    # (Dufferin St / Bloor St W)
    return to_tmc_path / 'centreline_leg_directions_13464621.csv'


@pytest.fixture
def ref_cnts_13465260(
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """ 
    Reference processed TMC counts for station 13465260 
    (Dufferin St / Bloor St W). These have all been manually checked. 
    """

    mi = pd.MultiIndex.from_arrays([
            ['TTMC'] * 24,
            ['10865133']*6 + ['14011415']*6 + ['14018251']*6 + ['6710177']*6,
            ['EB']*3 + ['WB']*3 + ['NB']*3 + ['SB']*3 + ['NB']*3 + ['SB']*3 + ['EB']*3 + ['WB']*3,
            [date(2024,9,5), date(2025,6,25), date(2025,9,16)] * 8
        ],
        names=['source', 'station_id', 'direction', 'date']
    )

    # All modes (total)
    ref_tot = pd.DataFrame(
        index=mi,
        columns=tot_cols,
        data=[
            [1464,603,3100,577,1894,527,nan,521,nan,nan,nan,nan,172],
            [1333,532,2862,516,1857,488,nan,438,nan,nan,nan,nan,141],
            [1403,536,2474,451,1816,494,nan,429,nan,nan,nan,nan,143],
            [1055,466,2597,523,2030,568,nan,531,nan,nan,nan,nan,148],
            [1143,490,2831,581,2150,565,nan,509,nan,nan,nan,nan,168],
            [1163,483,2494,471,1966,529,nan,482,nan,nan,nan,nan,148],
            [1066,488,2904,584,2796,764,nan,594,nan,nan,nan,nan,203],
            [1051,476,3008,623,2646,688,nan,547,nan,nan,nan,nan,193],
            [1181,508,3007,651,2724,713,nan,554,nan,nan,nan,nan,187],
            [1559,672,3159,615,2297,637,nan,593,nan,nan,nan,nan,184],
            [1276,474,3065,542,2596,712,nan,600,nan,nan,nan,nan,195],
            [1500,600,3005,601,2182,603,nan,511,nan,nan,nan,nan,161],
            [1041,492,3266,653,2721,729,nan,636,nan,nan,nan,nan,189],
            [1059,478,3352,683,2683,699,nan,595,nan,nan,nan,nan,204],
            [1105,479,3458,698,2760,709,nan,576,nan,nan,nan,nan,197],
            [1674,750,3619,703,2735,753,nan,669,nan,nan,nan,nan,211],
            [1494,579,3751,689,3233,879,nan,712,nan,nan,nan,nan,238],
            [1704,732,3667,713,2765,764,nan,598,nan,nan,nan,nan,207],
            [1471,607,2835,524,1949,536,nan,459,nan,nan,nan,nan,168],
            [1348,535,2640,492,1812,494,nan,396,nan,nan,nan,nan,137],
            [1489,575,2072,398,1779,505,nan,397,nan,nan,nan,nan,158],
            [ 922,389,2234,433,1572,444,nan,435,nan,nan,nan,nan,131],
            [ 948,390,2267,449,1505,430,nan,403,nan,nan,nan,nan,129],
            [ 969,374,1881,393,1382,360,nan,385,nan,nan,nan,nan,109],
        ]
    )

    # Car mode
    ref_car = pd.DataFrame(
        index=mi,
        columns=car_cols,
        data=[
            [1408,584,2971,561,1867,522,nan,515,nan,nan,nan,nan],
            [1274,509,2753,497,1823,484,nan,435,nan,nan,nan,nan],
            [1335,512,2371,438,1793,493,nan,428,nan,nan,nan,nan],
            [1004,442,2492,508,1980,551,nan,527,nan,nan,nan,nan],
            [1090,467,2709,554,2098,548,nan,504,nan,nan,nan,nan],
            [1099,448,2380,453,1923,516,nan,479,nan,nan,nan,nan],
            [985, 453,2715,541,2681,739,nan,577,nan,nan,nan,nan],
            [976, 442,2813,586,2554,674,nan,526,nan,nan,nan,nan],
            [1104,470,2789,616,2615,686,nan,532,nan,nan,nan,nan],
            [1462,634,2928,579,2198,619,nan,574,nan,nan,nan,nan],
            [1177,434,2863,513,2516,694,nan,579,nan,nan,nan,nan],
            [1405,560,2785,555,2089,584,nan,495,nan,nan,nan,nan],
            [955, 458,3071,613,2609,703,nan,619,nan,nan,nan,nan],
            [977, 440,3151,645,2588,687,nan,574,nan,nan,nan,nan],
            [1027,442,3232,663,2652,679,nan,554,nan,nan,nan,nan],
            [1568,707,3371,661,2625,724,nan,651,nan,nan,nan,nan],
            [1378,534,3527,654,3141,859,nan,689,nan,nan,nan,nan],
            [1598,689,3423,671,2659,739,nan,582,nan,nan,nan,nan],
            [1419,589,2710,501,1920,531,nan,455,nan,nan,nan,nan],
            [1293,512,2533,470,1782,490,nan,391,nan,nan,nan,nan],
            [1425,550,1967,376,1750,500,nan,396,nan,nan,nan,nan],
            [879, 367,2144,422,1534,427,nan,432,nan,nan,nan,nan],
            [909, 372,2163,427,1466,412,nan,398,nan,nan,nan,nan],
            [919, 359,1781,374,1347,349,nan,382,nan,nan,nan,nan],
        ]
    )

    # Bus mode
    ref_bus = pd.DataFrame(
        index=mi,
        columns=bus_cols,
        dtype=np.float32,
        data=[
            [14, 7, 24,10, 9, 3,nan, 1,nan,nan,nan,nan],
            [ 8, 7, 17, 5,13, 8,nan, 0,nan,nan,nan,nan],
            [18,10, 15, 5, 8, 6,nan, 0,nan,nan,nan,nan],
            [21,12, 24, 7,10, 7,nan, 0,nan,nan,nan,nan],
            [20,12, 17, 6,17, 7,nan, 1,nan,nan,nan,nan],
            [27,17, 13, 6, 6, 4,nan, 1,nan,nan,nan,nan],
            [51,23, 96,19,65,22,nan,15,nan,nan,nan,nan],
            [53,24, 98,20,64,23,nan,19,nan,nan,nan,nan],
            [47,22,101,19,71,22,nan,20,nan,nan,nan,nan],
            [53,23,100,20,70,22,nan,16,nan,nan,nan,nan],
            [46,19,108,21,60,21,nan,17,nan,nan,nan,nan],
            [47,24,105,21,68,20,nan,13,nan,nan,nan,nan],
            [49,21,101,19,65,22,nan,16,nan,nan,nan,nan],
            [50,21,102,22,61,22,nan,19,nan,nan,nan,nan],
            [44,20,107,21,71,21,nan,20,nan,nan,nan,nan],
            [56,26,104,22,70,21,nan,16,nan,nan,nan,nan],
            [52,23,111,22,61,22,nan,18,nan,nan,nan,nan],
            [50,24,107,22,72,20,nan,13,nan,nan,nan,nan],
            [18,11, 19, 8, 9, 4,nan, 0,nan,nan,nan,nan],
            [11, 8, 15, 5,12, 8,nan, 1,nan,nan,nan,nan],
            [19,11, 12, 6,12, 8,nan, 0,nan,nan,nan,nan],
            [20,11, 20, 6,10, 8,nan, 0,nan,nan,nan,nan],
            [14, 9, 16, 8,12, 5,nan, 1,nan,nan,nan,nan],
            [22,15, 14, 7, 6, 5,nan, 1,nan,nan,nan,nan],
        ]
    )

    # Truck mode
    ref_trk = pd.DataFrame(
        index=mi,
        columns=trk_cols,
        dtype=np.float32,
        data=[
            [42,17,105,29, 18, 8,nan,5,nan,nan,nan,nan],				
            [51,25, 92,22, 21, 9,nan,3,nan,nan,nan,nan],				
            [50,23, 88,23, 15, 7,nan,1,nan,nan,nan,nan],				
            [30,17, 81,18, 40,15,nan,4,nan,nan,nan,nan],				
            [33,16,105,24, 35,15,nan,4,nan,nan,nan,nan],				
            [37,19,101,23, 37,16,nan,2,nan,nan,nan,nan],				
            [30,15, 93,25, 50,21,nan,2,nan,nan,nan,nan],				
            [22,10, 97,25, 28,14,nan,2,nan,nan,nan,nan],				
            [30,17,117,27, 38,16,nan,2,nan,nan,nan,nan],				
            [44,17,131,28, 29,14,nan,3,nan,nan,nan,nan],				
            [53,23, 94,19, 20,10,nan,4,nan,nan,nan,nan],				
            [48,24,115,30, 25,10,nan,3,nan,nan,nan,nan],				
            [37,16, 94,24, 47,21,nan,1,nan,nan,nan,nan],				
            [32,17, 99,26, 34,18,nan,2,nan,nan,nan,nan],				
            [34,19,119,28, 37,16,nan,2,nan,nan,nan,nan],				
            [50,19,144,32, 40,17,nan,2,nan,nan,nan,nan],				
            [64,26,113,25, 31,12,nan,5,nan,nan,nan,nan],				
            [56,24,137,33, 34,14,nan,3,nan,nan,nan,nan],				
            [34,15,106,30, 20,10,nan,4,nan,nan,nan,nan],				
            [44,19, 92,24, 18, 8,nan,4,nan,nan,nan,nan],				
            [45,20, 93,25, 17, 7,nan,1,nan,nan,nan,nan],				
            [23,14, 70,17, 28,11,nan,3,nan,nan,nan,nan],				
            [25,13, 88,21, 27,13,nan,4,nan,nan,nan,nan],				
            [28,13, 86,19, 29,12,nan,2,nan,nan,nan,nan],
        ]
    )
    return ref_tot, ref_car, ref_bus, ref_trk

@pytest.fixture
def ref_cnts_13464621(
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """ 
    Reference processed TMC counts for station 13464621 
    (Dupont St / Dundas St W). This is a count for which 24-hour counts are
    recorded. These values have all been manually checked. 
    """
    mi = pd.MultiIndex.from_arrays([
            ['TTMC'] * 6,
            ['1143283']*2 + ['1143284']*2 + ['30140709']*2,
            ['EB', 'WB', 'NB', 'SB', 'NB', 'SB'],
            [date(2023,9,27)] * 6
        ],
        names=['source', 'station_id', 'direction', 'date']
    )
    ref_tot = pd.DataFrame(
        index=mi,
        columns=tot_cols,
        dtype=np.float32,
        data=[
            [2098,806,4025,730,3029,791,2201,720,559,188,11912, nan, 214],
            [1248,546,2984,577,2500,652,1840,479,492,153, 9064, nan, 175],
            [1077,470,2588,514,2107,556,1583,411,419,129, 7774, nan, 149],
            [1769,692,3231,590,2337,603,1768,586,465,166, 9570, nan, 175],
            [ 354,192, 815,157, 707,204, 442,140,104, 27, 2422, nan,  62],
            [ 196, 89, 417, 93, 408,118, 266, 77, 83, 24, 1370, nan,  34],

        ]
    )
    ref_car = pd.DataFrame(
        index=mi,
        columns=car_cols,
        dtype=np.float32,
        data=[
            [1987,760,3833,695,2972,770,2177,712,540,178, 11509,nan],
            [1195,523,2817,549,2432,641,1815,475,477,151,  8736,nan],
            [1029,451,2436,490,2047,543,1558,407,405,127,  7475,nan],
            [1668,648,3067,560,2292,595,1751,578,451,158,  9229,nan],
            [ 340,182, 785,150, 694,195, 435,138, 99, 26,  2353,nan],
            [ 187, 83, 400, 90, 399,116, 266, 77, 82, 24,  1334,nan],

        ]
    )
    ref_bus = pd.DataFrame(
        index=mi,
        columns=bus_cols,
        dtype=np.float32,
        data=[
            [29,17,36,14,31,19,13,5,9,4,118,nan],
            [17,11,32,12,21,13,15,4,8,4, 93,nan],
            [15, 9,29,11,18,11,15,4,7,3, 84,nan],
            [21,14,33,13,25,13,13,5,6,2, 98,nan],
            [ 8, 8, 3, 1, 6, 6,	0,0,3,2, 20,nan],
            [ 2, 2, 3, 2, 3, 2,	0,0,1,1,  9,nan],

        ]
    )
    ref_trk = pd.DataFrame(
        index=mi,
        columns=trk_cols,
        dtype=np.float32,
        data=[
            [82,40,156,35,26,10,11,6,10,6,285,nan],
            [36,19,135,39,47,15,10,4, 7,4,235,nan],
            [33,18,123,37,42,14,10,4, 7,4,215,nan],
            [80,40,131,29,20, 7, 4,4, 8,6,243,nan],
            [ 6, 4, 27, 8, 7, 4, 7,3, 2,1, 49,nan],
            [ 7, 4, 14, 5, 6, 3, 0,0, 0,0, 27,nan],

        ]
    )
    return ref_tot, ref_car, ref_bus, ref_trk


def test_toronto_tmc_13465260(
        tmc_13465260_fp, tcl_leg_dir_13465260_fp, tcl_totmc_13465260,
        ref_cnts_13465260
    ):
    stns, cnts = read_turning_movement_counts_from_file(
         tmc_13465260_fp, tcl_leg_dir_13465260_fp, tcl_totmc_13465260)
    cnts=cnts.sort_index()

    # Don't check the stations for now, a lot of work with less current benefit 
    # than checking the counts.
    ref_tot = ref_cnts_13465260[0]
    ref_car = ref_cnts_13465260[1]
    ref_bus = ref_cnts_13465260[2]
    ref_trk = ref_cnts_13465260[3]
    tm.assert_frame_equal(cnts[tot_cols], ref_tot, check_dtype=False)
    tm.assert_frame_equal(cnts[car_cols], ref_car, check_dtype=False)
    tm.assert_frame_equal(cnts[bus_cols], ref_bus, check_dtype=False)
    tm.assert_frame_equal(cnts[trk_cols], ref_trk, check_dtype=False)


def test_toronto_tmc_13464621(
        tmc_13464621_fp, tcl_leg_dir_13464621_fp, tcl_totmc_13464621,
        ref_cnts_13464621
    ):
    stns, cnts = read_turning_movement_counts_from_file(
         tmc_13464621_fp, tcl_leg_dir_13464621_fp, tcl_totmc_13464621)
    cnts=cnts.sort_index()

    # Don't check the stations for now, a lot of work with less current benefit 
    # than checking the counts.
    ref_tot = ref_cnts_13464621[0]
    ref_car = ref_cnts_13464621[1]
    ref_bus = ref_cnts_13464621[2]
    ref_trk = ref_cnts_13464621[3]
    tm.assert_frame_equal(cnts[tot_cols], ref_tot, check_dtype=False)
    tm.assert_frame_equal(cnts[car_cols], ref_car, check_dtype=False)
    tm.assert_frame_equal(cnts[bus_cols], ref_bus, check_dtype=False)
    tm.assert_frame_equal(cnts[trk_cols], ref_trk, check_dtype=False)