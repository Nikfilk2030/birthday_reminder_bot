import logging
import os
import sqlite3
from datetime import datetime, timedelta

import utils

# Database file selection based on environment
DB_FILE = os.getenv("DB_FILE", "data.db")
PRESTABLE_MODE = os.getenv("PRESTABLE_MODE", "false").lower() == "true"

# Use separate database for prestable
if PRESTABLE_MODE:
    DB_FILE = "data_prestable.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)


class TBackupPingSettings:
    def __init__(self, select_result: tuple):
        if select_result is None:
            self.chat_id = None
            self.last_updated_timestamp = None
            self.update_timedelta = None
            self.is_active = False
            return

        self.chat_id = int(select_result[0])
        self.last_updated_timestamp = int(
            datetime.strptime(select_result[1], "%Y-%m-%d %H:%M:%S").timestamp()
        )
        self.update_timedelta = int(select_result[2])
        self.is_active = bool(select_result[3])

    def __str__(self):
        return (
            f"Chat ID: {self.chat_id}, "
            f"Last Updated Timestamp: {self.last_updated_timestamp}, "
            f"Update Timedelta: {self.update_timedelta}, "
            f"Is Active: {self.is_active}"
        )


def _safe_replace_year(date: datetime, new_year: int) -> datetime:
    """
    Safely replace the year in a date, handling leap year edge cases.

    If the date is February 29th and the new year is not a leap year,
    returns February 28th of the new year instead.

    Args:
        date: The original date
        new_year: The year to replace

    Returns:
        A new datetime with the replaced year (or Feb 28 if Feb 29 -> non-leap year)
    """
    try:
        return date.replace(year=new_year)
    except ValueError:
        # This happens when date is Feb 29 and new_year is not a leap year
        # Return Feb 28 of the new year instead
        if date.month == 2 and date.day == 29:
            return datetime(new_year, 2, 28)
        raise


class TBirthday:
    def __init__(self, select_result: tuple, need_id: bool = False):
        self.need_id = need_id

        if select_result is None:
            self.id = None
            self.name = None
            self.birthday = None
            self.has_year = False
            return

        self.id = int(select_result[0])
        self.name = select_result[2]
        self.birthday = datetime.strptime(select_result[3], "%Y-%m-%d")
        self.has_year = bool(select_result[4])

    def __str__(self):
        birthday_format = "%d %B %Y" if self.has_year else "%d %B"
        birthday_str = self.birthday.strftime(birthday_format)

        age_text = ""
        if self.has_year:
            current_year = datetime.now().year
            age = current_year - self.birthday.year
            # Check if birthday hasn't happened yet this year
            # Handle leap year edge case (Feb 29 -> non-leap year)
            birthday_this_year = _safe_replace_year(self.birthday, current_year)
            if datetime.now() < birthday_this_year:
                age -= 1
            age_text = f", _(Current age: {age} years)_"

        id_text = f", ID: {self.id}" if self.need_id else ""

        return f"{birthday_str}, {self.name}{age_text}{id_text}"


def init_db() -> None:
    logging.debug(f"Initializing database at '{DB_FILE}'...")
    try:
        conn = sqlite3.connect(DB_FILE)
        logging.info("Database connected successfully.")
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_reminder_settings (
                chat_id INTEGER PRIMARY KEY,
                reminder_days TEXT DEFAULT "0,1,3,7",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_language_settings (
                chat_id INTEGER PRIMARY KEY,
                language_code TEXT DEFAULT "en",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS backup_ping_settings (
                chat_id INTEGER PRIMARY KEY NOT NULL,
                last_updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                update_timedelta INT NOT NULL,
                is_active BOOLEAN DEFAULT FALSE
            );
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS birthdays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                birthday DATE NOT NULL,
                has_year BOOLEAN DEFAULT FALSE,
                was_reminded_0_days_ago BOOLEAN DEFAULT FALSE,
                was_reminded_1_days_ago BOOLEAN DEFAULT FALSE,
                was_reminded_3_days_ago BOOLEAN DEFAULT FALSE,
                was_reminded_7_days_ago BOOLEAN DEFAULT FALSE
            );
        """
        )
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing the database: {e}")
        utils.log_exception(e)


def get_reminder_settings(chat_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT reminder_days FROM user_reminder_settings WHERE chat_id = ?", (chat_id,)
    )
    result = cursor.fetchone()

    conn.close()

    if result and result[0]:
        return [int(x) for x in result[0].split(",")]
    return []


def update_reminder_settings(chat_id, days):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    days_str = ",".join(map(str, sorted(days)))

    cursor.execute(
        """
        INSERT OR REPLACE INTO user_reminder_settings (chat_id, reminder_days)
        VALUES (?, ?)
    """,
        (chat_id, days_str),
    )

    conn.commit()
    conn.close()


def get_all_birthdays_for_all_chats(need_id: bool = False) -> list[str]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH ordered_birthdays AS (
                SELECT *,
                    CASE
                        WHEN strftime('%m-%d', birthday) >= strftime('%m-%d', 'now')
                        THEN 0  -- This year
                        ELSE 1  -- Next year
                    END as year_offset,
                    strftime('%m-%d', birthday) as date_without_year
                FROM birthdays
            )
            SELECT * FROM ordered_birthdays
            ORDER BY year_offset, date_without_year
            """,
        )
        birthdays = cursor.fetchall()
        conn.close()
        return [str(TBirthday(birthday, need_id)) for birthday in birthdays]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving birthdays from database: {e}")
        utils.log_exception(e)


