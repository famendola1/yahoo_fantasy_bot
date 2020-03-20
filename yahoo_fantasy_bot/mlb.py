#!/bin/python

from baseball_scraper import baseball_reference, espn, fangraphs
from baseball_id import Lookup
from yahoo_fantasy_bot import utils, source
import pandas as pd
import numpy as np
import datetime
import logging


logger = logging.getLogger()


class Builder:
    """Class that constructs prediction datasets for hitters and pitchers.

    The datasets it generates are fully populated with projected stats.  The
    projection stats are scraped from fangraphs.com.

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param cfg: config details
    :type cfg: ConfigParser
    :param csv_details: Details about projections, stored in csv format
    :type csv_details: dict
    :param ts: Scraper to use to pull team data from baseball_reference.com
    :type ts: baseball_reference.TeamScraper
    :param es: Scraper to use to pull probable starters from espn
    :type es: espn.ProbableStartersScraper
    :param tss: Scraper to use to pull team list data from baseball_reference
    :type tss: baseball_reference.TeamSummaryScraper
    """
    def __init__(self, lg, cfg, csv_details, ts, es, tss):
        hitters = source.read_csv(csv_details['hitters'])
        pitchers = source.read_csv(csv_details['pitchers'])
        self.ppool = pd.concat([hitters, pitchers], sort=True)
        self.id_lookup = Lookup
        self.use_weekly_schedule = \
            cfg['Scorer'].getboolean('useWeeklySchedule')
        self.source = cfg['Prediction']['source']
        self.ts = ts
        self.es = es
        self.tss = tss
        if lg.settings()['weekly_deadline'] != '1':
            raise RuntimeError("This bot only supports weekly lineups.")
        # In the preseason the edit date will be the next day.  Only once the
        # season starts does the edit date advance to the start of the next
        # week.
        if lg.current_week() == 1:
            self.wk_start_date, self.wk_end_date = lg.week_date_range(1)
        else:
            self.wk_start_date = lg.edit_date()
            assert(self.wk_start_date.weekday() == 0)
            self.wk_end_date = self.wk_start_date + datetime.timedelta(days=6)
        self.season_end_date = datetime.date(self.wk_end_date.year, 12, 31)

    def __getstate__(self):
        return (self.ppool, self.ts, self.es, self.tss, self.wk_start_date,
                self.wk_end_date, self.season_end_date,
                self.use_weekly_schedule, self.source)

    def __setstate__(self, state):
        self.id_lookup = Lookup
        (self.ppool, self.ts, self.es, self.tss, self.wk_start_date,
         self.wk_end_date, self.season_end_date, self.use_weekly_schedule,
         self.source) = state

    def set_id_lookup(self, lk):
        self.id_lookup = lk

    def select_players(self, plyrs):
        """Return players from the player pool that match the given Yahoo! IDs

        :param plyrs: List of dicts that contain the player name and their
            Yahoo! ID.  These are all of the players we will return.
        :return: List of players from the player pool
        """
        if self.source.startswith("yahoo"):
            yahoo_ids = [e['player_id'] for e in plyrs]
            return self.ppool[self.ppool['player_id'].isin(yahoo_ids)]
        else:
            assert(self.source == 'csv')
            # Convert all of the player IDs to fan graph IDs
            fg_ids = []
            for plyr in plyrs:
                lk = self._lookup_plyr(plyr, True)
                fg_ids.append(lk['fg_id'])
            return self.ppool[self.ppool['playerid'].isin(fg_ids)]

    def predict(self, roster_cont, fail_on_missing=True,
                lk_id_system='yahoo_id',
                scrape_id_system='playerid', team_has='abbrev'):
        """Build a dataset of hitting and pitching predictions for the week

        The roster is inputed into this function.  It will scrape the
        predictions from fangraphs returning a DataFrame.

        The returning DataFrame is the prediction of each stat.

        :param roster_cont: Roster of players to generate predictions for
        :type roster_cont: roster.Container object
        :param fail_on_missing: True we are to fail if any player in
            roster_cont can't be found in the prediction data set.  Set this to
            false to simply filter those out.
        :param lk_id_system: Name of the ID column in the baseball_id Lookup
        :type lk_id_system: str
        :param scrape_id_system: Name of the ID column in the scraped data that
            has the ID to match with Lookup
        :type scrape_id_system: str
        :param team_has: Indicate the Team field in the scraped data frame.
            Does it have 'just_name' (e.g. Blue Jays, Reds, etc.) or 'abbrev'
            (e.g.  NYY, SEA, etc.)
        :type team_has: str
        :type fail_on_missing: bool
        :return: Dataset of predictions
        :rtype: DataFrame
        """
        res = pd.DataFrame()
        for roster_type in ['B', 'P']:
            lk = self._find_roster(roster_type, roster_cont.get_roster(),
                                   fail_on_missing)
            if lk is None:
                continue

            # Merge lk with the player pool.  We do an inner join to find the
            # intersection between the player pool and the players from the
            # roster.
            if self.source.startswith("yahoo"):
                df = pd.merge(lk, self.ppool, how='inner',
                              left_on=['yahoo_id'],
                              right_on=[scrape_id_system])
            else:
                assert(self.source == 'csv')
                df = pd.merge(lk, self.ppool, how='inner', left_on=['fg_id'],
                              right_on=[scrape_id_system])

            espn_ids = df.espn_id.to_list()
            num_GS = self._num_gs(espn_ids)
            df = df.assign(WK_GS=pd.Series(num_GS, index=df.index))
            team_abbrevs = self._lookup_teams(df.mlb_team.to_list(), team_has)
            df = df.assign(team=pd.Series(team_abbrevs, index=df.index))
            if self.use_weekly_schedule:
                wk_g = self._num_games_for_teams(team_abbrevs, True)
                df = df.assign(WK_G=pd.Series(wk_g, index=df.index))
                sea_g = self._num_games_for_teams(team_abbrevs, False)
                df = df.assign(SEASON_G=pd.Series(sea_g, index=df.index))
            roster_type = [roster_type] * len(df.index)
            df = df.assign(roster_type=pd.Series(roster_type, index=df.index))

            # Filter out some of the batting categories from pitchers
            if roster_type == 'P':
                for hit_stat in ['HR', 'RBI', 'AVG', 'OBP', 'R', 'SB']:
                    df[hit_stat] = np.nan

            res = res.append(df, sort=False)

        # Add a column that will track the selected position of each player.
        # It is currently set to NaN since other modules fill that in.
        res = res.assign(selected_position=np.nan)

        return res

    def _lookup_teams(self, teams, team_has):
        if team_has == 'just_name':
            return self._lookup_teams_by_name(teams)
        else:
            return self._lookup_teams_by_abbrev(teams)

    def _lookup_teams_by_name(self, teams):
        a = []
        tl_df = self.tss.scrape(self.wk_start_date.year)
        for team in teams:
            # In case we are given a team list with NaN (i.e. player isn't on
            # any team)
            if type(team) is str:
                a.append(tl_df[tl_df.Franchise.str.endswith(team)].
                         abbrev.iloc(0)[0])
            else:
                assert(np.isnan(team))
                a.append(None)
        return a

    def _lookup_teams_by_abbrev(self, teams):
        a = []
        abbrev_remap = {"WAS": "WSN"}
        for team in teams:
            if type(team) is str and team != 'FAA':
                if team in abbrev_remap:
                    team = abbrev_remap[team]
                a.append(team)
            else:
                a.append(None)
        return a

    def _lookup_plyr(self, plyr, fail_on_missing):
        one_lk = self.id_lookup.from_yahoo_ids([plyr['player_id']])
        # Do a lookup of names if the ID lookup didn't work.  We do two of
        # them.  The first one is to filter on any name that has a missing
        # yahoo_id.  This is better then just a plain name lookup because
        # it has a better chance of being unique.  A missing ID typically
        # happens for rookies.
        if len(one_lk.index) == 0:
            one_lk = self.id_lookup.from_names(
                [plyr['name']], filter_missing='yahoo_id')
            # Failback to a pure-name lookup.  There have been instances
            # with hitter/pitchers where they have two IDs: one for
            # pitchers and one for hitters.  The id_lookup only keeps
            # track of one of those IDs.  We will strip off the '(Batter)'
            # from their name.
            if len(one_lk.index) == 0:
                paren = plyr['name'].find('(')
                if paren > 0:
                    name = plyr['name'][0:paren-1].strip()
                else:
                    name = plyr['name']
                    # Get rid of any accents
                    name = utils.normalized(name)
                    one_lk = self.id_lookup.from_names([name])

            if len(one_lk.index) != 1:
                if fail_on_missing:
                    raise ValueError("Was not able to lookup player: {}".
                                     format(plyr))
        return one_lk

    def _find_roster(self, position_type, roster, fail_on_missing=True):
        lk = None
        for plyr in roster:
            if plyr['position_type'] != position_type or \
                    ('selected_position' in plyr and
                     plyr['selected_position'] in ['BN', 'DL']):
                continue

            one_lk = self._lookup_plyr(plyr, fail_on_missing)
            if len(one_lk.index) != 1:
                continue

            ep_series = pd.Series([plyr["eligible_positions"]], dtype="object",
                                  index=one_lk.index)
            one_lk = one_lk.assign(eligible_positions=ep_series)
            yahoo_series = pd.Series([plyr['player_id']], index=one_lk.index)
            one_lk = one_lk.assign(player_id=yahoo_series)
            status_series = pd.Series([plyr['status']], index=one_lk.index)
            one_lk = one_lk.assign(status=status_series)
            name_series = pd.Series([plyr['name']], index=one_lk.index)
            one_lk = one_lk.assign(name=name_series)
            if 'percent_owned' in plyr:
                pct_series = pd.Series([plyr['percent_owned']],
                                       index=one_lk.index)
                one_lk = one_lk.assign(percent_owned=pct_series)

            if lk is None:
                lk = one_lk
            else:
                lk = lk.append(one_lk)
        return lk

    def _num_games_for_team(self, abrev, week):
        if abrev is None:
            return 0
        if week:
            self.ts.set_date_range(self.wk_start_date, self.wk_end_date)
        else:
            self.ts.set_date_range(self.wk_start_date, self.season_end_date)
        df = self.ts.scrape(abrev)
        return len(df.index)

    def _num_games_for_teams(self, abrevs, week):
        games = []
        for abrev in abrevs:
            games.append(self._num_games_for_team(abrev, week))
        return games

    def _num_gs(self, espn_ids):
        df = self.es.scrape()
        num_GS = []
        for espn_id in espn_ids:
            if len(df.index) > 0:
                gs = len(df[df.espn_id == espn_id].index)
            else:
                gs = 0
            num_GS.append(gs)
        return num_GS


