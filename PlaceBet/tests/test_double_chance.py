import unittest
from config import Config
from fixture_parser import parse_fixtures_from_text
from selector import SelectionFilter
from odds_provider import OddsProvider
from tests.test_live_build import LiveProvider, FakeWithGet


class DCProvider(LiveProvider):
    """Stubs the browser-only tab switching; flips the fake page to the DC market."""
    def __init__(self, driver, switch_ok=True):
        super().__init__(driver)
        self.switch_ok = switch_ok
    def _switch_to_double_chance(self, before):
        if self.switch_ok:
            self.fake.mode = 'DC'
        return self.switch_ok


class DoubleChanceTests(unittest.TestCase):
    def setUp(self):
        self.old = (Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS)
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = 3, 2

    def tearDown(self):
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = self.old

    def _sel(self, market, min_odds=1.05):
        return SelectionFilter(min_odds, 3.0, 6500, 5000, market, True, 0.60)

    def test_parser_reads_dc_columns_with_header_labels(self):
        text = "1X\nX2\n12\nToday 20:00\nArsenal\nBrighton\n+9\n1.08\n2.10\n1.20\n"
        f = parse_fixtures_from_text(text, 'DC')
        self.assertEqual((f[0]['dc_1x'], f[0]['dc_x2'], f[0]['dc_12']), (1.08, 2.10, 1.20))
        self.assertEqual((f[0]['home_team'], f[0]['away_team']), ('Arsenal', 'Brighton'))

    def test_dc_probabilities_are_normalised_and_12_never_chosen(self):
        fx = dict(competition='c', date_time='t', home_team='A', away_team='B',
                  dc_1x=1.10, dc_12=1.15, dc_x2=1.60)
        sel = self._sel(Config.MARKET_DOUBLE_CHANCE).best_dc_selection(fx)
        self.assertEqual(sel['selection'], '1X')
        self.assertFalse(sel['derived'])
        self.assertAlmostEqual(sel['win_prob'], 2 * (1 / 1.10) / (1/1.10 + 1/1.15 + 1/1.60), places=6)
        # X2 at 1.60 is 52% -> below the 60% floor, so 12 / X2 not picked
        fx2 = dict(fx, dc_1x=2.2, dc_12=1.10, dc_x2=1.9)
        self.assertIsNone(self._sel(Config.MARKET_DOUBLE_CHANCE).best_dc_selection(fx2))

    def test_double_chance_mode_adds_real_dc_picks_until_target(self):
        p = DCProvider(FakeWithGet(batches=6, per_batch=5, delay=0.5))
        r = p.build_betslip_live(self._sel(Config.MARKET_DOUBLE_CHANCE), 5000, 6500, 30)
        self.assertTrue(r['reached_target'])
        self.assertTrue(all(s['selection'] == '1X' for s in r['added']))
        self.assertEqual(len(r['added']), 3)          # 1.10^3 = 1.331 >= 1.30
        self.assertEqual(r['fixtures_checked'] <= 10, True)

    def test_mixed_mode_wins_first_then_dc_without_duplicate_matches(self):
        drv = FakeWithGet(batches=1, per_batch=2, delay=0.2)
        drv.dc_per_batch = 6
        p = DCProvider(drv)
        r = p.build_betslip_live(self._sel(Config.MARKET_MIXED), 5000, 15000, 30)   # target 3.0
        kinds = [s['selection'] for s in r['added']]
        self.assertEqual(kinds[:2], ['Home Win', 'Home Win'])
        self.assertIn('1X', kinds)
        self.assertTrue(r['reached_target'])
        teams = [s['home_team'] for s in r['added']]
        self.assertEqual(len(teams), len(set(teams)))  # one pick per match

    def test_switch_failure_is_reported_not_silent(self):
        p = DCProvider(FakeWithGet(batches=1, per_batch=2, delay=0.2), switch_ok=False)
        r = p.build_betslip_live(self._sel(Config.MARKET_DOUBLE_CHANCE), 5000, 6500, 30)
        self.assertEqual(r['added'], [])
        self.assertTrue(any('Double Chance' in n for n in r['notes']))

    def test_1x2_prices_are_rejected_as_double_chance(self):
        # Home 1.50 / Draw 4.00 / Away 6.00 sums to ~1.08 -> that is a 1X2 row, not Double Chance
        fx = dict(competition='c', date_time='t', home_team='A', away_team='B',
                  dc_1x=1.50, dc_12=4.00, dc_x2=6.00)
        sf = self._sel(Config.MARKET_DOUBLE_CHANCE)
        self.assertFalse(sf.dc_row_is_valid(fx))
        self.assertIsNone(sf.best_dc_selection(fx))

    def test_double_chance_mode_never_returns_a_win_pick(self):
        fx = dict(competition='c', date_time='t', home_team='A', away_team='B',
                  home_odds=1.30, draw_odds=5.0, away_odds=9.0)
        self.assertIsNone(self._sel(Config.MARKET_DOUBLE_CHANCE).best_selection(fx))

    def test_page_that_still_shows_1x2_adds_nothing(self):
        class StuckProvider(DCProvider):
            def _switch_to_double_chance(self, before):
                return True          # claims success, but the fake page stays in 1X2 mode
        p = StuckProvider(FakeWithGet(batches=3, per_batch=8, delay=0.2))
        r = p.build_betslip_live(self._sel(Config.MARKET_DOUBLE_CHANCE), 5000, 6500, 30)
        self.assertEqual(r['added'], [])
        self.assertEqual(p.clicked, [])
        self.assertTrue(any('real Double Chance prices' in n for n in r['notes']))


