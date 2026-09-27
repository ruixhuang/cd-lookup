import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scan import parse_name  # noqa: E402


class ParseNameTests(unittest.TestCase):
    def check(self, name, artist, title, year=None, catalog=None):
        got = parse_name(name)
        self.assertEqual(got, {"artist": artist, "title": title, "year": year, "catalog": catalog}, name)

    def test_plain(self):
        self.check("Abbey Lincoln - Abbey is Blue", "Abbey Lincoln", "Abbey is Blue")

    def test_ecm_catalog_and_trailing_year(self):
        self.check("[ECM 1009] - Chick Corea & Dave Holland & Barry Altschul - A.R.C (1971)",
                   "Chick Corea & Dave Holland & Barry Altschul", "A.R.C", 1971, "ECM 1009")

    def test_ecm_no_artist_separator(self):
        self.check("[ECM 1005] - music improvisation company 1968-1971 (1970)",
                   "", "music improvisation company 1968-1971", 1970, "ECM 1005")

    def test_compilation(self):
        self.check("- The Best of CTI", "", "The Best of CTI")
        self.check("- Tower Of Song; The Songs Of Leonard Cohen", "", "Tower Of Song; The Songs Of Leonard Cohen")

    def test_leading_year_glued(self):
        self.check("1986-Phalanx - Got Something Good For You", "Phalanx", "Got Something Good For You", 1986)

    def test_leading_year_only(self):
        self.check("1994 - Is What It Is", "", "Is What It Is", 1994)

    def test_bracket_not_at_start_is_kept(self):
        self.check("Emmylou Harris - Evangeline [remastered 2013]", "Emmylou Harris", "Evangeline [remastered 2013]")

    def test_chinese(self):
        self.check("崔健 - 红旗下的蛋", "崔健", "红旗下的蛋")

    def test_middle_year(self):
        self.check("Johnny Cash - 1962 - Ride This Train", "Johnny Cash", "Ride This Train", 1962)

    def test_no_separator(self):
        self.check("Buddy Rich", "", "Buddy Rich")

    def test_year_range_in_parens_is_not_a_year(self):
        self.check("Albert King (1924-1992) - Best of Albert King Vol. 1 (1968-1973)",
                   "Albert King (1924-1992)", "Best of Albert King Vol. 1 (1968-1973)")

    def test_multiple_separators_split_on_first(self):
        self.check("Ahmad Jamal - Chicago Revisited - Live At Joe Segal's Jazz Showcase",
                   "Ahmad Jamal", "Chicago Revisited - Live At Joe Segal's Jazz Showcase")

    def test_hyphen_without_spaces_is_not_a_separator(self):
        self.check("AC-DC - Back In Black", "AC-DC", "Back In Black")


if __name__ == "__main__":
    unittest.main()
