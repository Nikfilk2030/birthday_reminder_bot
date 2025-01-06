import sqlite3
import logging

from datetime import datetime

DB_FILE = "messages.db"

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


def init_db() -> None:
    logging.debug(f"Initializing database at '{DB_FILE}'...")
    try:
        conn = sqlite3.connect(DB_FILE)
        logging.info("Database connected successfully.")
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing the database: {e}")
        utils.log_exception(e)
        raise


def save_message(chat_id: int, user_message: str) -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (chat_id, user_message)
            VALUES (?, ?)
        """,
            (chat_id, user_message),
        )
        conn.commit()
        conn.close()
        logging.info(
            f"Message saved to database: [Chat ID: {chat_id}, Message: {user_message}]"
        )
    except sqlite3.Error as e:
        logging.error(f"Error saving message to database: {e}")
        utils.log_exception(e)
        raise


def get_all_messages(chat_id: int) -> list[str]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM messages WHERE chat_id = ?
        """,
            (chat_id,),
        )
        messages = cursor.fetchall()
        conn.close()
        logging.info(f"Retrieved messages for Chat ID {chat_id}: {messages}")
        return [str(message) for message in messages]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving messages from database: {e}")
        utils.log_exception(e)
        raise


def get_all_chat_ids() -> list[int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT chat_id FROM messages
        """
        )
        chat_ids = cursor.fetchall()
        conn.close()
        logging.info(f"Retrieved chat IDs: {chat_ids}")
        return chat_ids
    except sqlite3.Error as e:
        logging.error(f"Error retrieving messages from database: {e}")
        utils.log_exception(e)
        raise


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
        raise


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
        raise


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
        utils.log_exception(e)
        raise


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
        raise
