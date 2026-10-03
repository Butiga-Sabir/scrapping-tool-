import unittest
from config import Config
from fixture_parser import parse_fixtures_from_text
from odds_provider import OddsProvider, FIND_ROW_ODDS_JS, BUTTON_LABEL_JS
from selector import SelectionFilter


def sf():
    return SelectionFilter(1.05, 3.0, 6500, 5000, Config.MARKET_DOUBLE_CHANCE, True, 0.60)


class ColumnOrderParsing(unittest.TestCase):
    def test_header_order_1x_x2_12_is_respected(self):
        text = "1X\nX2\n12\nToday 20:00\nArsenal\nBrighton\n+9\n1.10\n1.60\n1.15\n"
        fx = parse_fixtures_from_text(text, 'DC')[0]
        self.assertEqual((fx['dc_1x'], fx['dc_x2'], fx['dc_12']), (1.10, 1.60, 1.15))
        self.assertEqual(fx['dc_positions'], {'1x': 0, 'x2': 1, '12': 2})

    def test_labels_printed_next_to_prices_win(self):
        text = "Today 20:00\nArsenal\nBrighton\n+9\n12\n1.15\n1X\n1.10\nX2\n1.60\n"
        fx = parse_fixtures_from_text(text, 'DC')[0]
        self.assertEqual((fx['dc_1x'], fx['dc_12'], fx['dc_x2']), (1.10, 1.15, 1.60))
        self.assertEqual(fx['dc_positions']['1x'], 1)

    def test_default_order_when_page_gives_no_labels(self):
        # no header, no labels -> BetPawa's real layout (confirmed): 1X, X2, 12
        text = "Today 20:00\nArsenal\nBrighton\n+9\n1.10\n1.60\n1.15\n"
        fx = parse_fixtures_from_text(text, 'DC')[0]
        self.assertEqual(fx['dc_positions'], {'1x': 0, 'x2': 1, '12': 2})
        self.assertEqual((fx['dc_1x'], fx['dc_x2'], fx['dc_12']), (1.10, 1.60, 1.15))

    def test_selector_never_returns_12_and_carries_column(self):
        text = "1X\nX2\n12\nToday 20:00\nArsenal\nBrighton\n+9\n1.10\n1.60\n1.15\n"
        fx = parse_fixtures_from_text(text, 'DC')[0]
        sel = sf().best_dc_selection(fx)
        self.assertEqual(sel['selection'], '1X')
        self.assertEqual(sel['col_index'], 0)
        # make 12 the best-looking price: still must not be chosen
        fx2 = dict(fx, dc_1x=1.40, dc_12=1.02, dc_x2=2.6)
        sel2 = sf().best_dc_selection(fx2)
        self.assertTrue(sel2 is None or sel2['selection'] in ('1X', 'X2'))


class El:
    def __init__(self, text, label=None):
        self.text, self.label = text, label


class ClickProvider(OddsProvider):
    def __init__(self, buttons):
        super().__init__()
        self.buttons, self.clicked = buttons, None
        self.driver = self
    def execute_script(self, js, *args):
        if js == FIND_ROW_ODDS_JS:
            return self.buttons
        if js == BUTTON_LABEL_JS:
            return args[0].label
        return ''
    def _body_text(self): return ''
    def _safe_click(self, el): self.clicked = el; return True


def sel(name, odds, col):
    return dict(home_team='Arsenal', away_team='Brighton', selection=name, odds=odds, col_index=col)


class ClickTests(unittest.TestCase):
    def test_clicks_detected_column_not_a_fixed_position(self):
        b = [El('1.10'), El('1.60'), El('1.15')]          # page order: 1X, X2, 12
        p = ClickProvider(b)
        self.assertTrue(p._click_visible_row(sel('X2', 1.60, 1)))
        self.assertIs(p.clicked, b[1])

    def test_dom_labels_override_position(self):
        b = [El('1.15', '12'), El('1.10', '1x'), El('1.60', 'x2')]
        p = ClickProvider(b)
        self.assertTrue(p._click_visible_row(sel('1X', 1.10, 0)))   # position says 0, label says 1
        self.assertIs(p.clicked, b[1])

    def test_never_clicks_a_button_labelled_12(self):
        b = [El('1.10', '12'), El('1.15', None), El('1.60', None)]
        p = ClickProvider(b)
        self.assertFalse(p._click_visible_row(sel('1X', 1.10, 0)))
        self.assertIsNone(p.clicked)

    def test_12_selection_is_refused(self):
        p = ClickProvider([El('1.10'), El('1.15'), El('1.60')])
        self.assertFalse(p._click_visible_row(sel('12', 1.15, 1)))
        self.assertIsNone(p.clicked)


if __name__ == '__main__':
    unittest.main()
