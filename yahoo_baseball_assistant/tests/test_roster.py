#!/usr/bin/python

import pandas as pd
import numpy as np
import pytest
from conftest import RBLDR_COLS


def test_fit_empty(bldr, empty_roster):
    plyr = pd.Series(["Joe", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    print(df)
    assert(len(df.index) == 1)
    assert(df.at[0, 'selected_position'] == 'C')


def test_fit_pick_2nd_pos(bldr, empty_roster):
    plyr = pd.Series(["Jack", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr.at['name'] = "Kyle"
    df = bldr.fit_if_space(df, plyr)
    print(df)
    assert(len(df.index) == 2)
    assert(df.at[0, 'selected_position'] == 'C')
    assert(df.at[0, 'name'] == 'Jack')
    assert(df.at[1, 'selected_position'] == '1B')
    assert(df.at[1, 'name'] == 'Kyle')


def test_fit_move_multi_pos(bldr, empty_roster):
    plyr = pd.Series(["Cecil", ['C', '1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    assert(len(df.index) == 1)
    assert(df.at[0, 'selected_position'] == 'C')
    plyr = pd.Series(["Ernie", ['C'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 2)
    assert(df.at[0, 'selected_position'] == '1B')
    assert(df.at[0, 'name'] == 'Cecil')
    assert(df.at[1, 'selected_position'] == 'C')
    assert(df.at[1, 'name'] == 'Ernie')
    plyr = pd.Series(["Fred", ['1B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 3)
    assert(df.at[0, 'selected_position'] == '3B')
    assert(df.at[1, 'selected_position'] == 'C')
    assert(df.at[2, 'selected_position'] == '1B')
    assert(df.at[2, 'name'] == 'Fred')
    plyr = pd.Series(["George", ['LF', 'RF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 4)
    assert(df.at[3, 'selected_position'] == 'LF')
    assert(df.at[3, 'name'] == 'George')
    plyr = pd.Series(["Rance", ['3B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 5)
    assert(df.at[0, 'selected_position'] == 'LF')
    assert(df.at[0, 'name'] == 'Cecil')
    assert(df.at[3, 'selected_position'] == 'RF')
    assert(df.at[3, 'name'] == 'George')
    assert(df.at[4, 'selected_position'] == '3B')
    assert(df.at[4, 'name'] == 'Rance')


def test_fit_failure(bldr, empty_roster):
    plyr = pd.Series(["Cecil", ['1B', '3B', 'LF', 'C'], np.nan],
                     index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    assert(len(df.index) == 1)
    plyr = pd.Series(["Fred", ['1B', 'LF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 2)
    plyr = pd.Series(["Rance", ['3B', '2B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 3)
    plyr = pd.Series(["Domaso", ['2B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 4)
    plyr = pd.Series(["George", ['LF', 'RF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 5)
    plyr = pd.Series(["Jesse", ['RF', 'CF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(len(df.index) == 6)
    plyr = pd.Series(["Lloyd", ['CF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    print(df)
    assert(len(df.index) == 7)
    assert(df.at[0, 'name'] == 'Cecil')
    assert(df.at[0, 'selected_position'] == 'C')
    assert(df.at[1, 'name'] == 'Fred')
    assert(df.at[1, 'selected_position'] == '1B')
    assert(df.at[2, 'name'] == 'Rance')
    assert(df.at[2, 'selected_position'] == '3B')
    assert(df.at[3, 'name'] == 'Domaso')
    assert(df.at[3, 'selected_position'] == '2B')
    assert(df.at[4, 'name'] == 'George')
    assert(df.at[4, 'selected_position'] == 'LF')
    assert(df.at[5, 'name'] == 'Jesse')
    assert(df.at[5, 'selected_position'] == 'RF')
    assert(df.at[6, 'name'] == 'Lloyd')
    assert(df.at[6, 'selected_position'] == 'CF')
    plyr = pd.Series(["Ernie", ['C', '1B'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        df = bldr.fit_if_space(df, plyr)


def test_fit_failure_cycles(bldr, empty_roster):
    plyr = pd.Series(["Cecil", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Rance", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Garth", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["George", ['LF'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        df = bldr.fit_if_space(df, plyr)
    print(df)
    assert(len(df.index) == 3)
    assert(df.at[0, 'name'] == 'Cecil')
    assert(df.at[0, 'selected_position'] == '1B')
    assert(df.at[1, 'name'] == 'Rance')
    assert(df.at[1, 'selected_position'] == '3B')
    assert(df.at[2, 'name'] == 'Garth')
    assert(df.at[2, 'selected_position'] == 'LF')


def test_fit_enumerate_3(bldr, empty_roster):
    plyr = pd.Series(["Ben", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Rance", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Garth", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(df.at[0, 'name'] == 'Ben')
    assert(df.at[0, 'selected_position'] == '1B')
    assert(df.at[1, 'name'] == 'Rance')
    assert(df.at[1, 'selected_position'] == '3B')
    assert(df.at[2, 'name'] == 'Garth')
    assert(df.at[2, 'selected_position'] == 'LF')
    plyr = pd.Series(["George", ['LF'], np.nan], index=RBLDR_COLS)
    itr = bldr.enumerate_fit(df, plyr)
    edf = next(itr)
    print(edf)
    assert(edf.at[0, 'name'] == 'Ben')
    assert(np.isnan(edf.at[0, 'selected_position']))
    assert(edf.at[1, 'name'] == 'Rance')
    assert(edf.at[1, 'selected_position'] == '3B')
    assert(edf.at[2, 'name'] == 'Garth')
    assert(edf.at[2, 'selected_position'] == '1B')
    assert(edf.at[3, 'name'] == 'George')
    assert(edf.at[3, 'selected_position'] == 'LF')
    edf = next(itr)
    print(edf)
    assert(edf.at[0, 'name'] == 'Ben')
    assert(edf.at[0, 'selected_position'] == '1B')
    assert(edf.at[1, 'name'] == 'Rance')
    assert(np.isnan(edf.at[1, 'selected_position']))
    assert(edf.at[2, 'name'] == 'Garth')
    assert(edf.at[2, 'selected_position'] == '3B')
    assert(edf.at[3, 'name'] == 'George')
    assert(edf.at[3, 'selected_position'] == 'LF')
    edf = next(itr)
    print(edf)
    assert(edf.at[0, 'name'] == 'Ben')
    assert(edf.at[0, 'selected_position'] == '1B')
    assert(edf.at[1, 'name'] == 'Rance')
    assert(edf.at[1, 'selected_position'] == '3B')
    assert(edf.at[2, 'name'] == 'Garth')
    assert(np.isnan(edf.at[2, 'selected_position']))
    assert(edf.at[3, 'name'] == 'George')
    assert(edf.at[3, 'selected_position'] == 'LF')
    with pytest.raises(StopIteration):
        edf = next(itr)


def test_fit_enumerate_2(bldr, empty_roster):
    plyr = pd.Series(["Paul", ['3B'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Robin", ['CF', 'SS'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Gorman", ['CF'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    assert(df.at[0, 'name'] == 'Paul')
    assert(df.at[0, 'selected_position'] == '3B')
    assert(df.at[1, 'name'] == 'Robin')
    assert(df.at[1, 'selected_position'] == 'SS')
    assert(df.at[2, 'name'] == 'Gorman')
    assert(df.at[2, 'selected_position'] == 'CF')
    plyr = pd.Series(["Kevin", ['CF', 'SS'], np.nan], index=RBLDR_COLS)
    itr = bldr.enumerate_fit(df, plyr)
    edf = next(itr)
    print(edf)
    assert(edf.at[0, 'selected_position'] == '3B')
    assert(np.isnan(edf.at[1, 'selected_position']))
    assert(edf.at[2, 'selected_position'] == 'CF')
    assert(edf.at[3, 'selected_position'] == 'SS')
    edf = next(itr)
    print(edf)
    assert(edf.at[0, 'selected_position'] == '3B')
    assert(edf.at[1, 'selected_position'] == 'SS')
    assert(np.isnan(edf.at[2, 'selected_position']))
    assert(edf.at[3, 'selected_position'] == 'CF')
    with pytest.raises(StopIteration):
        edf = next(itr)


def test_fit_with_duplicate_positions(bldr, empty_roster):
    plyr = pd.Series(["Stieb", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Clancy", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Cerutti", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Flanigan", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Alexander", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Fernandez", ['SP'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Claudell", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    print(df)
    assert(len(df.index) == 6)
    assert(df.at[5, 'name'] == 'Claudell')
    assert(df.at[5, 'selected_position'] == 'RP')


def test_fit_with_multiple_duplicate_positions(bldr, empty_roster):
    plyr = pd.Series(["Stieb", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Clancy", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Cerutti", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Flanigan", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Alexander", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    print(df)
    assert(len(df[df.selected_position == 'SP'].index) == 5)
    plyr = pd.Series(["Fernandez", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Claudell", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Key", ['SP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Guzman", ['SP'], np.nan], index=RBLDR_COLS)
    print(df)
    assert(len(df[df.selected_position == 'RP'].index) == 3)
    with pytest.raises(LookupError):
        df = bldr.fit_if_space(df, plyr)


def test_fit_enumerate_dup_position(bldr, empty_roster):
    plyr = pd.Series(["Henke", ['RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Ward", ['RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Timlin", ['RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Eichorn", ['RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Cox", ['RP'], np.nan], index=RBLDR_COLS)
    df = bldr.fit_if_space(df, plyr)
    plyr = pd.Series(["Castillo", ['RP'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        df = bldr.fit_if_space(df, plyr)
    itr = bldr.enumerate_fit(df, plyr)

    def names(df):
        return [e['name'] for i, e in
                df[df.selected_position.notnull()].iterrows()]

    edf = next(itr)
    print(edf)
    assert(names(edf) == ['Ward', 'Timlin', 'Eichorn', 'Cox', 'Castillo'])
    edf = next(itr)
    print(edf)
    assert(names(edf) == ['Henke', 'Timlin', 'Eichorn', 'Cox', 'Castillo'])
    edf = next(itr)
    print(edf)
    assert(names(edf) == ['Henke', 'Ward', 'Eichorn', 'Cox', 'Castillo'])
    edf = next(itr)
    print(edf)
    assert(names(edf) == ['Henke', 'Ward', 'Timlin', 'Cox', 'Castillo'])
    edf = next(itr)
    print(edf)
    assert(names(edf) == ['Henke', 'Ward', 'Timlin', 'Eichorn', 'Castillo'])
    with pytest.raises(StopIteration):
        edf = next(itr)


def test_selector_rank_hitters(fake_player_selector):
    ppool = fake_player_selector.ppool
    fake_player_selector.rank(['HR', 'OBP'])
    df = ppool.sort_values(by=['rank'], ascending=False)
    print(df)
    assert(len(ppool.index) == 15)
    itr = df.iterrows()
    (i, p) = next(itr)
    assert(p['name'] == 'McGriff')
    (i, p) = next(itr)
    assert(p['name'] == 'Gruber')
    (i, p) = next(itr)
    assert(p['name'] == 'Olerud')
    (i, p) = next(itr)
    assert(p['name'] == 'Borders')


def test_selector_rank_pitchers(fake_player_selector):
    ppool = fake_player_selector.ppool
    fake_player_selector.rank(['W', 'ERA'])
    df = ppool.sort_values(by=['rank'], ascending=False)
    print(df)
    assert(len(ppool.index) == 15)
    itr = df.iterrows()
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Steib')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Key')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Wells')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Stottlemyre')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Cerutti')


def test_selector_hitters_iter(fake_player_selector):
    fake_player_selector.rank(['HR', 'OBP'])
    expected_order = ["McGriff", "Gruber", "Olerud", "Borders", "Bell",
                      "Felix", "Fernandez", "Lee", "Hill", "Wilson"]
    for exp, plyr in zip(expected_order, fake_player_selector.select()):
        print(plyr)
        assert(plyr['name'] == exp)


def test_selector_pitchers_iter(fake_player_selector):
    fake_player_selector.rank(['ERA', 'W'])
    expected_order = ["Steib", "Key", "Wells", "Stottlemyre", "Cerutti"]
    for exp, plyr in zip(expected_order, fake_player_selector.select()):
        print(plyr)
        assert(plyr['name'] == exp)
