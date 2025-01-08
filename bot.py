import enum
import logging
import os
import threading
import time

import telebot
from dotenv import load_dotenv
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

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

user_states = {}


class TUserState(enum.Enum):
    Default = "default"
    AwaitingInterval = "awaiting_interval"
    AwaitingNameAndDate = "awaiting_name_and_date"


class TCommand(enum.Enum):
    Start = "start"
    Backup = "backup"
    RegisterBirthday = "register_birthday"
    RegisterBackup = "register_backup"
    UnregisterBackup = "unregister_backup"


button_to_command = {
    "🚀 Start": TCommand.Start,
    "/start": TCommand.Start,
    "/help": TCommand.Start,
    #
    "💾 Backup": TCommand.Backup,
    "/backup": TCommand.Backup,
    #
    "🎉 Register Birthday": TCommand.RegisterBirthday,
    "/register_birthday": TCommand.RegisterBirthday,
    #
    "🔐 Register Backup": TCommand.RegisterBackup,
    "/register_backup": TCommand.RegisterBackup,
    #
    "🚫 Unregister Backup": TCommand.UnregisterBackup,
    "/unregister_backup": TCommand.UnregisterBackup,
}


def get_main_buttons():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    buttons = [
        KeyboardButton("🚀 Start"),
        KeyboardButton("💾 Backup"),
        KeyboardButton("🎉 Register Birthday"),
        KeyboardButton("🔐 Register Backup"),
        KeyboardButton("🚫 Unregister Backup"),
    ]

    markup.add(*buttons)

    return markup


def send_delayed_messages(chat_id, original_message):
    for i in range(1, 6):
        bot.send_message(chat_id, f"Minute {i}: {original_message}")
        logging.debug(
            f"Sent delayed message {i} to Chat ID {chat_id}: {original_message}"
        )
        time.sleep(60)


def handle_start(message):
    logging.info(f"Received /start or /help command from Chat ID {message.chat.id}")

    user_states[message.chat.id] = TUserState.Default

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


def send_backup(message):
    logging.info(f"Received /backup command from Chat ID {message.chat.id}")
    all_messages = "\n".join(db.get_all_messages(message.chat.id))

    bot.send_message(
        message.chat.id,
        f"Your messages:\n{all_messages if all_messages else 'No messages found.'}",
        reply_markup=get_main_buttons(),
    )
    logging.debug(f"Sent backup messages to Chat ID {message.chat.id}: {all_messages}")


# def process_birthday_pings():
#     while True:
#         time.sleep(60)
#         try:
#             all_chat_ids = db.get_all_chat_ids()
#             logging.debug(f"Processing backup pings for Chat IDs: {all_chat_ids}")

#             for chat_id in all_chat_ids:
#                 chat_id = chat_id[0]

#                 backup_ping_settings = db.select_from_backup_ping(chat_id)

#                 if backup_ping_settings.is_active is False:
#                     continue

#                 now = int(time.time())
#                 delta_seconds = now - backup_ping_settings.last_updated_timestamp
#                 settings_delta_seconds = backup_ping_settings.update_timedelta * 60

#                 if delta_seconds < settings_delta_seconds:
#                     continue

#                 db.update_backup_ping(chat_id)

#                 all_messages = "\n".join(db.get_all_messages(chat_id))
#                 if all_messages:
#                     bot.send_message(
#                         chat_id,
#                         f"Here's your latest backup:\n{all_messages}",
#                     )
#                     logging.info(f"Sent backup to Chat ID {chat_id}.")
#                 else:
#                     bot.send_message(chat_id, "You have no saved messages.")
#                     logging.info(f"No messages found for Chat ID {chat_id}.")

#         except Exception as e:
#             logging.error(f"Error during backup ping processing: {e}")
#             utils.log_exception(e)


def register_birthday(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        (
            "Please enter the birthday details in the following format:\n"
            "1. First line: Name (and surname)\n"
            "2. Second line: Date of birth (e.g., DD/MM/YYYY)\n\n"
            "Example:\n"
            "John Doe\n"
            "15/05/1990"
        ),
        reply_markup=get_main_buttons(),
    )

    user_states[chat_id] = TUserState.AwaitingNameAndDate
    logging.info(f"Awaiting name input for Chat ID {chat_id}.")


def process_backup_pings():
    while True:
        time.sleep(60)
        try:
            all_chat_ids = db.get_all_chat_ids()
            logging.debug(f"Processing backup pings for Chat IDs: {all_chat_ids}")

            for chat_id in all_chat_ids:
                chat_id = chat_id[0]

                backup_ping_settings = db.select_from_backup_ping(chat_id)

                if backup_ping_settings.is_active is False:
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


def register_backup(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        "Please enter the interval at which to send backup (1 month, 1year, 1год, etc).",
        reply_markup=get_main_buttons(),
    )

    user_states[chat_id] = TUserState.AwaitingInterval
    logging.info(f"Awaiting interval input for Chat ID {chat_id}.")


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
    user_message = message.text.strip()
    logging.info(f"Received message from Chat ID {chat_id}: {user_message}")

    global button_to_command
    if message.text in button_to_command.keys():
        match button_to_command[message.text]:
            case TCommand.Start:
                handle_start(message)
                return
            case TCommand.Backup:
                send_backup(message)
                return
            case TCommand.RegisterBirthday:
                register_birthday(message)
                return
            case TCommand.RegisterBackup:
                register_backup(message)
                return
            case TCommand.UnregisterBackup:
                unregister_backup(message)
                return
            case _:
                raise ValueError("Unknown command")

    match user_states.get(chat_id):
        case TUserState.AwaitingInterval:
            try:
                if not utils.is_timestamp_valid(user_message):
                    raise ValueError("Invalid format")

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

                user_states[chat_id] = None

            except Exception as e:
                logging.error(
                    f"Error processing interval input for Chat ID {chat_id}: {e}"
                )
                bot.send_message(
                    chat_id,
                    "Invalid interval format. Please try again using a format like '1 month'.",
                    reply_markup=get_main_buttons(),
                )
                utils.log_exception(e)
        case TUserState.AwaitingNameAndDate:
            try:
                splitted_message = user_message.split("\n")

                if len(splitted_message) != 2:
                    raise ValueError("Invalid format")

                name = splitted_message[0]
                date = splitted_message[1]

                # if not utils.is_name_valid(name):
                #     raise ValueError("Invalid name format")

                # if not utils.is_date_valid(date):
                #     raise ValueError("Invalid date format")

                # db.register_birthday(chat_id, user_message)

                # bot.send_message(
                #     chat_id,
                #     "Birthday registered!",
                #     reply_markup=get_main_buttons(),
                # )
                # logging.info(f"Registered birthday for Chat ID {chat_id}.")

                bot.send_message(
                    chat_id,
                    f"Name: {name}\nDate: {date}",
                    reply_markup=get_main_buttons(),
                )
                logging.info(f"Sent birthday details to Chat ID {chat_id}.")

                user_states[chat_id] = None

            except Exception as e:
                logging.error(f"Error processing name input for Chat ID {chat_id}: {e}")
                bot.send_message(
                    chat_id,
                    "Invalid name format. Please try again using a format like 'John Doe'.",
                    reply_markup=get_main_buttons(),
                )
                utils.log_exception(e)
        case _:  # TODO change to default?
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

        # logging.info("Starting birthday ping thread...")
        # thread = threading.Thread(target=process_birthday_pings)
        # thread.start()

        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)

    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
        utils.log_exception(e)
