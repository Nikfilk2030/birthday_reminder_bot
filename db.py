import sqlite3
import logging

DB_FILE = "messages.db"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("db.log"),
        logging.StreamHandler(),
    ],
)


def init_db():
    """
    Initialize the SQLite database by creating the `messages` table if it doesn't exist.
    """
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
            )
        """
        )
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing the database: {e}")
        raise


def save_message(chat_id: int, user_message: str):
    """
    Save a message in the database.

    Arguments:
        chat_id (int): ID of the Telegram chat.
        user_message (str): The message text sent by the user.
    """
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
        raise


def get_all_messages(chat_id: int) -> list[str]:
    """
    Fetch all messages for a specific chat ID from the database.

    Arguments:
        chat_id (int): ID of the Telegram chat.

    Returns:
        list[str]: The list of messages.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_message FROM messages WHERE chat_id = ?
        """,
            (chat_id,),
        )
        messages = cursor.fetchall()
        conn.close()
        logging.info(f"Retrieved messages for Chat ID {chat_id}: {messages}")
        return [message[0] for message in messages]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving messages from database: {e}")
        raise
