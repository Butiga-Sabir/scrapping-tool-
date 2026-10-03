import unittest
from unittest import mock

from odds_provider import OddsProvider


class ManualInputTests(unittest.TestCase):
    def test_done_is_ignored_until_at_least_one_fixture(self):
        provider = OddsProvider()

        with mock.patch("builtins.input", side_effect=[
            "done",
            "Arsenal vs Chelsea, 1.45, 2.60",
            "done",
        ]):
            with mock.patch("builtins.print"):
                fixtures = provider._get_custom_input()

        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["home_team"], "Arsenal")
        self.assertEqual(fixtures[0]["away_team"], "Chelsea")

    def test_short_v_separator_is_supported(self):
        provider = OddsProvider()

        with mock.patch("builtins.input", side_effect=[
            "Arsenal v Chelsea, 1.45, 2.60",
            "done",
        ]):
            with mock.patch("builtins.print"):
                fixtures = provider._get_custom_input()

        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["home_team"], "Arsenal")
        self.assertEqual(fixtures[0]["away_team"], "Chelsea")


if __name__ == "__main__":
    unittest.main()