def init_prediction_builder(lg, cfg):
    # Build for week one if we are still in the preseason
    dates_for_next_week = True
    if lg.current_week() == 1:
        (start_date, end_date) = lg.week_date_range(1)
        if lg.edit_date() <= start_date:
            dates_for_next_week = False
    if dates_for_next_week:
        (start_date, end_date) = lg.week_date_range(lg.current_week() + 1)
    es = espn.ProbableStartersScraper(start_date, end_date)

    if 'source' not in cfg['Prediction']:
        raise RuntimeError(
            "Missing 'source' config attribute in 'Prediction' section")
    elif cfg['Prediction']['source'].startswith('yahoo'):
        cv = source.Yahoo(lg, cfg)
    elif cfg['Prediction']['source'] == 'csv':
        cv = source.CSV(lg, cfg)
    else:
        raise RuntimeError(
            "Unknown prediction source: {}".format(
                cfg['Prediction']['source']))

    ts = baseball_reference.TeamScraper()
    tss = baseball_reference.TeamSummaryScraper()
    return Builder(lg, cfg, cv.fetch_csv_details(), ts, es, tss)


class GenericCsvScraper:
    def __init__(self, batter_proj_file, pitcher_proj_file):
        self.batter_cache = pd.read_csv(batter_proj_file,
                                        encoding='iso-8859-1',
                                        header=1,
                                        skipfooter=1,
                                        engine='python')
        self.pitcher_cache = pd.read_csv(pitcher_proj_file,
                                         encoding='iso-8859-1',
                                         header=1,
                                         skipfooter=1,
                                         engine='python')

    def scrape(self, mlb_ids, scrape_as):
        """Scrape the csv file and return those match mlb_ids"""
        cache = self._get_cache(scrape_as)
        df = cache[cache['MLBAM ID'].isin(mlb_ids)]
        df['Name'] = df['Firstname'] + " " + df['Lastname']
        df = df.rename(columns={"Tm": "Team"})
        if scrape_as == fangraphs.ScrapeType.PITCHER:
            df = df.rename(columns={"Sv": "SV", "Hld": "HLD", "K": "SO"})
        return df

    def _get_cache(self, scrape_as):
        if scrape_as == fangraphs.ScrapeType.HITTER:
            return self.batter_cache
        else:
            return self.pitcher_cache