def get_all_birthdays(chat_id: int, need_id: bool = False) -> list[str]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH ordered_birthdays AS (
                SELECT *,
                    CASE
                        WHEN strftime('%m-%d', birthday) >= strftime('%m-%d', 'now')
                        THEN 0  -- This year
                        ELSE 1  -- Next year
                    END as year_offset,
                    strftime('%m-%d', birthday) as date_without_year
                FROM birthdays
                WHERE chat_id = ?
            )
            SELECT * FROM ordered_birthdays
            ORDER BY year_offset, date_without_year
            """,
            (chat_id,),
        )
        birthdays = cursor.fetchall()
        conn.close()
        return [str(TBirthday(birthday, need_id)) for birthday in birthdays]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving birthdays from database: {e}")
        utils.log_exception(e)


def get_all_chat_ids() -> list[int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT chat_id FROM user_reminder_settings
        """
        )
        chat_ids = cursor.fetchall()
        conn.close()
        return chat_ids
    except sqlite3.Error as e:
        logging.error(f"Error retrieving chat_ids from database: {e}")
        utils.log_exception(e)


def register_backup_ping(chat_id: int, update_timedelta: int) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO backup_ping_settings (chat_id, is_active, last_updated_timestamp, update_timedelta)
            VALUES (?, TRUE, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                is_active = TRUE,
                last_updated_timestamp = CURRENT_TIMESTAMP,
                update_timedelta = ?
            """,
            (chat_id, update_timedelta, update_timedelta),
        )

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error registering backup ping: {e}")
        utils.log_exception(e)


def update_backup_ping(chat_id: int) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE backup_ping_settings
            SET last_updated_timestamp = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """,
            (chat_id,),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error updating last backup sent: {e}")
        utils.log_exception(e)


def unregister_backup_ping(chat_id: int) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE backup_ping_settings
            SET is_active = FALSE
            WHERE chat_id = ?
        """,
            (chat_id,),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error unregistering backup ping: {e}")
        utils.log_exception(e)


def select_from_backup_ping(chat_id: int) -> TBackupPingSettings:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM backup_ping_settings WHERE chat_id = ?
        """,
            (chat_id,),
        )
        data = cursor.fetchone()
        conn.close()
        return TBackupPingSettings(data)
    except sqlite3.Error as e:
        logging.error(f"Error retrieving last backup sent: {e}")
        utils.log_exception(e)


