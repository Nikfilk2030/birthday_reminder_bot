import unittest
from datetime import datetime

from utils import get_time, is_timestamp_valid, parse_date


class TestTimestampParser(unittest.TestCase):
    def test_is_timestamp_valid(self):
        self.assertTrue(is_timestamp_valid("1 minute"))
        self.assertTrue(is_timestamp_valid("3h"))
        self.assertTrue(is_timestamp_valid("5  днЕй"))
        self.assertTrue(is_timestamp_valid("2 месяца"))

        self.assertFalse(is_timestamp_valid("20 lightyears"))
        self.assertFalse(is_timestamp_valid("abc xyz"))
        self.assertFalse(is_timestamp_valid(""))
        self.assertFalse(is_timestamp_valid("100 123"))

    def test_get_time(self):
        self.assertEqual(get_time("1 minute"), 1)
        self.assertEqual(get_time("3 hours"), 180)
        self.assertEqual(get_time("2 месяца"), 86400)
        self.assertEqual(get_time("5  днЕй"), 7200)
        self.assertEqual(get_time("10 M"), 10)
        self.assertEqual(get_time("15 h"), 900)

        self.assertIsNone(get_time("20 lightyears"))
        self.assertIsNone(get_time("abc xyz"))
        self.assertIsNone(get_time(""))
        self.assertIsNone(get_time("100 123"))


class TestParseDate(unittest.TestCase):

    def test_valid_dates_with_year(self):
        self.assertEqual(parse_date("5.06.2001"), (True, datetime(2001, 6, 5), True))
        self.assertEqual(
            parse_date("29.02.2020"), (True, datetime(2020, 2, 29), True)
        )  # Leap year
        self.assertEqual(parse_date("15.11.1995"), (True, datetime(1995, 11, 15), True))

    def test_valid_dates_without_year(self):
        current_year = datetime.now().year
        self.assertEqual(
            parse_date("1.01"), (True, datetime(current_year, 1, 1), False)
        )
        self.assertEqual(
            parse_date("31.12"), (True, datetime(current_year, 12, 31), False)
        )

    def test_valid_dates_with_age(self):
        current_year = datetime.now().year
        self.assertEqual(
            parse_date("5.06 19"), (True, datetime(current_year - 19, 6, 5), True)
        )
        self.assertEqual(
            parse_date("15.08 0"), (True, datetime(current_year, 8, 15), True)
        )

    def test_invalid_dates(self):
        self.assertEqual(parse_date("32.12.2001"), (False, None, False))  # Invalid day
        self.assertEqual(
            parse_date("29.02.2019"), (False, None, False)
        )  # Non-leap year
        self.assertEqual(
            parse_date("15.13.2020"), (False, None, False)
        )  # Invalid month
        self.assertEqual(parse_date("0.06.2020"), (False, None, False))  # Invalid day
        self.assertEqual(parse_date("5.00.2020"), (False, None, False))  # Invalid month

    def test_invalid_formats(self):
        self.assertEqual(parse_date("abc.def"), (False, None, False))  # Invalid format
        self.assertEqual(
            parse_date("5-06-2020"), (False, None, False)
        )  # Wrong delimiter
        self.assertEqual(parse_date("31/12"), (False, None, False))  # Wrong delimiter
        self.assertEqual(
            parse_date("5.06.19.20"), (False, None, False)
        )  # Too many components

    def test_edge_cases(self):
        self.assertEqual(
            parse_date("31.04"), (False, None, False)
        )  # April has only 30 days


if __name__ == "__main__":
    unittest.main()