class Categories:
    def __init__(self, cfg):
        stats = cfg['League']['predictedStatCategories'].split(',')
        self.int_hit_cats = self._get_intermediate_hit_cats(stats)
        self.hit_count_cats = self._get_counting_hit_cats(stats)
        self.hit_ratio_cats = self._get_ratio_hit_cats(stats)
        self.all_hit_cats = self.hit_count_cats + self.hit_ratio_cats
        self.int_pit_cats = self._get_intermediate_pit_cats(stats)
        self.pit_count_cats = self._get_counting_pit_cats(stats)
        self.pit_ratio_cats = self._get_ratio_pit_cats(stats)
        self.all_pit_cats = self.pit_count_cats + self.pit_ratio_cats
        self.all_cats = self.hit_count_cats + self.hit_ratio_cats + \
            self.pit_count_cats + self.pit_ratio_cats
        if len(self.all_cats) != len(stats):
            raise RuntimeError("Did not use all stat categories: " +
                               str(self.all_cats) + " " + str(stats))

    def _get_intermediate_hit_cats(self, stats):
        ratio_cats = {'AVG': ['AB', 'H'],
                      'OBP': ['AB', 'H', 'BB']}
        cats = []
        for ratio_cat, int_cats in ratio_cats.items():
            if ratio_cat in stats:
                cats += int_cats
        return list(set(cats))   # Convert to a set to remove dups

    def _get_counting_hit_cats(self, stats):
        counting_hit_cats = ['H', 'R', 'RBI', 'SB', 'HR']
        cats = []
        for stat in stats:
            if stat in counting_hit_cats:
                cats.append(stat)
        return(cats)

    def _get_ratio_hit_cats(self, stats):
        ratio_cats = ['AVG', 'OBP']
        cats = []
        for stat in stats:
            if stat in ratio_cats:
                cats.append(stat)
        return(cats)

    def _get_intermediate_pit_cats(self, stats):
        ratio_cats = {'WHIP': ['IP', 'H', 'BB'],
                      'ERA': ['IP', 'ER']}
        cats = []
        for ratio_cat, int_cats in ratio_cats.items():
            if ratio_cat in stats:
                cats += int_cats
        return list(set(cats))  # Convert to a set to remove dups

    def _get_counting_pit_cats(self, stats):
        counting_pit_stats = ['SV', 'NSV', 'HLD', 'K', 'W', 'SO']
        cats = []
        for stat in stats:
            if stat in counting_pit_stats:
                cats.append(stat)
        return(cats)

    def _get_ratio_pit_cats(self, stats):
        ratio_cats = ['WHIP', 'ERA']
        cats = []
        for stat in stats:
            if stat in ratio_cats:
                cats.append(stat)
        return(cats)


