#!/usr/bin/python

import logging



logger = logging.getLogger()


class Builder:
    """Class that constructs prediction datasets for hockey players.

    The datasets it generates are fully populated with projected stats taken
    from csv files.

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param cfg: config details
    :type cfg: ConfigParser
    :param csv_details: A map of details about the csv that contains the
        predicted stats
    """
    def __init__(self, lg, cfg, csv_details):
        pass

    def select_players(self, plyrs):
        """Return players from the player pool that match the given Yahoo! IDs

        :param plyrs: List of dicts that contain the player name and their
            Yahoo! ID.  These are all of the players we will return.
        :return: List of players from the player pool
        """
        yahoo_ids = [e['player_id'] for e in plyrs]
        return self.ppool[self.ppool['player_id'].isin(yahoo_ids)]

    def predict(self, plyrs, fail_on_missing=True, **kwargs):
        """Build a dataset of hockey predictions for the week

        The pool of players is passed into this function through roster_const.
        It will generate a DataFrame for these players with their predictions.

        The returning DataFrame has rows for each player, and columns for each
        prediction stat.

        :param plyrs: Roster of players to generate predictions for
        :type plyrs: list
        :param fail_on_missing: True we are to fail if any player in
            roster_cont can't be found in the prediction data set.  Set this to
            false to simply filter those out.
        :type roster_cont: roster.Container object
        :return: Dataset of predictions
        :rtype: DataFrame
        """
        pass

    def _find_players_schedule(self, plyr_name):
        """Find a players schedule for the upcoming week

        :param plyr_name: Name of the player
        :type plyr_name: str
        :return: Pair of team_id (from NHL) and the number of games
        :rtype: (int, int)
        """
        pass


def init_prediction_builder(lg, cfg):
    pass


class PlayerPrinter:
    def __init__(self, cfg):
        pass

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
        pass

    @staticmethod
    def _get_stat_category(stat):
        '''Helper to determine if a given stat is for a skater or goalie

        :param stat: Stat to check
        :return: 'G' for a goalie stat or 'S' for skater stat
        '''
        pass


class Scorer:
    """Class that scores rosters that it is given"""
    def __init__(self, cfg):
        pass

    def summarize(self, df):
        """Summarize the dataframe into individual stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        pass

    def is_numeric(self, v):
        '''Helper to check if v is a numeric type we can use in math'''
        pass

    def is_counting_stat(self, stat):
        pass

    def is_highest_better(self, stat):
        pass


class StatAccumulator:
    """Class that aggregates stats for a bunch of players"""
    def __init__(self, cfg):
        self.scorer = Scorer(cfg)

    def add_player(self, plyr):
        pass

    def remove_player(self, plyr):
        pass

    def get_summary(self, roster):
        """Return a summary of the stats for players in the roster

        :param roster: List of players we want go get stats for
        :type roster: list
        :return: Summary of key stats for the players
        :rtype: pandas.Series
        """
        pass
