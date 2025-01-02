import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import threading
from dotenv import load_dotenv
import os
import logging

import db

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logging.critical("TELEGRAM_BOT_TOKEN is not set in the .env file!")
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the .env file!")

bot = telebot.TeleBot(TOKEN)


def send_delayed_messages(chat_id, original_message):
    for i in range(1, 6):
        bot.send_message(chat_id, f"Minute {i}: {original_message}")
        logging.debug(
            f"Sent delayed message {i} to Chat ID {chat_id}: {original_message}"
        )
        time.sleep(60)


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    logging.info(f"Received /start or /help command from Chat ID {message.chat.id}")
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    btn = KeyboardButton("/start")
    markup.add(btn)
    bot.send_message(
        message.chat.id,
        "Hello! Send me a message and I'll repeat it once a minute for 5 minutes.",
        reply_markup=markup,
    )
    logging.debug(f"Sent welcome message to Chat ID {message.chat.id}")


@bot.message_handler(commands=["backup"])
def send_backup(message):
    logging.info(f"Received /backup command from Chat ID {message.chat.id}")
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    btn = KeyboardButton("/backup")
    markup.add(btn)
    all_messages = db.get_all_messages(message.chat.id)
    bot.send_message(
        message.chat.id,
        f"Your messages: {all_messages}",
        reply_markup=markup,
    )
    logging.debug(f"Sent backup messages to Chat ID {message.chat.id}: {all_messages}")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_message = message.text
    logging.info(f"Received message from Chat ID {chat_id}: {user_message}")

    db.save_message(chat_id, user_message)

    bot.send_message(
        chat_id, "Got it! I'll send this message to you once a minute for 5 minutes."
    )
    logging.debug(f"Sent confirmation message to Chat ID {chat_id}")
    thread = threading.Thread(
        target=send_delayed_messages, args=(chat_id, user_message)
    )
    thread.start()


if __name__ == "__main__":
    db.init_db()

    logging.info("Bot is running...")
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