class PlayerPrinter(Categories):
    def __init__(self, cfg):
        super().__init__(cfg)

    def printRosterHitHeader(self):
        print("{:4}: {:20}   ".format('B', '') +
              "/".join(["{}" for _ in self.all_hit_cats]).format(
                  *self.all_hit_cats))

    def printRosterPitcherHeader(self):
        print("")
        print("{:4}: {:20}   ".format('P', '') +
              "/".join(["{}" for _ in self.all_pit_cats]).format(
                  *self.all_pit_cats))

    def printRoster(self, lineup, bench, injury_reserve):
        """Print out the roster to standard out

        :param cfg: Instance of the config
        :type cfg: configparser
        :param lineup: Roster to print out
        :type lineup: List
        :param bench: Players on the bench
        :type bench: List
        :param injury_reserve: Players on the injury reserve
        :type injury_reserve: List
        """
        hit_header_printed = False
        pit_header_printed = False
        for pos in ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'Util',
                    'SP', 'RP']:
            for plyr in lineup:
                if plyr['selected_position'] == pos:
                    if pos in ["SP", "RP"]:
                        if not pit_header_printed:
                            self.printRosterPitcherHeader()
                            pit_header_printed = True

                        s = "{:4}: {:20}   ".format(plyr['selected_position'],
                                                    plyr['name'])
                        if len(self.pit_count_cats) > 0:
                            s += "/".join(["{:.1f}" for _ in
                                           self.pit_count_cats]). \
                                format(*[plyr[t] for t in self.pit_count_cats])
                        s += " "
                        if len(self.pit_ratio_cats) > 0:
                            s += "/".join(["{:.3f}" for _ in
                                           self.pit_ratio_cats]). \
                                format(*[plyr[t] for t in
                                         self.pit_ratio_cats])
                        print(s)
                    else:
                        if not hit_header_printed:
                            self.printRosterHitHeader()
                            hit_header_printed = True

                        s = "{:4}: {:20}   ".format(plyr['selected_position'],
                                                    plyr['name'])
                        if len(self.hit_count_cats) > 0:
                            s += "/".join(["{:.1f}" for _ in
                                           self.hit_count_cats]). \
                                format(*[plyr[t] for t in
                                         self.hit_count_cats])
                        s += " "
                        if len(self.hit_ratio_cats) > 0:
                            s += "/".join(["{:.3f}" for _ in
                                           self.hit_ratio_cats]). \
                                format(*[plyr[t] for t in
                                         self.hit_ratio_cats])
                        print(s)
        print("")
        print("Bench")
        for plyr in bench:
            print(plyr['name'])
        print("")
        print("Injury Reserve")
        for plyr in injury_reserve:
            print(plyr['name'])
        print("")

    def printListPlayerHeading(self, pos):
        s = "{:20}   ".format('name')
        if pos in ['C', '1B', '2B', 'SS', '3B', 'LF', 'CF', 'RF', 'Util']:
            if len(self.hit_count_cats) > 0:
                s += "/".join(["{}" for _ in self.hit_count_cats]).format(
                    *self.hit_count_cats)
            s += " "
            if len(self.hit_ratio_cats) > 0:
                s += "/".join(["{}" for _ in self.hit_ratio_cats]).format(
                    *self.hit_ratio_cats)
        else:
            if len(self.hit_count_cats) > 0:
                s += "/".join(["{}" for _ in self.pit_count_cats]).format(
                    *self.pit_count_cats)
            s += " "
            if len(self.pit_ratio_cats) > 0:
                s += "/".join(["{}" for _ in self.pit_ratio_cats]).format(
                    *self.pit_ratio_cats)
        print(s)

    def printPlayer(self, pos, plyr):
        s = "{:20}   ".format(plyr[1]['name'])
        if pos in ['C', '1B', '2B', 'SS', '3B', 'LF', 'CF', 'RF', 'Util']:
            if len(self.hit_count_cats) > 0:
                s += "/".join(["{:.1f}" for _ in self.hit_count_cats]).format(
                    *[plyr[1][t] for t in self.hit_count_cats])
            s += " "
            if len(self.hit_ratio_cats) > 0:
                s += "/".join(["{:.3f}" for _ in self.hit_ratio_cats]).format(
                    *[plyr[1][t] for t in self.hit_ratio_cats])
        else:
            if len(self.pit_count_cats) > 0:
                s += "/".join(["{:.1f}" for _ in self.pit_count_cats]).format(
                    *[plyr[1][t] for t in self.pit_count_cats])
            s += " "
            if len(self.hit_ratio_cats) > 0:
                s += "/".join(["{:.3f}" for _ in self.pit_ratio_cats]).format(
                    *[plyr[1][t] for t in self.pit_ratio_cats])
        print(s)