class FakeButton:
    def __init__(self, text, label=None):
        self.text, self.label = text, label


class ClickProvider(OddsProvider):
    """Exercises the real _click_visible_row with a fake page row of three price buttons."""
    def __init__(self, buttons):
        super().__init__()
        self.buttons, self.clicked = buttons, None
        self.driver = self
    def execute_script(self, js, *args):
        from odds_provider import FIND_ROW_ODDS_JS, BUTTON_LABEL_JS
        if js == FIND_ROW_ODDS_JS:
            return self.buttons
        if js == BUTTON_LABEL_JS:
            return args[0].label
        return ''
    def _body_text(self): return 'A\nB'
    def _safe_click(self, el):
        self.clicked = el
        return True


class ColumnOrderTests(unittest.TestCase):
    def _fx(self, text):
        return parse_fixtures_from_text(text, 'DC')[0]

    def test_default_order_is_1x_x2_12(self):
        # no header, no labels -> BetPawa's layout: 1X, X2, 12
        fx = self._fx("Today 20:00\nArsenal\nBrighton\n+9\n1.10\n1.60\n1.15\n")
        self.assertEqual((fx['dc_1x'], fx['dc_x2'], fx['dc_12']), (1.10, 1.60, 1.15))
        self.assertEqual(fx['dc_positions'], {'1x': 0, 'x2': 1, '12': 2})

    def test_header_order_overrides_default(self):
        fx = self._fx("1X\n12\nX2\nToday 20:00\nArsenal\nBrighton\n+9\n1.10\n1.15\n1.60\n")
        self.assertEqual((fx['dc_1x'], fx['dc_12'], fx['dc_x2']), (1.10, 1.15, 1.60))
        self.assertEqual(fx['dc_positions']['x2'], 2)

    def test_per_button_labels_override_everything(self):
        fx = self._fx("Today 20:00\nArsenal\nBrighton\n+9\n12\n1.15\n1X\n1.10\nX2\n1.60\n")
        self.assertEqual((fx['dc_1x'], fx['dc_x2'], fx['dc_12']), (1.10, 1.60, 1.15))

    def test_x2_pick_uses_second_column_not_12(self):
        fx = self._fx("1X\nX2\n12\nToday 20:00\nTeamA\nTeamB\n+9\n2.30\n1.12\n1.30\n")
        sel = SelectionFilter(1.05, 3.0, 1000, 1000, Config.MARKET_DOUBLE_CHANCE, True, 0.60).best_dc_selection(fx)
        self.assertEqual(sel['selection'], 'X2')
        self.assertEqual(sel['odds'], 1.12)
        self.assertEqual(sel['col_index'], 1)

    def test_click_hits_x2_button_and_never_the_12_button(self):
        btns = [FakeButton('2.30'), FakeButton('1.12'), FakeButton('1.30')]   # 1X, X2, 12
        p = ClickProvider(btns)
        ok = p._click_visible_row(dict(home_team='A', away_team='B', selection='X2', odds=1.12, col_index=1))
        self.assertTrue(ok)
        self.assertIs(p.clicked, btns[1])

    def test_dom_labels_beat_position(self):
        # page actually labels the buttons in a different order than we assumed
        btns = [FakeButton('2.30', '1x'), FakeButton('1.30', '12'), FakeButton('1.12', 'x2')]
        p = ClickProvider(btns)
        ok = p._click_visible_row(dict(home_team='A', away_team='B', selection='X2', odds=1.12, col_index=1))
        self.assertTrue(ok)
        self.assertIs(p.clicked, btns[2])

    def test_refuses_12_selection_and_12_labelled_button(self):
        p = ClickProvider([FakeButton('2.30'), FakeButton('1.12'), FakeButton('1.30')])
        self.assertFalse(p._click_visible_row(dict(home_team='A', away_team='B', selection='12', odds=1.30)))
        self.assertIsNone(p.clicked)
        p2 = ClickProvider([FakeButton('1.12', '12'), FakeButton('1.30', None), FakeButton('2.30', None)])
        self.assertFalse(p2._click_visible_row(dict(home_team='A', away_team='B', selection='X2', odds=1.12, col_index=0)))
        self.assertIsNone(p2.clicked)


