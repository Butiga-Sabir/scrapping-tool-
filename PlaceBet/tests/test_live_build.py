import unittest
from config import Config
from odds_provider import OddsProvider
from selector import SelectionFilter
from tests.test_scroll_loading import FakeDriver


class LiveProvider(OddsProvider):
    """OddsProvider with browser-only pieces stubbed out."""
    def __init__(self, driver):
        super().__init__()
        self.fake = driver
        self.clicked = []
    def _setup_driver(self, headless=None, keep_open=False): self.driver = self.fake
    def _dismiss_overlays(self): pass
    def _scroll_to_betslip(self): pass
    def _click_visible_row(self, sel):
        self.clicked.append(sel['home_team']); return True


class FakeWithGet(FakeDriver):
    def get(self, url): pass
    def quit(self): pass


class LiveBuildTests(unittest.TestCase):
    def setUp(self):
        self.old = (Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS)
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = 3, 2

    def tearDown(self):
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = self.old

    def _selector(self):
        return SelectionFilter(1.10, 3.0, 15000, 5000, Config.MARKET_WIN, True, 0.60)

    def test_stops_as_soon_as_target_is_reached(self):
        # each fixture: home 1.50 (61.5% implied). Target odds 3.0 -> 3 legs (3.375)
        p = LiveProvider(FakeWithGet(batches=6, per_batch=5, delay=0.5))
        seen_cb = []
        r = p.build_betslip_live(self._selector(), 5000, 15000, 8,
                                 on_added=lambda s, o, n: seen_cb.append(round(o, 3)))
        self.assertEqual(r['status'], 'ok')
        self.assertTrue(r['reached_target'])
        self.assertEqual(len(r['added']), 3)
        self.assertEqual(len(p.clicked), 3)
        self.assertEqual(seen_cb, [1.5, 2.25, 3.375])
        self.assertLess(r['fixtures_checked'], 30)       # did not scan the whole list

    def test_reports_shortfall_when_matches_run_out(self):
        p = LiveProvider(FakeWithGet(batches=1, per_batch=2, delay=0.2))   # only 2 matches exist
        r = p.build_betslip_live(self._selector(), 5000, 15000, 8)
        self.assertFalse(r['reached_target'])
        self.assertEqual(len(r['added']), 2)


if __name__ == '__main__':
    unittest.main()
