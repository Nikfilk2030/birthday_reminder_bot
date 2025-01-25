import os
import unittest
from datetime import datetime, timedelta

import db
import utils
from utils import (get_time, is_timestamp_valid, parse_date,
                   validate_birthday_input)


class TestTimestampParser(unittest.TestCase):
    def test_is_timestamp_valid(self):
        self.assertTrue(is_timestamp_valid("1 minute"))
        self.assertTrue(is_timestamp_valid("3h"))
        self.assertTrue(is_timestamp_valid("5  днЕй"))
        self.assertTrue(is_timestamp_valid("2 месяца"))

        self.assertFalse(is_timestamp_valid("20 lightyears"))
        self.assertFalse(is_timestamp_valid("abc xyz"))
        self.assertFalse(is_timestamp_valid(""))
        self.assertFalse(is_timestamp_valid("200 123"))

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
        self.assertIsNone(get_time("200 123"))


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
            parse_date("5.06 19"), (True, datetime(current_year - 20, 6, 5), True)
        )
        self.assertEqual(parse_date("15.08 0"), (False, None, False))

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

        # Test two-digit year format
        self.assertEqual(parse_date("01.01.94"), (False, None, False))

        # Test dates more than 200 years ago
        self.assertEqual(parse_date("01.01.1800"), (False, None, False))
        current_year = datetime.now().year
        self.assertEqual(
            parse_date(f"01.01 {current_year - 250}"), (False, None, False)
        )

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


class TestValidateBirthdayInput(unittest.TestCase):
    def test_incomplete_input(self):
        message = "John Doe\n15.05.1990\nJane Smith"
        success, error_message = validate_birthday_input(message)
        self.assertFalse(success)
        self.assertIn("incomplete", error_message)

    def test_empty_name(self):
        message = "\n15.05.1990"
        success, error_message = validate_birthday_input(message)
        self.assertFalse(success)

    def test_invalid_date_format(self):
        message = "John Doe\n32.13.2000"
        success, error_message = validate_birthday_input(message)
        self.assertFalse(success)
        self.assertIn("couldn't parse the date '32.13.2000'", error_message)

    def test_valid_input(self):
        message = "John Doe\n15.05.1990\nJane Smith\n20.06.1985"
        success, error_message = validate_birthday_input(message)
        self.assertTrue(success)
        self.assertEqual(error_message, "")


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Use a test database file
        self.original_db_file = db.DB_FILE
        db.DB_FILE = "test_data.db"
        db.init_db()
        self.test_chat_id = 123456789

    def tearDown(self):
        # Clean up test database
        if os.path.exists(db.DB_FILE):
            os.remove(db.DB_FILE)
        db.DB_FILE = self.original_db_file

    def test_reminder_settings(self):
        # Test default settings
        settings = db.get_reminder_settings(self.test_chat_id)
        self.assertEqual(settings, [])

        # Test updating settings
        test_days = [0, 3, 7]
        db.update_reminder_settings(self.test_chat_id, test_days)
        settings = db.get_reminder_settings(self.test_chat_id)
        self.assertEqual(settings, test_days)

    def test_birthday_operations(self):
        # Test registering birthday
        name = "Test User"
        birthday = datetime(1990, 5, 15)
        has_year = True

        db.register_birthday(self.test_chat_id, name, birthday, has_year)

        # Test retrieving birthdays
        birthdays = db.get_all_birthdays(self.test_chat_id)
        self.assertEqual(len(birthdays), 1)
        self.assertIn(name, birthdays[0])
        self.assertIn("15 May 1990", birthdays[0])

        # Test deleting birthday
        birthday_id = 1  # First entry should have ID 1
        rows_deleted = db.delete_birthday(self.test_chat_id, birthday_id)
        self.assertEqual(rows_deleted, 1)

        birthdays = db.get_all_birthdays(self.test_chat_id)
        self.assertEqual(len(birthdays), 0)

    def test_backup_ping_operations(self):
        # Test registering backup ping
        update_interval = 60  # 60 minutes
        db.register_backup_ping(self.test_chat_id, update_interval)

        # Test retrieving backup settings
        settings = db.select_from_backup_ping(self.test_chat_id)
        self.assertTrue(settings.is_active)
        self.assertEqual(settings.update_timedelta, update_interval)

        # Test unregistering backup ping
        db.unregister_backup_ping(self.test_chat_id)
        settings = db.select_from_backup_ping(self.test_chat_id)
        self.assertFalse(settings.is_active)


