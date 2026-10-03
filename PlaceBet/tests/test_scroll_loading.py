import time
import unittest
from config import Config
from odds_provider import OddsProvider, SCROLL_STEP_JS


class FakeDriver:
    """Simulates a lazy-loading page: each scroll triggers a new batch after `delay` seconds."""
    def __init__(self, batches=4, per_batch=5, delay=1.0):
        self.batches, self.per_batch, self.delay = batches, per_batch, delay
        self.loaded = 1
        self.pending_at = None
        self.mode = '1X2'          # or 'DC'
        self.dc_per_batch = per_batch

    def _tick(self):
        if self.pending_at and time.time() >= self.pending_at:
            self.loaded += 1
            self.pending_at = None

    def execute_script(self, js, *args):
        self._tick()
        if js == SCROLL_STEP_JS:
            if self.loaded < self.batches and not self.pending_at:
                self.pending_at = time.time() + self.delay
            return self.loaded >= self.batches
        if 'innerText' in js:
            lines = []
            if self.mode == 'DC':
                lines += ["1X", "X2", "12"]
                for i in range(self.loaded * self.dc_per_batch):
                    lines += ["Today 20:00", f"Home{i}", f"Away{i}", "+10", "1.10", "1.60", "1.15"]
            else:
                for i in range(self.loaded * self.per_batch):
                    lines += ["Today 20:00", f"Home{i}", f"Away{i}", "+10", "1.50", "4.00", "6.00"]
            return "\n".join(lines)
        if 'scrollHeight' in js:
            return self.loaded * 1000
        return None


class ScrollLoadingTests(unittest.TestCase):
    def test_collects_all_lazy_batches(self):
        old = (Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS)
        Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = 3, 2
        try:
            p = OddsProvider()
            p.driver = FakeDriver(batches=4, per_batch=5, delay=1.5)  # batch arrives 1.5s after scroll
            fixtures = p._collect_fixtures_while_scrolling()
        finally:
            Config.SCROLL_LOAD_WAIT, Config.SCROLL_MAX_STALLS = old
        self.assertEqual(len(fixtures), 20)   # 4 batches x 5


if __name__ == '__main__':
    unittest.main()
