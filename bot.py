import enum
import logging
import os
import threading
import time
from datetime import datetime

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
    AwaitingDeletion = "awaiting_deletion"


class TCommand(enum.Enum):
    Start = "start"
    Backup = "backup"
    RegisterBirthday = "register_birthday"
    RegisterBackup = "register_backup"
    UnregisterBackup = "unregister_backup"
    DeleteBirthday = "delete_birthday"


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
    #
    "❌ Delete Birthday": TCommand.DeleteBirthday,
    "/delete_birthday": TCommand.DeleteBirthday,
}


def get_main_buttons():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    buttons = [
        KeyboardButton("🚀 Start"),
        KeyboardButton("💾 Backup"),
        KeyboardButton("🎉 Register Birthday"),
        KeyboardButton("🔐 Register Backup"),
        KeyboardButton("🚫 Unregister Backup"),
        KeyboardButton("❌ Delete Birthday"),
    ]

    markup.add(*buttons)

    return markup


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
        "Hello! This bot in beta. Use commands to understand what they do.\n\n"
        "Also, you can use the buttons below for navigation.\n\n" + backup_ping_msg,
        reply_markup=get_main_buttons(),
    )
    logging.debug(f"Sent welcome message to Chat ID {message.chat.id}")


def send_backup(message):
    logging.info(f"Received /backup command from Chat ID {message.chat.id}")
    all_birthdays = "\n".join(db.get_all_birthdays(message.chat.id))

    bot.send_message(
        message.chat.id,
        f"Your messages:\n{all_birthdays if all_birthdays else 'No messages found.'}",
        reply_markup=get_main_buttons(),
    )
    logging.debug(f"Sent backup messages to Chat ID {message.chat.id}: {all_birthdays}")


def process_birthday_pings():
    days_notice = [0, 1, 3, 7]  # Customize days for reminders
    while True:
        try:
            time.sleep(60)  # TODO Check every hour

            logging.info("Checking for upcoming birthdays...")

            for days in days_notice:
                upcoming_birthdays = db.get_upcoming_birthdays(days)
                for id, chat_id, name, birthday_str in upcoming_birthdays:
                    birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
                    current_year = datetime.now().year
                    birthday_this_year = birthday.replace(year=current_year)

                    today = datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )

                    if (birthday_this_year - today).days == days:
                        logging.info("got into if")
                        if days == 0:
                            reminder_text = f"Today is {name}'s birthday! 🎂"
                        else:
                            reminder_text = f"{name}'s birthday is in {days} days!"

                        bot.send_message(chat_id, reminder_text)
                        logging.info(
                            f"Sent reminder to Chat ID {chat_id}: {reminder_text}"
                        )

                        db.mark_birthday_reminder_sent(id, days)
        except Exception as e:
            logging.error(f"Error during birthday ping processing: {e}")
            utils.log_exception(e)


def register_birthday(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        (
            "*Please enter the birthday details in the following format:*\n"
            "1. First line: Name (and surname)\n"
            "2. Second line: Date of birth\n"
            "\n"
            "*Possible formats:*\n"
            "- day.month.year  (5.06.2001)\n"
            "- day.month (5.06)\n"
            "- day.month age (5.06 19)\n"
            "\n"
            "*Example:*\n"
            "John Doe\n"
            "15.05.1990"
            "\n\n"
        ),
        parse_mode="Markdown",
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

                all_birthdays = "\n".join(db.get_all_birthdays(chat_id))
                if all_birthdays:
                    bot.send_message(
                        chat_id,
                        f"Here's your latest backup:\n{all_birthdays}",
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


def handle_deletion(message):
    chat_id = message.chat.id
    try:
        birthday_id = int(message.text)
        db.delete_birthday(birthday_id)
        bot.send_message(
            chat_id, "Birthday deleted successfully.", reply_markup=get_main_buttons()
        )
    except ValueError:
        bot.send_message(
            chat_id,
            "Invalid ID. Please enter a numerical ID.",
            reply_markup=get_main_buttons(),
        )
    except Exception as e:
        logging.error(f"Error deleting birthday for Chat ID {chat_id}: {e}")
        bot.send_message(
            chat_id,
            "An error occurred. Please try again.",
            reply_markup=get_main_buttons(),
        )
        utils.log_exception(e)
    finally:
        user_states[chat_id] = TUserState.Default


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
            case TCommand.DeleteBirthday:
                delete_birthday(message)
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

                success, parsed_date = utils.parse_date(date)

                if not success:
                    raise ValueError("Invalid date format")

                db.register_birthday(chat_id, name, parsed_date)

                bot.send_message(
                    chat_id,
                    f"Birthday registered! Name: {name}, Date: {parsed_date}",
                    reply_markup=get_main_buttons(),
                )
                logging.info(f"Registered birthday for Chat ID {chat_id}.")

                user_states[chat_id] = None

            except Exception as e:
                logging.error(f"Error processing name input for Chat ID {chat_id}: {e}")
                bot.send_message(
                    chat_id,
                    "Invalid name format. Please try again using a format like 'John Doe'.",
                    reply_markup=get_main_buttons(),
                )
                utils.log_exception(e)
        case TUserState.AwaitingDeletion:
            try:
                birthday_id = int(user_message)
                db.delete_birthday(birthday_id)
                bot.send_message(
                    chat_id,
                    f"Birthday deleted successfully. ID: {birthday_id}",
                    reply_markup=get_main_buttons(),
                )
                logging.info(f"Deleted birthday for Chat ID {chat_id}.")
                user_states[chat_id] = None
            except ValueError:
                bot.send_message(
                    chat_id,
                    "Invalid ID. Please enter a numerical ID.",
                    reply_markup=get_main_buttons(),
                )
            except Exception as e:
                logging.error(f"Error deleting birthday for Chat ID {chat_id}: {e}")
        case _:
            bot.send_message(
                chat_id,
                "Unknown command. Send /start to see available commands.",
                reply_markup=get_main_buttons(),
            )


if __name__ == "__main__":
    db.init_db()

    logging.info("Bot is running...")
    try:
        logging.info("Starting backup ping thread...")
        thread = threading.Thread(target=process_backup_pings)
        thread.start()

        logging.info("Starting birthday ping thread...")
        thread = threading.Thread(target=process_birthday_pings)
        thread.start()

        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)

    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
        utils.log_exception(e)
