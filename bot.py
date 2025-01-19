import enum
import logging
import os
import threading
import time
from datetime import datetime

import telebot
from dotenv import load_dotenv
from telebot.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)

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

REMINDED_DAYS = [0, 1, 3, 7]


class TUserState(enum.Enum):
    Default = "default"
    AwaitingInterval = "awaiting_interval"
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


description_to_command = {
    "🚀 Start": "Start the bot and see available commands.",
    "🎉 Register Birthday": "Register a new birthday.",
    "❌ Delete Birthday": "Delete a birthday.",
    "💾 Backup": "Get a list of all your birthdays.",
    "🔐 Register Backup": "Register a new backup interval.",
    "🚫 Unregister Backup": "Unregister a backup interval.",
}


def get_main_buttons():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    buttons = [
        KeyboardButton("🚀 Start"),
        KeyboardButton("💾 Backup"),
        KeyboardButton("🎉 Register Birthday"),
        KeyboardButton("🔐 Register Backup"),
        KeyboardButton("❌ Delete Birthday"),
        KeyboardButton("🚫 Unregister Backup"),
    ]

    markup.add(*buttons)

    return markup


def get_all_birthdays(chat_id: int) -> str:
    return "\n".join(db.get_all_birthdays(chat_id))


def get_reminder_settings_keyboard(chat_id):
    current_settings = db.get_reminder_settings(chat_id) or []

    markup = InlineKeyboardMarkup()

    reminder_buttons = [
        InlineKeyboardButton(
            f"{'✅' if days in current_settings else '❌'} {days} days",
            callback_data=f"reminder_{days}",
        )
        for days in REMINDED_DAYS
    ]

    markup.row(reminder_buttons[0], reminder_buttons[1])
    markup.row(reminder_buttons[2], reminder_buttons[3])

    return markup


def handle_start(message):
    logging.info(f"Received /start or /help command from Chat ID {message.chat.id}")

    user_states[message.chat.id] = TUserState.Default

    backup_ping_settings = db.select_from_backup_ping(message.chat.id)
    if backup_ping_settings.is_active:
        backup_ping_msg = f"You have an active backup ping every {backup_ping_settings.update_timedelta} minute(s).\n"
    else:
        backup_ping_msg = "You have no active backup ping.\n"

    commands_msg = "\n".join(
        [
            f"{command}: {description}"
            for command, description in description_to_command.items()
        ]
    )

    bot.send_message(
        message.chat.id,
        f"""
Hello! This bot in beta. Use commands to understand what they do.
Also, you can use the buttons below for navigation.

List of commands:
{commands_msg}

Bot can send you backup of all birthdays. You can register it by clicking on the button "🔐 Register Backup".

{backup_ping_msg}
""",
        reply_markup=get_main_buttons(),
    )
    logging.debug(f"Sent welcome message to Chat ID {message.chat.id}")

    bot.send_message(
        message.chat.id,
        "Configure when you want to receive birthday reminders:",
        reply_markup=get_reminder_settings_keyboard(message.chat.id),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("reminder_"))
def handle_reminder_callback(call):
    days = int(call.data.split("_")[1])
    chat_id = call.message.chat.id

    current_settings = db.get_reminder_settings(chat_id) or []

    if days in current_settings:
        current_settings.remove(days)
    else:
        current_settings.append(days)

    db.update_reminder_settings(chat_id, current_settings)

    # Update the message with new keyboard
    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=get_reminder_settings_keyboard(chat_id),
    )

    # Answer the callback to remove loading state
    bot.answer_callback_query(
        call.id,
        f"{'Enabled' if days in current_settings else 'Disabled'} {days}-day reminders",
    )


def send_backup(message):
    logging.info(f"Received /backup command from Chat ID {message.chat.id}")
    all_birthdays = get_all_birthdays(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"Your birthdays:\n{all_birthdays if all_birthdays else 'No birthdays found.'}",
        reply_markup=get_main_buttons(),
    )
    logging.debug(
        f"Sent backup birthdays to Chat ID {message.chat.id}: {all_birthdays}"
    )