class LegCapTests(unittest.TestCase):
    def setUp(self):
        self.old = (Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS)
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = 3, 2

    def tearDown(self):
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = self.old

    def _dc(self):
        return SelectionFilter(1.05, 3.0, 8000, 5000, Config.MARKET_DOUBLE_CHANCE, True, 0.60)

    def test_cap_reached_is_reported_as_cap_not_exhausted(self):
        p = DCProvider(FakeWithGet(batches=6, per_batch=5, delay=0.3))
        r = p.build_betslip_live(self._dc(), 5000, 8000, 3, pace=False)   # needs 1.6x; 3 legs at 1.10 = 1.33
        self.assertEqual(len(r['added']), 3)
        self.assertFalse(r['reached_target'])
        self.assertEqual(r['stop_reason'], 'cap')

    def test_pace_skips_legs_too_low_to_reach_target_within_cap(self):
        # 3 slots to reach 1.6x needs avg 1.17 per leg; every available leg is 1.10 -> all skipped
        p = DCProvider(FakeWithGet(batches=2, per_batch=5, delay=0.3))
        r = p.build_betslip_live(self._dc(), 5000, 8000, 3, pace=True)
        self.assertEqual(r['added'], [])

    def test_meets_pace_math(self):
        mp = OddsProvider._meets_pace
        sel = {'odds': 1.15}
        self.assertTrue(mp(sel, 1000.0, 1.0, 60, 1.40))      # needs avg 1.121 -> 1.15 ok
        self.assertFalse(mp({'odds': 1.05}, 1000.0, 1.0, 60, 1.40))
        self.assertTrue(mp({'odds': 1.05}, 1e9, 1.0, 10, 1.40))   # unreachable target: pace not applied
        self.assertTrue(mp({'odds': 1.01}, 5.0, 6.0, 10, 1.40))   # target already reached

    def test_default_leg_cap_is_60(self):
        self.assertGreaterEqual(Config.LIVE_MAX_LEGS, 60)


if __name__ == '__main__':
    unittest.main()
