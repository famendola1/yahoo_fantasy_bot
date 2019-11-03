#!/bin/python

import copy
import logging
import numpy as np
import pandas as pd
from progressbar import ProgressBar, Percentage, Bar
import math
import random
from yahoo_fantasy_bot import roster


def optimize_single_player_at_a_time(cfg, score_comparer, roster_bldr,
                                     avail_plyrs, lineup):
    """
    Optimize by swapping in a single player to a constructed lineup

    :param cfg: Loaded config object
    :type cfg: configparser.ConfigParser
    :param score_comparer: Object that is used to compare two lineups to
    determine the better one
    :type score_comparer: bot.ScoreComparer
    :param roster_bldr: Object that is used to construct a roster given the
    constraints of the league
    :type roster_bldr: roster.Builder
    :param avail_plyrs: Pool of available players that can be included in
    a lineup
    :type avail_plyrs: DataFrame
    :param lineup: The currently constructed lineup
    :type lineup: list
    :return: If a better lineup was found, this will return it.  If no better
    lineup was found this returns None
    :rtype: list or None
    """
    selector = roster.PlayerSelector(avail_plyrs)
    categories = cfg['LineupOptimizer']['categories'].split(",")
    try:
        selector.rank(categories)
    except KeyError:
        raise KeyError("Categories are not valid: {}".format(categories))

    found_better = False
    score_comparer.update_score(lineup)
    for i, plyr in enumerate(selector.select()):
        if i+1 > int(cfg['LineupOptimizer']['iterations']):
            break

        print("Player: {} Positions: {}".
              format(plyr['name'], plyr['eligible_positions']))

        plyr['selected_position'] = np.nan
        best_lineup = copy.deepcopy(lineup)
        for potential_lineup in roster_bldr.enumerate_fit(best_lineup, plyr):
            if score_comparer.compare_lineup(potential_lineup):
                print("  *** Found better lineup when including {}"
                      .format(plyr['name']))
                lineup = copy.deepcopy(potential_lineup)
                score_comparer.update_score(lineup)
                found_better = True
    return lineup if found_better else None


def optimize_with_genetic_algorithm(cfg, score_comparer, roster_bldr,
                                    avail_plyrs, lineup):
    """
    Loader for the GeneticAlgorithm class

    See GeneticAlgorithm.__init__ for parameter type descriptions.
    """
    for plyr in lineup:
        if plyr['status'] != '':
            continue
        avail_plyrs = avail_plyrs.append(plyr, ignore_index=True)
    algo = GeneticAlgorithm(cfg, score_comparer, roster_bldr, avail_plyrs,
                            lineup)
    generations = int(cfg['LineupOptimizer']['generations']) \
        if 'generations' in cfg['LineupOptimizer'] else 100
    return algo.run(generations)