class TestUtils(unittest.TestCase):
    def test_is_daytime(self):
        # Mock datetime.now() to test different times
        class MockDateTime(datetime):
            @classmethod
            def now(cls):
                return cls(2024, 1, 1, 12, 0)  # Noon

        original_datetime = utils.datetime
        utils.datetime = MockDateTime

        self.assertTrue(utils.is_daytime())

        # Reset datetime
        utils.datetime = original_datetime

    def test_cleanup_old_logs(self):
        # Create a test log file
        test_log = "bot.log.test"
        with open(test_log, "w") as f:
            f.write("test log content")

        # Set file modification time to 31 days ago
        past_time = datetime.now() - timedelta(days=31)
        os.utime(test_log, (past_time.timestamp(), past_time.timestamp()))

        # Run cleanup
        utils.cleanup_old_logs(max_days=30)

        # Check file was deleted
        self.assertFalse(os.path.exists(test_log))


class TestBackupPingSettings(unittest.TestCase):
    def test_backup_settings_creation(self):
        # Test with None
        settings = db.TBackupPingSettings(None)
        self.assertFalse(settings.is_active)
        self.assertIsNone(settings.chat_id)
        self.assertIsNone(settings.last_updated_timestamp)
        self.assertIsNone(settings.update_timedelta)

        # Test with valid data
        now = datetime.now()
        test_data = (
            123456,  # chat_id
            now.strftime("%Y-%m-%d %H:%M:%S"),  # last_updated_timestamp
            60,  # update_timedelta
            1,  # is_active
        )
        settings = db.TBackupPingSettings(test_data)
        self.assertTrue(settings.is_active)
        self.assertEqual(settings.chat_id, 123456)
        self.assertEqual(settings.update_timedelta, 60)


class TestMultipleBirthdayRegistration(unittest.TestCase):
    def setUp(self):
        self.test_chat_id = 123456789
        db.DB_FILE = "test_data.db"
        db.init_db()

    def tearDown(self):
        if os.path.exists(db.DB_FILE):
            os.remove(db.DB_FILE)

    def test_multiple_birthday_registration(self):
        message = "John Doe\n15.05.1990\nJane Smith\n20.06.1985"
        success, parsed_birthdays = utils.parse_dates(message)
        self.assertTrue(success)
        self.assertEqual(len(parsed_birthdays), 2)

        for name, date, has_year in parsed_birthdays:
            db.register_birthday(self.test_chat_id, name, date, has_year)

        birthdays = db.get_all_birthdays(self.test_chat_id)
        self.assertEqual(len(birthdays), 2)
        self.assertIn("John Doe", birthdays[0])
        self.assertIn("Jane Smith", birthdays[1])

    def test_invalid_multiple_birthday_registration(self):
        message = "John Doe\n15.05.1990\nInvalid Date\n32.13.2000"
        success, _ = utils.parse_dates(message)
        self.assertFalse(success)


class TestMultipleBirthdayDeletion(unittest.TestCase):
    def setUp(self):
        self.test_chat_id = 123456789
        db.DB_FILE = "test_data.db"
        db.init_db()

        # Register some birthdays
        db.register_birthday(self.test_chat_id, "John Doe", datetime(1990, 5, 15), True)
        db.register_birthday(
            self.test_chat_id, "Jane Smith", datetime(1985, 6, 20), True
        )
        db.register_birthday(
            self.test_chat_id, "Alice Johnson", datetime(1992, 7, 25), True
        )

    def tearDown(self):
        if os.path.exists(db.DB_FILE):
            os.remove(db.DB_FILE)

    def test_delete_multiple_birthdays(self):
        # Attempt to delete multiple birthdays
        message = "1, 2"
        chat_id = self.test_chat_id

        # Simulate deletion
        birthday_ids = [int(id_str.strip()) for id_str in message.split(",")]
        deleted_ids = []
        not_found_ids = []

        for birthday_id in birthday_ids:
            deleted_rows = db.delete_birthday(chat_id, birthday_id)
            if deleted_rows > 0:
                deleted_ids.append(birthday_id)
            else:
                not_found_ids.append(birthday_id)

        self.assertEqual(deleted_ids, [1, 2])
        self.assertEqual(not_found_ids, [])

        # Check remaining birthdays
        remaining_birthdays = db.get_all_birthdays(chat_id)
        self.assertEqual(len(remaining_birthdays), 1)
        self.assertIn("Alice Johnson", remaining_birthdays[0])

    def test_delete_nonexistent_birthdays(self):
        # Attempt to delete a non-existent birthday
        message = "99"
        chat_id = self.test_chat_id

        birthday_ids = [int(id_str.strip()) for id_str in message.split(",")]
        deleted_ids = []
        not_found_ids = []

        for birthday_id in birthday_ids:
            deleted_rows = db.delete_birthday(chat_id, birthday_id)
            if deleted_rows > 0:
                deleted_ids.append(birthday_id)
            else:
                not_found_ids.append(birthday_id)

        self.assertEqual(deleted_ids, [])
        self.assertEqual(not_found_ids, [99])


if __name__ == "__main__":
    unittest.main()
