import unittest
from config import Config
from selector import SelectionFilter
from combinations import CombinationGenerator

FIXTURES = [
    dict(competition='EPL', date_time='20:00', home_team='Man City', away_team='Luton', home_odds=1.18, draw_odds=7.5, away_odds=15.0),
    dict(competition='EPL', date_time='20:00', home_team='Arsenal', away_team='Brighton', home_odds=1.50, draw_odds=4.2, away_odds=6.0),
    dict(competition='LL', date_time='21:00', home_team='Real Madrid', away_team='Getafe', home_odds=1.35, draw_odds=5.0, away_odds=9.0),
    dict(competition='SA', date_time='21:45', home_team='Empoli', away_team='Inter', home_odds=5.5, draw_odds=4.1, away_odds=1.55),
    dict(competition='BL', date_time='19:30', home_team='Dortmund', away_team='Mainz', home_odds=1.60, draw_odds=4.0, away_odds=5.2),
    dict(competition='X', date_time='18:00', home_team='Coin', away_team='Flip', home_odds=2.6, draw_odds=3.2, away_odds=2.7),  # toss-up
]


class SelectionTests(unittest.TestCase):
    def _run(self, min_prob=0.60, market=Config.MARKET_WIN):
        f = SelectionFilter(1.10, 3.00, 20000, 5000, market, True, min_prob)
        return f.filter_fixtures(FIXTURES)

    def test_probabilities_sum_to_one_and_margin_removed(self):
        p = SelectionFilter.implied_probabilities(FIXTURES[1])
        self.assertAlmostEqual(p['home'] + p['draw'] + p['away'], 1.0, places=6)
        self.assertGreater(p['margin'], 0)

    def test_underdogs_and_tossups_are_excluded(self):
        picks = {(s['home_team'], s['selection']) for s in self._run()}
        self.assertNotIn(('Coin', 'Home Win'), picks)      # ~36% -> out
        self.assertNotIn(('Empoli', 'Home Win'), picks)    # underdog
        self.assertIn(('Empoli', 'Away Win') if False else ('Empoli', 'Away Win'), picks)  # Inter favourite

    def test_all_selected_meet_probability_floor(self):
        for s in self._run(0.65):
            self.assertGreaterEqual(s['win_prob'], 0.65)

    def test_combos_reach_payout_and_rank_by_probability(self):
        sels = self._run()
        gen = CombinationGenerator(8, 5)
        combos = gen.generate_combinations(sels, 15000, 5000)   # needs combined odds >= 3.0
        self.assertTrue(gen.meets_payout)
        probs = [gen.combined_probability(c) for c in combos]
        self.assertEqual(probs, sorted(probs, reverse=True))
        for c in combos:
            self.assertGreaterEqual(gen.combined_odds(c) * 5000, 15000)
            teams = [(s['home_team'], s['away_team']) for s in c]
            self.assertEqual(len(teams), len(set(teams)))

    def test_unreachable_target_flags_best_effort(self):
        sels = self._run()
        gen = CombinationGenerator(3, 5)
        combos = gen.generate_combinations(sels, 5_000_000, 5000)
        self.assertFalse(gen.meets_payout)
        self.assertEqual(len(combos), 1)


if __name__ == '__main__':
    unittest.main()