class Scorer(Categories):
    """Class that scores rosters that it is given"""
    def __init__(self, cfg):
        super().__init__(cfg)
        self.use_weekly_schedule = \
            cfg['Scorer'].getboolean('useWeeklySchedule')

    def summarize(self, df):
        """Summarize the dataframe into individual stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        res = self._sum_hit_prediction(df)
        res = res.append(self._sum_pit_prediction(df))
        return res

    def _sum_hit_prediction(self, df):
        res = pd.Series()
        for stat in self.hit_count_cats + self.int_hit_cats:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'B':
                    continue
                if self.use_weekly_schedule:
                    if plyr[1]['SEASON_G'] > 0:
                        val += plyr[1][stat] / plyr[1]['SEASON_G'] * \
                            plyr[1]['WK_G']
                else:
                    val += plyr[1][stat]
            res[stat] = val

        # Handle ratio stats
        if 'AVG' in self.hit_ratio_cats:
            res['AVG'] = res['H'] / res['AB'] if res['AB'] > 0 else 0
        if 'OBP' in self.hit_ratio_cats:
            res['OBP'] = (res['H'] + res['BB']) / (res['AB'] + res['BB']) \
                if res['AB'] + res['BB'] > 0 else 0

        # Drop the temporary values used to calculate the ratio stats
        if len(self.int_hit_cats) > 0:
            res = res.drop(index=self.int_hit_cats)

        return res

    def _sum_pit_prediction(self, df):
        res = pd.Series()
        for stat in self.pit_count_cats + self.int_pit_cats:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'P':
                    continue
                # Account for number of known starts (if applicable).
                # Otherwise, just revert to an average over the remaining games
                # on the team's schedule.
                if self.use_weekly_schedule:
                    if plyr[1]['WK_GS'] > 0:
                        val += plyr[1][stat] / plyr[1]['G'] \
                            * plyr[1]['WK_GS']
                    elif plyr[1]['WK_G'] > 0:
                        val += plyr[1][stat] / plyr[1]['SEASON_G'] \
                            * plyr[1]['WK_G']
                else:
                    val += plyr[1][stat]
            res[stat] = val

        # Handle ratio stats
        if 'WHIP' in self.pit_ratio_cats:
            res['WHIP'] = (res['BB'] + res['H']) / res['IP'] \
                if res['IP'] > 0 else 0
        if 'ERA' in self.pit_ratio_cats:
            res['ERA'] = res['ER'] * 9 / res['IP'] if res['IP'] > 0 else 0

        # Delete the temporary values used to calculate the ratio stats
        if len(self.int_pit_cats) > 0:
            res = res.drop(index=self.int_pit_cats)

        return res

    def is_counting_stat(self, stat):
        return stat in ['R', 'HR', 'RBI', 'SB', 'W', 'SO', 'SV', 'HLD', 'K']

    def is_highest_better(self, stat):
        return stat not in ['ERA', 'WHIP']