class GeneticAlgorithm:
    """
    Optimize the lineup using a genetic algorithm

    The traits of the algorithm and how it relates to lineup building is
    as follows:
    - chromosomes: lineups
    - genes: players in the lineup
    - population (group): random set of lineups that use all available players
    - fitness function: evaluation a lineup against the base line with the
    score_comparer

    When apply generations to the chromosomes, the following applies:
    - selection: Lineups that have the best score are more likely to be
    selected.
    - crossover: Involves merging of two lineups.
    - mutate: Randomly swapping out a player with someone else

    :param cfg: Loaded config object
    :type cfg: configparser.ConfigParser
    :param score_comparer: Object that is used to compare two lineups to
    determine the better one
    :type score_comparer: bot.ScoreComparer
    :param roster_bldr: Object that is used to construct a roster given the
    constraints of the league
    :type roster_bldr: roster.Builder
    :param avail_plyrs: Pool of available players that can be included in
    a lineup
    :type avail_plyrs: DataFrame
    :param lineup: The currently constructed lineup
    :type lineup: list
    :return: If a better lineup was found, this will return it.  If no better
    lineup was found this returns None
    :rtype: list or None
    """
    def __init__(self, cfg, score_comparer, roster_bldr, avail_plyrs, lineup):
        self.cfg = cfg
        self.score_comparer = score_comparer
        self.roster_bldr = roster_bldr
        self.ppool = avail_plyrs
        self.population = []
        self.logger = logging.getLogger()
        self.last_lineup_id = 0
        self.pbar = None

    def run(self, generations):
        """
        Optimize a lineup by running the genetic algorithm

        :param generations: The number of generations to run the algorithm for
        :type generations: int
        :return: The best lineup we generated.  Or None if no lineup was
        generated
        :rtype: list or None
        """
        self._init_progress_bar(generations)
        self._init_population()
        for generation in range(generations):
            self._update_progress(generation)
            self._mate()
            self._mutate()
        self.logger.info(
            "Ended with population size of {}".format(len(self.population)))
        return self._compute_best_lineup()

    def _gen_lineup_id(self):
        self.last_lineup_id += 1
        return self.last_lineup_id

    def _to_sids(self, lineup):
        """Return a sorted list of player IDs"""
        return sorted([e["player_id"] for e in lineup])

    def _is_dup_sids(self, sids):
        """Check if any lineup in the population matches the given sids"""
        for l in self.population:
            if sids == l['sids']:
                return True
        return False

    def _log_lineup(self, descr, lineup):
        self.logger.info("Lineup: ID={}, Desc={}, Score={}".format(
            lineup['id'], descr, lineup['score']))
        for plyr in lineup['players']:
            self.logger.info(
                "{} - {} ({}%)".format(plyr['selected_position'],
                                       plyr['name'],
                                       plyr['percent_owned']))

    def _init_progress_bar(self, generations):
        """
        Initialize the progress bar

        :param generations: Number of generations we will do
        """
        self.pbar = ProgressBar(widgets=[Percentage(), Bar()],
                                maxval=generations)
        self.pbar.start()

    def _update_progress(self, generation):
        """
        Shows progress of the lineup selection

        :param generation: Current generation number
        :param generations: Max number of generations
        """
        self.pbar.update(generation + 1)

    def _log_population(self):
        for i, lineup in enumerate(self.population):
            self._log_lineup("Initial Population " + str(i), lineup)

    def _init_population(self):
        max_lineups = int(self.cfg['LineupOptimizer']['initialPopulationSize'])
        self.population = []
        self._generate_lineups(max_lineups, gen_type='pct_own')
        while len(self.population) < max_lineups:
            self._generate_lineups(max_lineups, gen_type='random')
        self.score_comparer.compute_stddevs(
            [e['players'] for e in self.population])
        self._score_population()
        self._log_population()

    def _generate_lineups(self, max_lineups, gen_type='pct_own'):
        """
        Create lineups for initial population

        New lineups will be added to self.population.

        :param gen_type: Specify how to generate the lineup.  Acceptable values
        are 'pct_own' and 'random'.  'pct_own' will pick lineups with
        preference to the players who have the highest percent owned.  'random'
        will generate totally random lineups.
        :param max_lineups: The maximum number of lineups to have in
        self.population
        """
        assert(len(self.population) < max_lineups)
        selector = roster.PlayerSelector(self.ppool)
        if gen_type == 'pct_own':
            selector.set_descending_categories([])
            selector.rank(['percent_owned'])
        else:
            assert(gen_type == 'random')
            selector.shuffle()
        lineups = []
        lineups.append([])
        for plyr in selector.select():
            fit = False
            for lineup in lineups:
                if len(lineup) == self.roster_bldr.max_players():
                    continue
                try:
                    assert(plyr['status'] == '')
                    plyr['selected_position'] = np.nan
                    lineup = self.roster_bldr.fit_if_space(lineup, plyr)
                    fit = True

                    # If lineup is no complete add it to the population
                    if len(lineup) == self.roster_bldr.max_players():
                        sids = self._to_sids(lineup)
                        if self._is_dup_sids(sids):
                            continue
                        self.population.append({'players': lineup,
                                                'score': None,
                                                'id': self._gen_lineup_id(),
                                                'sids': sids})
                        if len(self.population) == max_lineups:
                            return

                    break   # Stop trying to find a lineup for plyr
                except LookupError:
                    pass   # Try fitting in the next lineup

            if not fit:
                lineup = self.roster_bldr.fit_if_space([], plyr)
                lineups.append(lineup)

    def _score_population(self):
        """
        Compute a score for each lineup in the population that
        """
        for l in self.population:
            if l['score'] is None:
                l['score'] = \
                    self.score_comparer.compute_score_as_stdev(l['players'])

    def _remove_from_pop(self, lineup):
        for i, p in enumerate(self.population):
            if lineup['id'] == p['id']:
                del(self.population[i])
                return
        raise RuntimeError(
            "Could not find lineup in population " + str(lineup['id']))

    def _compute_best_lineup(self):
        """
        Goes through all of the possible lineups and figures out the best

        :return: The best lineup
        """
        best_lineup = self.population[0]
        for lineup in self.population[1:]:
            assert(lineup['score'] is not None)
            if lineup['score'] > best_lineup['score']:
                best_lineup = lineup
        self._log_lineup("Best", best_lineup)
        return best_lineup['players']

    def _mate(self):
        """
        Merge two lineups to produce children that character genes from both

        The selection process regarding who to mate is determined using the
        selectionStyle config parameter.
        """
        mates = self._pick_lineups()
        self._remove_from_pop(mates[0])
        self._remove_from_pop(mates[1])
        offspring = self._produce_offspring(mates)
        for i, lineup in enumerate(offspring):
            self._log_lineup("Offspring " + str(i), lineup)
        self.population = self.population + offspring

    def _pick_lineups(self):
        """
        Pick two lineups at random

        This uses the tournament selection process where random set of lineups
        are selected, then go through a tournament to pick the top number.

        :return: List of lineups
        """
        k = int(self.cfg['LineupOptimizer']['tournamentParticipants'])
        if k > len(self.population):
            pw = math.floor(math.log(len(self.population), 2))
            k = 2**pw
        assert(math.log(k, 2).is_integer()), "Must be a power of 2"
        participants = random.sample(self.population, k=k)
        rounds = math.log(k, 2) - 1
        for _ in range(int(rounds)):
            next_participants = []
            for opp_1, opp_2 in zip(participants[0::2], participants[1::2]):
                assert(opp_1['score'] is not None)
                assert(opp_2['score'] is not None)
                if opp_1['score'] > opp_2['score']:
                    next_participants.append(opp_1)
                else:
                    next_participants.append(opp_2)
            participants = next_participants
        assert(len(participants) == 2)
        assert(participants[0]['id'] != participants[1]['id'])
        return participants

    def _produce_offspring(self, mates):
        """
        Merge two lineups together to produce a set of children.

        :param mates: Two parent lineups that we use to produce offspring
        :return: List of lineups
        """
        assert(len(mates) == 2)
        assert(mates[0]['sids'] != mates[1]['sids'])
        ppool = self._create_player_pool(mates)
        offspring = [mates[0], mates[1]]
        for _ in range(int(self.cfg['LineupOptimizer']['numOffspring'])):
            plyrs = self._complete_lineup(ppool, [])
            score = self.score_comparer.compute_score_as_stdev(plyrs)
            offspring.append({'players': plyrs, 'score': score,
                              'id': self._gen_lineup_id(),
                              'sids': self._to_sids(plyrs)})
        offspring = sorted(offspring, key=lambda e: e['score'], reverse=True)
        # Remove any identical offspring.  If two offspring are identical they
        # will be adjacent to each other because they have the same score.
        for i in range(len(offspring)-1, 0, -1):
            if offspring[i]['sids'] == offspring[i-1]['sids']:
                del(offspring[i])
        # Check for duplicate lineups in the general population
        while self._is_dup_sids(offspring[0]['sids']):
            del(offspring[0])
        while self._is_dup_sids(offspring[1]['sids']):
            del(offspring[1])
        return offspring[0:2]

    def _create_player_pool(self, lineups):
        """
        Produces a player pool from a set of lineups

        The player pool is suitable for use with the PlayerSelector

        :param lineups: Set of lineups to create a pool out of
        :return: DataFrame of all of the unique players in the lineups
        """
        df = pd.DataFrame()
        player_ids = []
        for lineup in lineups:
            for i, plyr in enumerate(lineup['players']):
                # Avoid adding duplicate players to the pool
                if plyr['player_id'] not in player_ids:
                    df = df.append(plyr, ignore_index=True)
                    player_ids.append(plyr['player_id'])
        return df

    def _complete_lineup(self, ppool, lineup):
        """
        Complete a lineup so that it has the max number of players

        The players are selected at random.

        :param ppool: Player pool to pull from
        :param lineup: Lineup to fill.  Can be [].
        :return: List that contains the players in the lineup
        """
        ids = [e['player_id'] for e in lineup]
        selector = roster.PlayerSelector(ppool)
        selector.shuffle()
        for plyr in selector.select():
            # Do not add the player if it is already in the lineup
            if plyr['player_id'] in ids:
                continue
            try:
                plyr['selected_position'] = np.nan
                lineup = self.roster_bldr.fit_if_space(lineup, plyr)
            except LookupError:
                pass
            if len(lineup) == self.roster_bldr.max_players():
                return lineup
        raise RuntimeError(
            "Walked all of the players but couldn't create a lineup.  Have "
            "{} players".format(len(lineup)))

    def _mutate(self):
        """
        Go through all of the players and mutate a certain percent.

        Mutation simply means swapping out the player with a random player.
        """
        mutate_pct = int(self.cfg['LineupOptimizer']['mutationPct'])
        add_lineups = []
        rem_lineups = []
        for lineup in self.population:
            new_plyrs = self._remove_mutations(mutate_pct, lineup)
            if new_plyrs is None:
                continue

            self._log_lineup("(Pre) Mutated lineup", lineup)
            self._complete_lineup(self.ppool, new_plyrs)
            assert(len(new_plyrs) == self.roster_bldr.max_players())
            sids = self._to_sids(new_plyrs)
            if self._is_dup_sids(sids):
                continue
            score = self.score_comparer.compute_score_as_stdev(new_plyrs)
            if score <= lineup['score']:
                continue
            new_lineup = {"players": new_plyrs, "id": self._gen_lineup_id(),
                          "score": score, "sids": sids}
            self._log_lineup("(Post) Mutated lineup", new_lineup)
            add_lineups.append(new_lineup)
            rem_lineups.append(lineup)
        for l in rem_lineups:
            self._remove_from_pop(l)
        self.population = self.population + add_lineups

    def _remove_mutations(self, mutate_pct, lineup):
        """
        Copy and modify the list of players with mutated players removed

        This does a deep copy of the plyrs so that we retain the original
        lineup in case the mutation does not improve things.

        :param plyrs: List of players to consider for mutation
        :return: Players with mutated players removed.  Return None if no
        mutation occurred
        """
        mutates = []
        plyrs = lineup['players']
        for i, plyr in enumerate(plyrs):
            if random.randint(0, 100) <= mutate_pct:
                self.logger.info("Mutating player {} in lineup {}".
                                 format(plyr['name'], lineup['id']))
                mutates.append(i)
        if len(mutates) == 0:
            return None
        new_plyrs = copy.deepcopy(plyrs)
        mutates.reverse()   # Delete at the end of lineup first
        for i in mutates:
            del(new_plyrs[i])
        return new_plyrs