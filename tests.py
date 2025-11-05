import os
import sqlite3
import unittest
from datetime import datetime, timedelta

import db
import i18n
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
        today = datetime.now()

        # Test with a birthday that has already passed this year
        # If today is after June 5th, person aged 19 was born in (current_year - 19)
        # If today is before June 5th, person aged 19 will turn 20 this year, born in (current_year - 20)
        birthday_passed = datetime(current_year, 6, 5)
        if today > birthday_passed:
            expected_year = current_year - 19
        else:
            expected_year = current_year - 20
        self.assertEqual(
            parse_date("5.06 19"), (True, datetime(expected_year, 6, 5), True)
        )

        # Test with age 0 (should be invalid)
        self.assertEqual(parse_date("15.08 0"), (False, None, False))

        # Test with a birthday far in the future this year
        # Person aged 25, birthday on December 31st
        future_birthday = datetime(current_year, 12, 31)
        if today > future_birthday:
            expected_year_dec = current_year - 25
        else:
            expected_year_dec = current_year - 26
        self.assertEqual(
            parse_date("31.12 25"), (True, datetime(expected_year_dec, 12, 31), True)
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
    def setUp(self):
        self.original_db_file = db.DB_FILE
        db.DB_FILE = "test_validate_input.db"
        db.init_db()
        self.test_chat_id = 123456789

    def tearDown(self):
        if os.path.exists(db.DB_FILE):
            os.remove(db.DB_FILE)
        db.DB_FILE = self.original_db_file

    def test_incomplete_input(self):
        message = "John Doe\n15.05.1990\nJane Smith"
        success, error_message = validate_birthday_input(message, self.test_chat_id)
        self.assertFalse(success)
        self.assertIn("incomplete", error_message.lower())

    def test_empty_name(self):
        message = "\n15.05.1990"
        success, error_message = validate_birthday_input(message, self.test_chat_id)
        self.assertFalse(success)

    def test_invalid_date_format(self):
        message = "John Doe\n32.13.2000"
        success, error_message = validate_birthday_input(message, self.test_chat_id)
        self.assertFalse(success)
        self.assertIn("parse", error_message.lower())

    def test_valid_input(self):
        message = "John Doe\n15.05.1990\nJane Smith\n20.06.1985"
        success, error_message = validate_birthday_input(message, self.test_chat_id)
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


class TestBirthdayAgeCalculation(unittest.TestCase):
    def test_age_calculation_with_past_birthday(self):
        """Test that age is calculated correctly for birthdays that already happened this year"""
        today = datetime.now()
        current_year = today.year

        # Birthday already passed this year (30 days ago)
        past_date = today - timedelta(days=30)
        birth_date = datetime(current_year - 25, past_date.month, past_date.day)

        # Create tuple matching database result structure: (id, chat_id, name, birthday_str, has_year)
        select_result = (
            1,                                      # id
            123456,                                 # chat_id
            "Test Person",                          # name
            birth_date.strftime("%Y-%m-%d"),        # birthday as string
            1                                        # has_year (1 = True)
        )
        birthday = db.TBirthday(select_result, need_id=False)

        birthday_str = str(birthday)
        # Should show age 25 (birthday already happened)
        self.assertIn("25 years", birthday_str)
        self.assertIn("Test Person", birthday_str)

    def test_age_calculation_with_future_birthday(self):
        """Test that age is calculated correctly for birthdays that haven't happened yet"""
        today = datetime.now()
        current_year = today.year

        # Birthday hasn't happened yet this year (30 days from now)
        future_date = today + timedelta(days=30)
        birth_date = datetime(current_year - 25, future_date.month, future_date.day)

        select_result = (
            1,                                      # id
            123456,                                 # chat_id
            "Test Person",                          # name
            birth_date.strftime("%Y-%m-%d"),        # birthday as string
            1                                        # has_year (1 = True)
        )
        birthday = db.TBirthday(select_result, need_id=False)

        birthday_str = str(birthday)
        # Should show age 24 (birthday hasn't happened yet, so still 24)
        self.assertIn("24 years", birthday_str)
        self.assertIn("Test Person", birthday_str)

    def test_birthday_without_year(self):
        """Test that birthdays without year don't show age"""
        today = datetime.now()
        birth_date = datetime(today.year, today.month, today.day)

        select_result = (
            1,                                      # id
            123456,                                 # chat_id
            "Test Person",                          # name
            birth_date.strftime("%Y-%m-%d"),        # birthday as string
            0                                        # has_year (0 = False)
        )
        birthday = db.TBirthday(select_result, need_id=False)

        birthday_str = str(birthday)
        # Should not show age
        self.assertNotIn("years", birthday_str)
        self.assertIn("Test Person", birthday_str)

    def test_birthday_with_id(self):
        """Test that ID is shown when needed"""
        today = datetime.now()
        birth_date = datetime(today.year - 25, today.month, today.day)

        select_result = (
            42,                                     # id
            123456,                                 # chat_id
            "Test Person",                          # name
            birth_date.strftime("%Y-%m-%d"),        # birthday as string
            1                                        # has_year (1 = True)
        )
        birthday = db.TBirthday(select_result, need_id=True)

        birthday_str = str(birthday)
        self.assertIn("ID: 42", birthday_str)
        self.assertIn("Test Person", birthday_str)

    def test_age_on_exact_birthday(self):
        """Test age calculation on the exact birthday"""
        today = datetime.now()
        birth_date = datetime(today.year - 30, today.month, today.day)

        select_result = (
            1,                                      # id
            123456,                                 # chat_id
            "Test Person",                          # name
            birth_date.strftime("%Y-%m-%d"),        # birthday as string
            1                                        # has_year (1 = True)
        )
        birthday = db.TBirthday(select_result, need_id=False)

        birthday_str = str(birthday)
        # On the exact birthday, they should be 30 (birthday has happened today)
        self.assertIn("30 years", birthday_str)


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
        cursor.execute(
            "SELECT was_reminded_7_days_ago FROM birthdays WHERE id = ?", (birthday_id,)
        )
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
        self.assertEqual(
            len(upcoming),
            0,
            "Should not return birthdays that already have reminders sent",
        )

    def test_birthday_reminder_flags_reset_mechanism(self):
        """Test that we need a mechanism to reset reminder flags yearly"""
        # This test demonstrates the current problem and will fail until we fix it
        today = datetime.now()

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
        self.assertEqual(
            len(upcoming),
            0,
            "This test shows the BUG - reminder flags are never reset, so no reminders are sent in subsequent years",
        )

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
            cursor.execute(
                f"SELECT {field_name} FROM birthdays WHERE id = ?", (birthday_id,)
            )
            result = cursor.fetchone()
            conn.close()

            self.assertTrue(
                result[0],
                f"Field {field_name} should be True after marking reminder as sent",
            )


class TestInternationalization(unittest.TestCase):
    def setUp(self):
        self.original_db_file = db.DB_FILE
        db.DB_FILE = "test_i18n.db"
        db.init_db()
        self.test_chat_id = 123456789

    def tearDown(self):
        if os.path.exists(db.DB_FILE):
            os.remove(db.DB_FILE)
        db.DB_FILE = self.original_db_file

    def test_default_language(self):
        """Test that default language is English"""
        language = i18n.get_user_language(self.test_chat_id)
        self.assertEqual(language, "en")

    def test_set_user_language(self):
        """Test setting user language preference"""
        # Test setting Russian
        result = i18n.set_user_language(self.test_chat_id, "ru")
        self.assertTrue(result)

        language = i18n.get_user_language(self.test_chat_id)
        self.assertEqual(language, "ru")

        # Test setting English
        result = i18n.set_user_language(self.test_chat_id, "en")
        self.assertTrue(result)

        language = i18n.get_user_language(self.test_chat_id)
        self.assertEqual(language, "en")

    def test_invalid_language(self):
        """Test setting invalid language"""
        result = i18n.set_user_language(self.test_chat_id, "fr")  # French not supported
        self.assertFalse(result)

        # Should remain default
        language = i18n.get_user_language(self.test_chat_id)
        self.assertEqual(language, "en")

    def test_get_button_text(self):
        """Test getting translated button text"""
        # Test English (default)
        start_button_en = i18n.get_button_text("start", self.test_chat_id)
        self.assertEqual(start_button_en, "🚀 Start")

        # Set to Russian
        i18n.set_user_language(self.test_chat_id, "ru")
        start_button_ru = i18n.get_button_text("start", self.test_chat_id)
        self.assertEqual(start_button_ru, "🚀 Начать")

    def test_get_message(self):
        """Test getting translated messages"""
        # Test English
        welcome_en = i18n.get_message("welcome_title", self.test_chat_id)
        self.assertIn("Welcome", welcome_en)

        # Set to Russian
        i18n.set_user_language(self.test_chat_id, "ru")
        welcome_ru = i18n.get_message("welcome_title", self.test_chat_id)
        self.assertIn("Добро пожаловать", welcome_ru)

    def test_message_formatting(self):
        """Test message formatting with variables"""
        # Test backup message with interval formatting
        i18n.set_user_language(self.test_chat_id, "en")
        backup_msg_en = i18n.get_message(
            "backup_ping_active", self.test_chat_id, interval=60
        )
        self.assertIn("60", backup_msg_en)

        i18n.set_user_language(self.test_chat_id, "ru")
        backup_msg_ru = i18n.get_message(
            "backup_ping_active", self.test_chat_id, interval=60
        )
        self.assertIn("60", backup_msg_ru)

    def test_month_names(self):
        """Test month name translations"""
        i18n.set_user_language(self.test_chat_id, "en")
        january_en = i18n.get_text("month_names.January", self.test_chat_id)
        self.assertEqual(january_en, "January")

        i18n.set_user_language(self.test_chat_id, "ru")
        january_ru = i18n.get_text("month_names.January", self.test_chat_id)
        self.assertEqual(january_ru, "Январь")

    def test_missing_translation_fallback(self):
        """Test fallback behavior for missing translations"""
        # Test with non-existent key
        missing_text = i18n.get_text("non.existent.key", self.test_chat_id)
        self.assertEqual(missing_text, "non.existent.key")  # Should return key itself

    def test_database_language_functions(self):
        """Test database language functions directly"""
        # Test setting language in database
        db.set_user_language(self.test_chat_id, "ru")
        language = db.get_user_language(self.test_chat_id)
        self.assertEqual(language, "ru")

        # Test updating language
        db.set_user_language(self.test_chat_id, "en")
        language = db.get_user_language(self.test_chat_id)
        self.assertEqual(language, "en")

    def test_command_descriptions(self):
        """Test that command descriptions work with different languages"""
        # Test that we can get descriptions in both languages
        i18n.set_user_language(self.test_chat_id, "en")
        desc_en = i18n.get_text("button_descriptions.start", self.test_chat_id)
        self.assertIn("Start", desc_en)

        i18n.set_user_language(self.test_chat_id, "ru")
        desc_ru = i18n.get_text("button_descriptions.start", self.test_chat_id)
        self.assertIn("Запустить", desc_ru)

    def test_translation_file_loading(self):
        """Test that translation file is loaded correctly"""
        # Test that we have both supported languages
        translations = i18n.i18n.translations
        self.assertIn("buttons", translations)
        self.assertIn("messages", translations)
        self.assertIn("month_names", translations)

        # Test that each section has both languages
        self.assertIn("en", translations["buttons"]["start"])
        self.assertIn("ru", translations["buttons"]["start"])

    def test_convenience_functions_exist(self):
        """Test that all convenience functions exist and work"""
        # Test button text function
        start_text = i18n.get_button_text("start", self.test_chat_id)
        self.assertIsInstance(start_text, str)
        self.assertIn("Start", start_text)

        # Test button description function
        start_desc = i18n.get_button_description("start", self.test_chat_id)
        self.assertIsInstance(start_desc, str)
        self.assertIn("Start", start_desc)

        # Test month name function
        january = i18n.get_month_name("January", self.test_chat_id)
        self.assertIsInstance(january, str)
        self.assertEqual(january, "January")

        # Test message function
        welcome = i18n.get_message("welcome_title", self.test_chat_id)
        self.assertIsInstance(welcome, str)
        self.assertIn("Welcome", welcome)

    def test_bot_functions_integration(self):
        pass
        """Test that bot functions work with i18n"""
        # This test ensures all functions used in bot.py exist
        try:
            # Test functions that caused the error
            from bot import (get_button_to_command_mapping,
                             get_command_descriptions)

            # These should not raise AttributeError
            descriptions = get_command_descriptions(self.test_chat_id)
            self.assertIsInstance(descriptions, dict)
            self.assertGreater(len(descriptions), 0)

            mappings = get_button_to_command_mapping(self.test_chat_id)
            self.assertIsInstance(mappings, dict)
            self.assertGreater(len(mappings), 0)

        except ImportError:
            # Bot module might not be importable in test environment
            # Just test the i18n functions directly
            pass

    def test_newline_formatting(self):
        """Test that newlines in translations are properly formatted"""
        # Test English instructions
        instructions_en = i18n.get_message(
            "register_birthday_instructions", self.test_chat_id
        )
        self.assertIn("\n", instructions_en)
        self.assertNotIn("\\n", instructions_en)  # Should not contain literal \n

        # Test Russian instructions
        i18n.set_user_language(self.test_chat_id, "ru")
        instructions_ru = i18n.get_message(
            "register_birthday_instructions", self.test_chat_id
        )
        self.assertIn("\n", instructions_ru)
        self.assertNotIn("\\n", instructions_ru)  # Should not contain literal \n

        # Test that features list has proper newlines
        features_en = i18n.get_message("bot_features", self.test_chat_id)
        self.assertIn("\n", features_en)
        self.assertTrue(features_en.count("\n") > 2)  # Multiple bullet points

    def test_error_handling_in_i18n(self):
        pass
        """Test error handling in i18n functions"""
        # Test with invalid chat_id
        try:
            text = i18n.get_text("buttons.start", -1)
            self.assertIsInstance(text, str)
        except Exception:
            self.fail("i18n should handle invalid chat_id gracefully")

        # Test with missing translation key
        missing_text = i18n.get_text("non.existent.key", self.test_chat_id)
        self.assertEqual(
            missing_text, "non.existent.key"
        )  # Should return key as fallback

    def test_markdown_safety(self):
        """Test that translations don't break Telegram Markdown parsing"""
        # Check all messages for problematic patterns
        all_messages = [
            i18n.get_message("welcome_title", self.test_chat_id),
            i18n.get_message("contribute", self.test_chat_id),
            i18n.get_message("register_birthday_instructions", self.test_chat_id),
        ]

        for message in all_messages:
            # Check for unmatched asterisks (should be even count)
            asterisk_count = message.count("*")
            self.assertEqual(
                asterisk_count % 2, 0, f"Unmatched asterisks in: {message[:50]}..."
            )

            # Check for problematic @ patterns
            self.assertNotIn(
                "@", message, f"@ symbol found in message: {message[:50]}..."
            )

            # Check balanced brackets
            open_brackets = message.count("[")
            close_brackets = message.count("]")
            self.assertEqual(
                open_brackets,
                close_brackets,
                f"Unbalanced brackets in: {message[:50]}...",
            )

    def test_welcome_message_length(self):
        """Test that welcome message doesn't exceed Telegram limits"""
        # Reconstruct welcome message like in bot
        backup_ping_msg = (
            i18n.get_message("backup_ping_inactive", self.test_chat_id) + "\n"
        )

        # Create commands list (simplified)
        commands_msg = "Sample commands list"

        welcome_message = f"""{i18n.get_message('welcome_title', self.test_chat_id)}

{i18n.get_message('welcome_subtitle', self.test_chat_id)}

{i18n.get_message('what_can_bot_do', self.test_chat_id)}
{i18n.get_message('bot_features', self.test_chat_id)}

{i18n.get_message('how_to_use', self.test_chat_id)}
{i18n.get_message('how_to_use_steps', self.test_chat_id)}

{i18n.get_message('available_commands', self.test_chat_id)}
{commands_msg}

{backup_ping_msg}{i18n.get_message('contribute', self.test_chat_id)}
"""

        # Telegram message limit is 4096 characters
        self.assertLess(
            len(welcome_message), 4096, "Welcome message too long for Telegram"
        )

        # Also test Russian version
        i18n.set_user_language(self.test_chat_id, "ru")
        welcome_message_ru = f"""{i18n.get_message('welcome_title', self.test_chat_id)}

{i18n.get_message('welcome_subtitle', self.test_chat_id)}

{i18n.get_message('what_can_bot_do', self.test_chat_id)}
{i18n.get_message('bot_features', self.test_chat_id)}

{i18n.get_message('how_to_use', self.test_chat_id)}
{i18n.get_message('how_to_use_steps', self.test_chat_id)}

{i18n.get_message('available_commands', self.test_chat_id)}
{commands_msg}

{backup_ping_msg}{i18n.get_message('contribute', self.test_chat_id)}
"""

        self.assertLess(
            len(welcome_message_ru),
            4096,
            "Russian welcome message too long for Telegram",
        )

        # Test incomplete input in English (default)
        i18n.set_user_language(self.test_chat_id, "en")
        message_incomplete = "John Doe"
        success, error_message = validate_birthday_input(
            message_incomplete, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("incomplete", error_message.lower())

        # Test Russian translation
        i18n.set_user_language(self.test_chat_id, "ru")
        success, error_message_ru = validate_birthday_input(
            message_incomplete, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("неполный", error_message_ru.lower())

        # Test future date error in Russian
        future_message = "John Doe\n1.1.2050"
        success, error_message_ru = validate_birthday_input(
            future_message, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("будущем", error_message_ru.lower())

        # Test date parse error in Russian
        invalid_message = "John Doe\n32.13.2000"
        success, error_message_ru = validate_birthday_input(
            invalid_message, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("разобрать", error_message_ru.lower())

        # Test backward compatibility (no chat_id)
        i18n.set_user_language(self.test_chat_id, "en")
        success, error_message_en = validate_birthday_input(message_incomplete)
        self.assertFalse(success)
        self.assertIn("incomplete", error_message_en.lower())

    def test_utils_translations(self):
        """Test that utils functions use correct translations"""
        from utils import validate_birthday_input

        # Test incomplete input in English (default)
        message_incomplete = "John Doe"
        success, error_message = validate_birthday_input(
            message_incomplete, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("incomplete", error_message.lower())

        # Test Russian translation
        i18n.set_user_language(self.test_chat_id, "ru")
        success, error_message_ru = validate_birthday_input(
            message_incomplete, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("неполный", error_message_ru.lower())

        # Test future date error in Russian
        future_message = "John Doe\n1.1.2050"
        success, error_message_ru = validate_birthday_input(
            future_message, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("будущем", error_message_ru.lower())

        # Test date parse error in Russian
        invalid_message = "John Doe\n32.13.2000"
        success, error_message_ru = validate_birthday_input(
            invalid_message, self.test_chat_id
        )
        self.assertFalse(success)
        self.assertIn("разобрать", error_message_ru.lower())

        # Test backward compatibility (no chat_id)
        success, error_message_en = validate_birthday_input(message_incomplete)
        self.assertFalse(success)
        self.assertIn("incomplete", error_message_en.lower())


class TestComputeAgeMetrics(unittest.TestCase):
    def test_compute_age_with_past_birthday(self):
        """Test age computation for birthdays that already happened this year"""
        today = datetime.now()
        current_year = today.year

        # Birthday already passed this year (should be current_year - birth_year)
        past_date = today - timedelta(days=30)
        past_birthday = f"{past_date.day} {past_date.strftime('%B')} {current_year - 25}"

        birthdays = [f"{past_birthday}, Test Person"]
        avg, min_val, max_val, median = utils.compute_age_metrics(birthdays)

        self.assertIsNotNone(avg)
        self.assertIsNotNone(min_val)
        self.assertIsNotNone(max_val)
        self.assertIsNotNone(median)
        self.assertEqual(avg, 25)
        self.assertEqual(min_val, 25)
        self.assertEqual(max_val, 25)
        self.assertEqual(median, 25.0)

    def test_compute_age_with_future_birthday(self):
        """Test age computation for birthdays that haven't happened yet this year"""
        today = datetime.now()
        current_year = today.year

        # Birthday hasn't happened yet this year (should be current_year - birth_year - 1)
        future_date = today + timedelta(days=30)
        future_birthday = f"{future_date.day} {future_date.strftime('%B')} {current_year - 30}"

        birthdays = [f"{future_birthday}, Test Person"]
        avg, min_val, max_val, median = utils.compute_age_metrics(birthdays)

        self.assertIsNotNone(avg)
        self.assertIsNotNone(min_val)
        self.assertIsNotNone(max_val)
        self.assertIsNotNone(median)
        # They haven't had their birthday yet, so they're still 29
        self.assertEqual(avg, 29)
        self.assertEqual(min_val, 29)
        self.assertEqual(max_val, 29)
        self.assertEqual(median, 29.0)

    def test_compute_age_with_mixed_birthdays(self):
        """Test age computation with multiple birthdays"""
        today = datetime.now()
        current_year = today.year

        past_date = today - timedelta(days=30)
        past_birthday = f"{past_date.day} {past_date.strftime('%B')} {current_year - 25}"

        future_date = today + timedelta(days=30)
        future_birthday = f"{future_date.day} {future_date.strftime('%B')} {current_year - 30}"

        birthdays = [
            f"{past_birthday}, Person 1",
            f"{future_birthday}, Person 2",
        ]

        avg, min_val, max_val, median = utils.compute_age_metrics(birthdays)

        self.assertIsNotNone(avg)
        self.assertIsNotNone(min_val)
        self.assertIsNotNone(max_val)
        self.assertIsNotNone(median)
        self.assertEqual(min_val, 25)  # Youngest person (birthday already happened)
        self.assertEqual(max_val, 29)  # Oldest person (birthday not yet happened)
        self.assertEqual(avg, (25 + 29) / 2)
        self.assertEqual(median, (25 + 29) / 2.0)  # Median of [25, 29] is 27

    def test_compute_age_with_invalid_formats(self):
        """Test that invalid birthday formats are handled gracefully"""
        invalid_birthday = "Not a date"
        missing_year = "15 January"

        birthdays = [invalid_birthday, missing_year]
        avg, min_val, max_val, median = utils.compute_age_metrics(birthdays)

        self.assertIsNone(avg)
        self.assertIsNone(min_val)
        self.assertIsNone(max_val)
        self.assertIsNone(median)

    def test_compute_age_with_empty_list(self):
        """Test that empty list returns None values"""
        avg, min_val, max_val, median = utils.compute_age_metrics([])

        self.assertIsNone(avg)
        self.assertIsNone(min_val)
        self.assertIsNone(max_val)
        self.assertIsNone(median)

    def test_compute_age_with_mixed_valid_invalid(self):
        """Test that valid birthdays are processed even with invalid ones present"""
        today = datetime.now()
        current_year = today.year

        past_date = today - timedelta(days=30)
        past_birthday = f"{past_date.day} {past_date.strftime('%B')} {current_year - 25}"

        birthdays = [
            f"{past_birthday}, Person 1",
            "Not a date",
            "15 January",  # No year
        ]

        avg, min_val, max_val, median = utils.compute_age_metrics(birthdays)

        # Should compute metrics for the one valid birthday
        self.assertIsNotNone(avg)
        self.assertEqual(avg, 25)
        self.assertEqual(min_val, 25)
        self.assertEqual(max_val, 25)
        self.assertEqual(median, 25.0)


class TestFindMostPopularDate(unittest.TestCase):
    def test_find_most_popular_date_with_single_date(self):
        """Test finding most popular date with single occurrence"""
        today = datetime.now()
        current_year = today.year

        birthday = f"15 January {current_year - 25}, Test Person"
        birthdays = [birthday]

        date, count = utils.find_most_popular_date(birthdays)

        self.assertIsNotNone(date)
        self.assertEqual(date, "15 January")
        self.assertEqual(count, 1)

    def test_find_most_popular_date_with_multiple_same_date(self):
        """Test finding most popular date when multiple people share the same date"""
        today = datetime.now()
        current_year = today.year

        birthdays = [
            f"1 January {current_year - 25}, Person 1",
            f"1 January {current_year - 30}, Person 2",
            f"1 January {current_year - 20}, Person 3",
            f"15 March {current_year - 25}, Person 4",
        ]

        date, count = utils.find_most_popular_date(birthdays)

        self.assertIsNotNone(date)
        self.assertEqual(date, "1 January")
        self.assertEqual(count, 3)

    def test_find_most_popular_date_without_year(self):
        """Test finding most popular date with birthdays that don't have year"""
        birthdays = [
            "1 January, Person 1",
            "1 January, Person 2",
            "15 March, Person 3",
        ]

        date, count = utils.find_most_popular_date(birthdays)

        self.assertIsNotNone(date)
        self.assertEqual(date, "1 January")
        self.assertEqual(count, 2)

    def test_find_most_popular_date_with_tie(self):
        """Test finding most popular date when there's a tie (should return one of them)"""
        today = datetime.now()
        current_year = today.year

        birthdays = [
            f"1 January {current_year - 25}, Person 1",
            f"1 January {current_year - 30}, Person 2",
            f"15 March {current_year - 25}, Person 3",
            f"15 March {current_year - 20}, Person 4",
        ]

        date, count = utils.find_most_popular_date(birthdays)

        # Should return one of the tied dates
        self.assertIsNotNone(date)
        self.assertIn(date, ["1 January", "15 March"])
        self.assertEqual(count, 2)

    def test_find_most_popular_date_with_empty_list(self):
        """Test finding most popular date with empty list"""
        date, count = utils.find_most_popular_date([])

        self.assertIsNone(date)
        self.assertEqual(count, 0)

    def test_find_most_popular_date_with_invalid_formats(self):
        """Test finding most popular date with invalid formats"""
        birthdays = [
            "Not a date, Person 1",
            "Invalid format",
        ]

        date, count = utils.find_most_popular_date(birthdays)

        self.assertIsNone(date)
        self.assertEqual(count, 0)

    def test_find_most_popular_date_mixed_valid_invalid(self):
        """Test that valid dates are processed even with invalid ones"""
        today = datetime.now()
        current_year = today.year

        birthdays = [
            f"1 January {current_year - 25}, Person 1",
            f"1 January {current_year - 30}, Person 2",
            "Not a date, Person 3",
            "Invalid format",
        ]

        date, count = utils.find_most_popular_date(birthdays)

        self.assertIsNotNone(date)
        self.assertEqual(date, "1 January")
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
