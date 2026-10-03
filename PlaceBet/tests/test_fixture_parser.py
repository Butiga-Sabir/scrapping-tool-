import unittest
from fixture_parser import parse_fixtures_from_text


class FixtureParserTests(unittest.TestCase):
    def test_stacked_layout_with_header_and_extra_markets(self):
        text = """England - Premier League
Today 20:00
Chelsea
Fulham
+312
1.45
4.50
6.80
Today 22:00
Arsenal
Brighton
+290
1.60
4.00
5.25
Spain - La Liga
Tomorrow 18:30
Real Madrid
Getafe
+250
1.30
5.20
9.00
"""
        f = parse_fixtures_from_text(text)
        self.assertEqual(len(f), 3)
        self.assertEqual((f[0]['home_team'], f[0]['away_team']), ('Chelsea', 'Fulham'))
        self.assertEqual((f[0]['home_odds'], f[0]['draw_odds'], f[0]['away_odds']), (1.45, 4.50, 6.80))
        self.assertEqual(f[0]['competition'], 'England - Premier League')
        # header persists for following events in the same group
        self.assertEqual(f[1]['competition'], 'England - Premier League')
        self.assertEqual(f[2]['competition'], 'Spain - La Liga')

    def test_labelled_odds_and_favourite_away_is_not_reassigned(self):
        # Away team is the favourite: home_odds must stay the 1st number, not the smallest
        text = "Italy - Serie A\n29/09 21:45\nEmpoli\nInter Milan\n+200\n1\n5.50\nX\n4.10\n2\n1.55\n"
        f = parse_fixtures_from_text(text)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['home_odds'], 5.50)
        self.assertEqual(f[0]['away_odds'], 1.55)

    def test_single_line_vs_layout(self):
        text = "Germany - Bundesliga\nToday 19:30\nDortmund vs Mainz\n1.40\n5.00\n7.50\n"
        f = parse_fixtures_from_text(text)
        self.assertEqual((f[0]['home_team'], f[0]['away_team']), ('Dortmund', 'Mainz'))

    def test_page_without_odds_returns_empty(self):
        self.assertEqual(parse_fixtures_from_text("Access denied\nVerify you are human"), [])

    def test_duplicates_removed(self):
        block = "Today 20:00\nChelsea\nFulham\n+3\n1.45\n4.50\n6.80\n"
        self.assertEqual(len(parse_fixtures_from_text(block * 2)), 1)




class BreadcrumbTests(unittest.TestCase):
    def test_breadcrumb_after_teams_is_competition_not_away_team(self):
        text = """Today 15:00
Nepal U23
China U23
Football / International / Asian Games
+120
5.20
4.10
1.23
Today 16:30
Negeri Sembilan U20
Selangor U20
Football / Malaysia / Malaysia Presidents Cup U20
+80
1.12
6.00
9.50
"""
        f = parse_fixtures_from_text(text)
        self.assertEqual(len(f), 2)
        self.assertEqual((f[0]['home_team'], f[0]['away_team']), ('Nepal U23', 'China U23'))
        self.assertEqual(f[0]['away_odds'], 1.23)
        self.assertEqual(f[0]['competition'], 'Football / International / Asian Games')
        self.assertEqual((f[1]['home_team'], f[1]['away_team']), ('Negeri Sembilan U20', 'Selangor U20'))

    def test_breadcrumb_before_teams(self):
        text = "Football / Malaysia / Cup\nToday 16:30\nA FC\nB FC\n+9\n1.30\n5.00\n8.00\n"
        f = parse_fixtures_from_text(text)
        self.assertEqual((f[0]['home_team'], f[0]['away_team']), ('A FC', 'B FC'))


if __name__ == '__main__':
    unittest.main()
