""" Tests for gtamodel_tools.common.data.round_to_totals.  """

import geopandas as gpd
from math import fabs
import numpy as np
import pandas as pd
import pandas.testing as tm
import pytest

from gtamodel_tools.common.data import round_to_totals




@pytest.fixture
def test_df():
    """ Dataframe for integer rounding tests.
    
    This dataframe makes the following tests
    col1: even progression of decimal component, sum is 279.5
    col2: all integers, cannot be modified, sum is 275
    col3: all decimal components are the same, hence will all be modified
          or none will be. Sum is 275.7
    col4: all decimal components near 1, sum is 167.999
    col5: adds negative numbers to random column, sum is -0.46

    """
    yield pd.DataFrame(
        index=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'],
        columns=['col1', 'col2', 'col3', 'col4', 'col5'],
        data=[
            [ 5.0,  5,  5.5,  20.9999, 20.46],
            [10.1, 10, 10.5, 17.9999, -17.04],
            [15.2, 15, 15.5, 19.9999,  19.92],
            [20.3, 20, 20.5, 17.9999, -17.42],
            [25.4, 25, 25.5, 12.9999,  12.13],
            [30.5, 30, 30.5, 18.9999, -18.64],
            [35.6, 35, 35.5, 16.9999,  16.54],
            [40.7, 40, 40.5, 12.9999, -12.77],
            [45.8, 45, 45.5, 12.9999,  12.28],
            [50.9, 50, 50.5, 15.9999, -15.92]
        ]
    )

def test_float_total(test_df):
    with pytest.raises(
            AttributeError, 
            match='This method expects total argument to be an integer.'):
        df = round_to_totals(test_df, {'col1': 281.5})

def test_col1_sum_279(test_df):
    exp_sum = 279

    ref_df = test_df.copy()
    ref_df['col1'] = [5, 10, 15, 20, 25, 30, 36, 41, 46, 51]
    ref_df = ref_df.astype({"col1": np.int64})
    df = round_to_totals(test_df, {'col1': exp_sum})
    assert df['col1'].sum() == exp_sum
    tm.assert_frame_equal(df, ref_df)

def test_col1_sum_277(test_df):
    exp_sum = 277

    ref_df = test_df.copy()
    ref_df['col1'] = [5, 10, 15, 20, 25, 30, 35, 40, 46, 51]
    ref_df = ref_df.astype({"col1": np.int64})
    df = round_to_totals(test_df, {'col1': exp_sum})
    assert df['col1'].sum() == exp_sum
    tm.assert_frame_equal(df, ref_df)


def test_col1_sum_274(test_df):
    exp_sum = 274
    with pytest.raises(
            AttributeError, 
            match=f'Total {exp_sum} cannot be achieved by rounding column col1.'):
        df = round_to_totals(test_df, {'col1': 274})

def test_col1_sum_282(test_df):
    exp_sum = 282

    ref_df = test_df.copy()
    ref_df['col1'] = [5, 10, 15, 21, 26, 31, 36, 41, 46, 51]
    ref_df = ref_df.astype({"col1": np.int64})

    df = round_to_totals(test_df, {'col1': exp_sum})
    assert df['col1'].sum() == exp_sum
    tm.assert_frame_equal(df, ref_df)

def test_col1_sum_285(test_df):
    exp_sum = 285
    with pytest.raises(
            AttributeError, 
            match=f'Total {exp_sum} cannot be achieved by rounding column col1.'):
        df = round_to_totals(test_df, {'col1': exp_sum})

def test_col2(test_df):
    # This column is all integers, and hence cannot get modified.
    with pytest.raises(RuntimeError, match='Threshold exceeds allowed bounds.'):
        df = round_to_totals(test_df, {'col2': 277})

def test_col3(test_df):
    # This column all has same decimal portion, cannot reach target.
    total=274
    col='col3'
    match_str = f"Total {total} cannot be achieved by rounding column {col}."
    test_df.to_clipboard()
    with pytest.raises(AttributeError, match=match_str):
        df = round_to_totals(test_df, {col: total})

def test_col5_sum_minus_3(test_df):
    ''' Test 1 of negative numbers, which have to be treated a bit different.'''
    exp_sum = -3
    ref_df = test_df.copy()
    ref_df['col5'] = [20, -17, 20, -18, 12, -19, 16, -13, 12, -16]
    ref_df = ref_df.astype({"col5": np.int64})

    df = round_to_totals(test_df, {'col5': exp_sum})
    assert df['col5'].sum() == exp_sum
    tm.assert_frame_equal(df, ref_df)

def test_col5_sum_plus_3(test_df):
    ''' Test 2 of negative numbers, which have to be treated a bit different.'''
    exp_sum = 3
    ref_df = test_df.copy()
    ref_df['col5'] = [21, -17, 20, -17, 12, -18, 17, -12, 13, -16]
    ref_df = ref_df.astype({"col5": np.int64})

    df = round_to_totals(test_df, {'col5': exp_sum})
    assert df['col5'].sum() == exp_sum
    tm.assert_frame_equal(df, ref_df)

def test_cols_1_5(test_df):
    ''' Test with two columns. '''
    col1_sum = 282
    col5_sum = 3
    ref_df = test_df.copy()
    ref_df['col1'] = [5, 10, 15, 21, 26, 31, 36, 41, 46, 51]
    ref_df['col5'] = [21, -17, 20, -17, 12, -18, 17, -12, 13, -16]
    ref_df = ref_df.astype({"col1": np.int64, "col5": np.int64})

    df = round_to_totals(test_df, {'col1': col1_sum, 'col5': col5_sum })
    assert df['col1'].sum() == col1_sum
    assert df['col5'].sum() == col5_sum
    tm.assert_frame_equal(df, ref_df)