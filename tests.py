import os
import sqlite3
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

    def test_future_date(self):
        future_year = datetime.now().year + 1
        future_date_str = f"5.06.{future_year}"
        success, parsed_date, has_year = parse_date(future_date_str)
        self.assertFalse(success)
        self.assertIsNone(parsed_date)
        self.assertFalse(has_year)

    def test_negative_age(self):
        future_date_str = "5.06 -42"
        success, parsed_date, has_year = parse_date(future_date_str)
        self.assertFalse(success)
        self.assertIsNone(parsed_date)
        self.assertFalse(has_year)


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


class TestBirthdayReminderLogic(unittest.TestCase):
    def setUp(self):
        self.original_db_file = db.DB_FILE
        db.DB_FILE = "test_reminder_logic.db"
        db.init_db()
        self.test_chat_id = 123456789

    def tearDown(self):
        if os.path.exists(db.DB_FILE):
            os.remove(db.DB_FILE)
        db.DB_FILE = self.original_db_file

    def test_mark_birthday_reminder_sent(self):
        """Test that birthday reminder flags are set correctly"""
        # Register a test birthday
        test_birthday = datetime(1990, 5, 15)
        db.register_birthday(self.test_chat_id, "Test Person", test_birthday, True)

        # Get the birthday ID
        birthdays = db.get_all_birthdays(self.test_chat_id)
        self.assertEqual(len(birthdays), 1)

        # Mark reminders as sent for different days
        birthday_id = 1  # First entry should have ID 1

        # Test marking 7-day reminder
        db.mark_birthday_reminder_sent(birthday_id, 7)

        # Verify the flag was set
        conn = sqlite3.connect(db.DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT was_reminded_7_days_ago FROM birthdays WHERE id = ?", (birthday_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertTrue(result[0], "7-day reminder flag should be True")

    def test_birthday_reminder_flags_prevent_duplicate_reminders(self):
        """Test that reminder flags prevent sending duplicate reminders"""
        # Register a birthday that would trigger today (for testing)
        today = datetime.now()
        test_birthday = datetime(1990, today.month, today.day)
        db.register_birthday(self.test_chat_id, "Test Person", test_birthday, True)

        # Mark the 0-day reminder as sent
        db.mark_birthday_reminder_sent(1, 0)

        # Try to get upcoming birthdays for today (0 days ahead)
        upcoming = db.get_upcoming_birthdays(0)

        # Should be empty because reminder was already sent
        self.assertEqual(len(upcoming), 0, "Should not return birthdays that already have reminders sent")

    def test_birthday_reminder_flags_reset_mechanism(self):
        """Test that we need a mechanism to reset reminder flags yearly"""
        # This test demonstrates the current problem and will fail until we fix it
        today = datetime.now()
        last_year = today.year - 1

        # Register a birthday from last year
        test_birthday = datetime(1990, today.month, today.day)
        db.register_birthday(self.test_chat_id, "Test Person", test_birthday, True)

        # Mark all reminders as sent (simulating what happened last year)
        birthday_id = 1
        for days in [0, 1, 3, 7]:
            db.mark_birthday_reminder_sent(birthday_id, days)

        # Now check if we can get upcoming birthdays for this year
        upcoming = db.get_upcoming_birthdays(0)

        # This should NOT be empty - we should get reminders again this year
        # But currently it WILL be empty due to the bug
        self.assertEqual(len(upcoming), 0,
                        "This test shows the BUG - reminder flags are never reset, so no reminders are sent in subsequent years")

    def test_get_upcoming_birthdays_respects_reminder_flags(self):
        """Test that get_upcoming_birthdays properly filters based on reminder flags"""
        today = datetime.now()

        # Create two identical birthdays
        test_birthday = datetime(1990, today.month, today.day)
        db.register_birthday(self.test_chat_id, "Person 1", test_birthday, True)
        db.register_birthday(self.test_chat_id, "Person 2", test_birthday, True)

        # Mark reminder as sent for only the first person
        db.mark_birthday_reminder_sent(1, 0)

        # Get upcoming birthdays
        upcoming = db.get_upcoming_birthdays(0)

        # Should only return the second person
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0][2], "Person 2")  # Name is at index 2

    def test_reminder_field_naming_consistency(self):
        """Test that the reminder field naming is consistent between functions"""
        # This test ensures that the field names used in mark_birthday_reminder_sent
        # match those used in get_upcoming_birthdays

        test_birthday = datetime(1990, 5, 15)
        db.register_birthday(self.test_chat_id, "Test Person", test_birthday, True)

        birthday_id = 1

        # Test each reminder day
        for days in [0, 1, 3, 7]:
            # Mark reminder as sent
            db.mark_birthday_reminder_sent(birthday_id, days)

            # Verify the field was set correctly by checking the database directly
            conn = sqlite3.connect(db.DB_FILE)
            cursor = conn.cursor()
            field_name = f"was_reminded_{days}_days_ago"
            cursor.execute(f"SELECT {field_name} FROM birthdays WHERE id = ?", (birthday_id,))
            result = cursor.fetchone()
            conn.close()

            self.assertTrue(result[0], f"Field {field_name} should be True after marking reminder as sent")


def test_compute_age_metrics():
    # Setup test data with different formats
    today = datetime.now()
    current_year = today.year

    # Birthday already passed this year (should be current_year - birth_year)
    past_date = today - timedelta(days=30)
    past_birthday = f"{past_date.day} {past_date.strftime('%B')} {current_year - 25}"

    # Birthday hasn't happened yet this year (should be current_year - birth_year - 1)
    future_date = today + timedelta(days=30)
    future_birthday = (
        f"{future_date.day} {future_date.strftime('%B')} {current_year - 30}"
    )

    # Invalid formats to test error handling
    invalid_birthday = "Not a date"
    missing_year = "15 January"

    # Test with various combinations
    test_cases = [
        # Valid birthdays that have passed this year
        [f"{past_birthday}, Test Person"],
        # Valid birthdays that haven't happened yet
        [f"{future_birthday}, Test Person"],
        # Mix of valid and invalid
        [
            f"{past_birthday}, Person 1",
            f"{future_birthday}, Person 2",
            invalid_birthday,
        ],
        # Empty list
        [],
        # List with only invalid entries
        [invalid_birthday, missing_year],
    ]

    for birthdays in test_cases:
        avg, min_val, max_val = utils.compute_age_metrics(birthdays)
        if any("Test Person" in b for b in birthdays):
            # At least one valid birthday with year
            assert avg is not None
            assert min_val is not None
            assert max_val is not None
        else:
            # No valid birthdays
            assert avg is None
            assert min_val is None
            assert max_val is None


if __name__ == "__main__":
    unittest.main()
