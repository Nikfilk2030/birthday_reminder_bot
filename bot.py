import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import threading
from dotenv import load_dotenv
import os
import logging

import db
import utils

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]",
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


def get_main_buttons():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)

    buttons = [
        KeyboardButton("/start"),
        KeyboardButton("/backup"),
        KeyboardButton("/register"),
        KeyboardButton("/unregister"),
    ]

    for button in buttons:
        markup.add(button)

    return markup


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

    # get info about backup settings
    backup_ping_settings = db.select_from_backup_ping(message.chat.id)
    if backup_ping_settings.is_active:
        backup_ping_msg = f"You have an active backup ping every {backup_ping_settings.update_timedelta} minute(s).\n"
    else:
        backup_ping_msg = "You have no active backup ping.\n"

    bot.send_message(
        message.chat.id,
        "Hello! Send me a message and I'll repeat it once a minute for 5 minutes.\n"
        "Also, you can use the buttons below for navigation.\n\n" + backup_ping_msg,
        reply_markup=get_main_buttons(),
    )
    logging.debug(f"Sent welcome message to Chat ID {message.chat.id}")


@bot.message_handler(commands=["backup"])
def send_backup(message):
    logging.info(f"Received /backup command from Chat ID {message.chat.id}")
    all_messages = "\n".join(db.get_all_messages(message.chat.id))

    bot.send_message(
        message.chat.id,
        f"Your messages:\n{all_messages if all_messages else 'No messages found.'}",
        reply_markup=get_main_buttons(),
    )
    logging.debug(f"Sent backup messages to Chat ID {message.chat.id}: {all_messages}")


def process_backup_pings():
    while True:
        time.sleep(60)
        try:
            all_chat_ids = db.get_all_chat_ids()
            logging.debug(f"Processing backup pings for Chat IDs: {all_chat_ids}")

            for chat_id in all_chat_ids:
                chat_id = chat_id[0]

                backup_ping_settings = db.select_from_backup_ping(chat_id)

                if backup_ping_settings.is_active == False:
                    continue

                now = int(time.time())
                delta_seconds = now - backup_ping_settings.last_updated_timestamp
                settings_delta_seconds = backup_ping_settings.update_timedelta * 60

                if delta_seconds < settings_delta_seconds:
                    continue

                db.update_backup_ping(chat_id)

                all_messages = "\n".join(db.get_all_messages(chat_id))
                if all_messages:
                    bot.send_message(
                        chat_id,
                        f"Here's your latest backup:\n{all_messages}",
                    )
                    logging.info(f"Sent backup to Chat ID {chat_id}.")
                else:
                    bot.send_message(chat_id, "You have no saved messages.")
                    logging.info(f"No messages found for Chat ID {chat_id}.")

        except Exception as e:
            logging.error(f"Error during backup ping processing: {e}")
            utils.log_exception(e)


@bot.message_handler(commands=["register"])
def register_backup(message):
    chat_id = message.chat.id
    user_message = message.text

    try:
        user_message = user_message.replace("/register", "").strip()

        if not utils.is_timestamp_valid(user_message):
            bot.send_message(
                chat_id,
                "Invalid input format. Please use the following format: `/register [interval] month`, or `/register [interval] месяцев`",
                reply_markup=get_main_buttons(),
            )
            return

        interval_in_minutes = utils.get_time(user_message)

        db.register_backup_ping(chat_id, interval_in_minutes)

        bot.send_message(
            chat_id,
            f"Auto-backup registered! You'll receive backups every {interval_in_minutes} minute(s).",
            reply_markup=get_main_buttons(),
        )
        logging.info(
            f"Registered auto-backup for Chat ID {chat_id} with interval {interval_in_minutes} minute(s)."
        )

    except Exception as e:
        logging.error(f"Error processing /register command for Chat ID {chat_id}: {e}")
        bot.send_message(
            chat_id,
            "Invalid input format. Please use the following format: `/register [interval]m`, e.g., `/register 1m`.",
            reply_markup=get_main_buttons(),
        )
        utils.log_exception(e)


@bot.message_handler(commands=["unregister"])
def unregister_backup(message):
    chat_id = message.chat.id
    db.unregister_backup_ping(chat_id)
    bot.send_message(
        chat_id,
        "Auto-backup unregistered.",
        reply_markup=get_main_buttons(),
    )
    logging.info(f"Unregistered auto-backup for Chat ID {chat_id}.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_message = message.text
    logging.info(f"Received message from Chat ID {chat_id}: {user_message}")

    # # Interpret user-specific buttons
    # if user_message.lower() == "help":
    #     bot.send_message(
    #         chat_id,
    #         "This is a help message! Use /backup to see all your saved messages, "
    #         "/start to restart the bot, or simply type a message to save it.",
    #         reply_markup=get_main_buttons(),
    #     )
    #     return
    # elif user_message.lower() == "cancel":
    #     bot.send_message(chat_id, "Action canceled.", reply_markup=get_main_buttons())
    #     return

    db.save_message(chat_id, user_message)

    bot.send_message(
        chat_id,
        "Got it! I'll send this message to you once a minute for 5 minutes.",
        reply_markup=get_main_buttons(),
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
        logging.info("Starting backup ping thread...")
        thread = threading.Thread(target=process_backup_pings)
        thread.start()

        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)

    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
        utils.log_exception(e)