def register_birthday(
    chat_id: int, name: str, birthday: datetime, has_year: bool
) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        birthday_str = birthday.strftime("%Y-%m-%d")

        cursor.execute(
            """
            INSERT INTO birthdays (chat_id, name, birthday, has_year)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, name, birthday_str, has_year),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error registering birthday: {e}")
        utils.log_exception(e)


def get_upcoming_birthdays(days_ahead: int) -> list[tuple]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        today = datetime.now()
        future_date = today + timedelta(days=days_ahead)
        start_date_str = future_date.strftime("%m-%d")
        end_date_str = future_date.strftime("%m-%d")

        reminder_field = f"was_reminded_{days_ahead}_days_ago"

        query = f"""
            SELECT id, chat_id, name, birthday, has_year FROM birthdays
            WHERE strftime('%m-%d', birthday) BETWEEN ? AND ?
            AND {reminder_field} = FALSE
        """

        cursor.execute(query, (start_date_str, end_date_str))

        birthdays = cursor.fetchall()
        conn.close()

        return birthdays
    except sqlite3.Error as e:
        logging.error(f"Error retrieving upcoming birthdays: {e}")
        utils.log_exception(e)


def mark_birthday_reminder_sent(birthday_id: int, days_until: int) -> None:
    """
    Mark that a birthday reminder has been sent for a specific number of days.

    Args:
        birthday_id: The ID of the birthday record
        days_until: Number of days until the birthday (0, 1, 3, or 7)
    """
    try:
        # Validate input to prevent SQL injection
        if days_until not in [0, 1, 3, 7]:
            logging.error(
                f"Invalid days_until value: {days_until}. Must be 0, 1, 3, or 7."
            )
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Use proper parameterized query for safety
        if days_until == 0:
            cursor.execute(
                "UPDATE birthdays SET was_reminded_0_days_ago = TRUE WHERE id = ?",
                (birthday_id,),
            )
        elif days_until == 1:
            cursor.execute(
                "UPDATE birthdays SET was_reminded_1_days_ago = TRUE WHERE id = ?",
                (birthday_id,),
            )
        elif days_until == 3:
            cursor.execute(
                "UPDATE birthdays SET was_reminded_3_days_ago = TRUE WHERE id = ?",
                (birthday_id,),
            )
        elif days_until == 7:
            cursor.execute(
                "UPDATE birthdays SET was_reminded_7_days_ago = TRUE WHERE id = ?",
                (birthday_id,),
            )

        conn.commit()
        conn.close()

        logging.debug(
            f"Marked {days_until}-day reminder as sent for birthday ID {birthday_id}"
        )

    except sqlite3.Error as e:
        logging.error(f"Error marking reminder as sent: {e}")
        utils.log_exception(e)


def reset_birthday_reminder_flags() -> None:
    """
    Reset reminder flags for birthdays that are:
    - More than 10 days in the future
    - More than 10 days in the past
    This ensures that reminders will be sent again next year and prevents duplicate reminders.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Reset flags for birthdays that are either:
        # 1. More than 10 days in the past
        # 2. More than 10 days in the future
        query = """
            UPDATE birthdays
            SET was_reminded_0_days_ago = FALSE,
                was_reminded_1_days_ago = FALSE,
                was_reminded_3_days_ago = FALSE,
                was_reminded_7_days_ago = FALSE
            WHERE (
                -- Case 1: Birthday is more than 10 days in the past
                (
                    strftime('%m-%d', birthday) < strftime('%m-%d', date('now', '-10 days'))
                    AND
                    strftime('%m-%d', birthday) < strftime('%m-%d', 'now')
                )
                OR
                -- Case 2: Birthday is more than 10 days in the future
                (
                    strftime('%m-%d', birthday) > strftime('%m-%d', date('now', '+10 days'))
                    AND
                    strftime('%m-%d', birthday) > strftime('%m-%d', 'now')
                )
            )
        """

        cursor.execute(query)
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            logging.info(f"Reset reminder flags for {rows_affected} birthdays")

    except sqlite3.Error as e:
        logging.error(f"Error resetting birthday reminder flags: {e}")
        utils.log_exception(e)


def delete_birthday(chat_id: int, birthday_id: int) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM birthdays
            WHERE id = ? AND chat_id = ?
            """,
            (birthday_id, chat_id),
        )

        conn.commit()
        deleted_rows = cursor.rowcount
        conn.close()

        return deleted_rows
    except sqlite3.Error as e:
        logging.error(f"Error deleting birthday: {e}")
        utils.log_exception(e)
        return 0


def get_user_language(chat_id: int) -> str:
    """Get user's language preference. Returns 'en' as default."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT language_code FROM user_language_settings WHERE chat_id = ?",
            (chat_id,),
        )
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else "en"
    except sqlite3.Error as e:
        logging.error(f"Error getting user language: {e}")
        utils.log_exception(e)
        return "en"


def set_user_language(chat_id: int, language_code: str) -> None:
    """Set user's language preference."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_language_settings (chat_id, language_code, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                language_code = ?,
                updated_at = CURRENT_TIMESTAMP
            """,
            (chat_id, language_code, language_code),
        )

        conn.commit()
        conn.close()

        logging.info(f"Set language to '{language_code}' for chat {chat_id}")

    except sqlite3.Error as e:
        logging.error(f"Error setting user language: {e}")
        utils.log_exception(e)
