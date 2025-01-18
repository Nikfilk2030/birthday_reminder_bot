import logging
import sqlite3
from datetime import datetime, timedelta

import utils

DB_FILE = "data.db"

logging.basicConfig(
    level=logging.DEBUG,
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


class TBirthday:
    def __init__(self, select_result: tuple):
        if select_result is None:
            self.id = None
            self.name = None
            self.birthday = None
            return

        self.id = int(select_result[0])
        self.name = select_result[2]
        self.birthday = datetime.strptime(select_result[3], "%Y-%m-%d")

    def __str__(self):
        return f"ID: {self.id},\t{self.name},\t{self.birthday}"


def init_db() -> None:
    logging.debug(f"Initializing database at '{DB_FILE}'...")
    try:
        conn = sqlite3.connect(DB_FILE)
        logging.info("Database connected successfully.")
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
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


def get_all_birthdays(chat_id: int) -> list[str]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM birthdays WHERE chat_id = ?
        """,
            (chat_id,),
        )
        birthdays = cursor.fetchall()
        conn.close()
        logging.info(f"Retrieved birthdays for Chat ID {chat_id}: {birthdays}")
        return [str(TBirthday(birthday)) for birthday in birthdays]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving birthdays from database: {e}")
        utils.log_exception(e)


def get_all_chat_ids() -> list[int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT chat_id FROM birthdays
        """
        )
        chat_ids = cursor.fetchall()
        conn.close()
        logging.info(f"Retrieved chat IDs: {chat_ids}")
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
        logging.info(f"Registered or updated backup ping for Chat ID {chat_id}")
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
        logging.info(f"Updated last backup sent for Chat ID {chat_id}")
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
        logging.info(f"Unregistered backup ping for Chat ID {chat_id}")
    except sqlite3.Error as e:
        logging.error(f"Error unregistering backup ping: {e}")
        utils.log_fexception(e)


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
        logging.info(f"Retrieved last backup sent for Chat ID {chat_id}: {data}")
        return TBackupPingSettings(data)
    except sqlite3.Error as e:
        logging.error(f"Error retrieving last backup sent: {e}")
        utils.log_exception(e)


def register_birthday(chat_id: int, name: str, birthday: datetime) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        birthday_str = birthday.strftime("%Y-%m-%d")

        cursor.execute(
            """
            INSERT INTO birthdays (chat_id, name, birthday)
            VALUES (?, ?, ?)
            """,
            (chat_id, name, birthday_str),
        )
        conn.commit()
        conn.close()
        logging.info(
            f"Birthday registered: [Chat ID: {chat_id}, Name: {name}, Birthday: {birthday_str}]"
        )
    except sqlite3.Error as e:
        logging.error(f"Error registering birthday: {e}")
        utils.log_exception(e)


def get_upcoming_birthdays(days_ahead: int) -> list[tuple]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        today = datetime.now()
        future_date = today + timedelta(days=days_ahead)
        start_date_str = today.strftime("%m-%d")
        end_date_str = future_date.strftime("%m-%d")

        reminder_field = f"was_reminded_{days_ahead}_days_ago"

        query = f"""
            SELECT id, chat_id, name, birthday FROM birthdays
            WHERE strftime('%m-%d', birthday) BETWEEN ? AND ?
            AND {reminder_field} = FALSE
        """

        cursor.execute(query, (start_date_str, end_date_str))

        birthdays = cursor.fetchall()
        conn.close()
        logging.info(f"Retrieved upcoming birthdays (excluding reminded): {birthdays}")

        return birthdays
    except sqlite3.Error as e:
        logging.error(f"Error retrieving upcoming birthdays: {e}")
        utils.log_exception(e)


def mark_birthday_reminder_sent(birthday_id: int, days_ago: int) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        reminder_field = f"was_reminded_{days_ago}_days_ago"
        cursor.execute(
            f"""
            UPDATE birthdays
            SET {reminder_field} = TRUE
            WHERE id = ?
            """,
            (birthday_id,),
        )

        conn.commit()
        conn.close()
        logging.info(
            f"Marked reminder as sent for Birthday ID {birthday_id}, {days_ago} days ago."
        )
    except sqlite3.Error as e:
        logging.error(f"Error marking reminder as sent: {e}")
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
        conn.close()
        logging.info(f"Deleted Birthday ID {birthday_id} for Chat ID {chat_id}")

        return cursor.rowcount
    except sqlite3.Error as e:
        logging.error(f"Error deleting birthday: {e}")
        utils.log_exception(e)
