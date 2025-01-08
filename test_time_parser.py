import unittest

from utils import get_time, is_timestamp_valid


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


if __name__ == "__main__":
    unittest.main()