def process_birthday_pings():
    while True:
        minutes = 1
        time.sleep(minutes * 60)

        if not utils.is_daytime():
            continue

        try:
            logging.info("Checking for upcoming birthdays...")

            for days in REMINDED_DAYS:
                upcoming_birthdays = db.get_upcoming_birthdays(days)

                for id, chat_id, name, birthday_str in upcoming_birthdays:
                    user_settings = db.get_reminder_settings(chat_id)
                    if not user_settings:
                        continue

                    birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
                    current_year = datetime.now().year
                    birthday_this_year = birthday.replace(year=current_year)

                    today = datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    days_until = (birthday_this_year - today).days

                    # Only send reminder if user has enabled this day.
                    if days_until in user_settings:
                        if days_until == 0:
                            bot.send_message(chat_id, "🎂")
                            reminder_text = f"Today is {name}'s birthday! 🎂"
                        else:
                            reminder_text = (
                                f"{name}'s birthday is in {days_until} days!"
                            )

                        bot.send_message(chat_id, reminder_text)
                        logging.info(
                            f"Sent reminder to Chat ID {chat_id}: {reminder_text}"
                        )

                        db.mark_birthday_reminder_sent(id, days_until)

        except Exception as e:
            logging.error(f"Error during birthday ping processing: {e}")
            utils.log_exception(e)


def register_birthday(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        (
            "*Please enter the birthday details in the following format:*\n"
            "First line: Name (and surname)\n"
            "Second line: Date of birth\n"
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

    user_states[chat_id] = TUserState.Default
    logging.info(f"Awaiting name input for Chat ID {chat_id}.")


def process_backup_pings():
    while True:
        minutes = 1
        time.sleep(minutes * 60)
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

                all_birthdays = get_all_birthdays(chat_id)
                if all_birthdays:
                    bot.send_message(
                        chat_id,
                        f"Here's your latest backup:\n{all_birthdays}",
                    )
                    logging.info(f"Sent backup to Chat ID {chat_id}.")
                else:
                    bot.send_message(chat_id, "You have no saved birthdays.")
                    logging.info(f"No birthdays found for Chat ID {chat_id}.")

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
    user_states[chat_id] = TUserState.AwaitingDeletion
    all_birthdays = get_all_birthdays(message.chat.id)

    bot.send_message(
        chat_id,
        "Enter the ID of the birthday you want to delete:"
        f"\n\n{all_birthdays if all_birthdays else 'No birthdays found.'}",
        reply_markup=get_main_buttons(),
    )


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
                handle_deletion(message)
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
        case TUserState.AwaitingDeletion:
            try:
                birthday_id = int(user_message)
                deleted_rows = db.delete_birthday(chat_id, birthday_id)
                if deleted_rows == 0:
                    raise ValueError("Birthday not found")
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
                    "Invalid ID. Please enter a numerical ID or check the list of birthdays.",
                    reply_markup=get_main_buttons(),
                )
            except Exception as e:
                logging.error(f"Error deleting birthday for Chat ID {chat_id}: {e}")
        case _:  # Awaiting name and date
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
                    "Invalid name format. Please try again.",
                    reply_markup=get_main_buttons(),
                )


if __name__ == "__main__":
    db.init_db()

    logging.info("Bot is running...")
    try:
        logging.info("Starting backup ping thread...")
        backup_thread = threading.Thread(target=process_backup_pings, daemon=True)
        backup_thread.start()

        logging.info("Starting birthday ping thread...")
        birthday_thread = threading.Thread(target=process_birthday_pings, daemon=True)
        birthday_thread.start()

        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)

    except KeyboardInterrupt:
        logging.info("Shutting down bot gracefully...")

        backup_thread.join(timeout=2)
        birthday_thread.join(timeout=2)

    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
        utils.log_exception(e)
