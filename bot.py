import enum
import logging
import os
import threading
import time
from datetime import datetime

import telebot
from dotenv import load_dotenv
from telebot.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup)

import db
import utils

logging.basicConfig(
    level=logging.INFO,
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
    AwaitingBirthday = "awaiting_birthday"


class TCommand(enum.Enum):
    Start = "start"
    Backup = "backup"
    RegisterBirthday = "register_birthday"
    RegisterBackup = "register_backup"
    UnregisterBackup = "unregister_backup"
    DeleteBirthday = "delete_birthday"
    Stats = "stats"
    Share = "share"


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
    #
    "🔗 Share": TCommand.Share,
    "/share": TCommand.Share,
    #
    "📊 Stats": TCommand.Stats,
    "/stats": TCommand.Stats,
}


description_to_command = {
    "🚀 Start": "Start the bot and see available commands.",
    "🎉 Register Birthday": "Register a new birthday. *Lifehack: you don't need to click this button, just send a message in the format: 'Name\nDate of birth'*",
    "❌ Delete Birthday": "Delete a birthday.",
    "💾 Backup": "Get a list of all your birthdays.",
    "🔐 Register Backup": "Register a new backup interval.",
    "🚫 Unregister Backup": "Unregister a backup interval.",
    "🔗 Share": "Share your birthdays with your friends.",
    "📊 Stats": "Get different statistics.",
}


def get_all_birthdays(chat_id: int, need_id: bool = False) -> str:
    return "\n".join(db.get_all_birthdays(chat_id, need_id))


def is_group_chat(message) -> bool:
    return message.chat.type in ["group", "supergroup"]


def get_reply_markup(message) -> ReplyKeyboardMarkup | None:
    markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton("🚀 Start", callback_data="🚀 Start"),
        InlineKeyboardButton("💾 Backup", callback_data="💾 Backup"),
        InlineKeyboardButton(
            "🎉 Register Birthday", callback_data="🎉 Register Birthday"
        ),
        InlineKeyboardButton("🔐 Register Backup", callback_data="🔐 Register Backup"),
        InlineKeyboardButton("❌ Delete Birthday", callback_data="❌ Delete Birthday"),
        InlineKeyboardButton(
            "🚫 Unregister Backup", callback_data="🚫 Unregister Backup"
        ),
        InlineKeyboardButton("🔗 Share", callback_data="🔗 Share"),
        InlineKeyboardButton("📊 Stats", callback_data="📊 Stats"),
    ]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i : (i + 2)])
    return markup


def get_reminder_settings_keyboard(chat_id) -> InlineKeyboardMarkup:
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


def handle_stats(message):
    chat_id = message.chat.id

    total_birthdays_for_this_chat = len(db.get_all_birthdays(chat_id))
    total_birthdays_for_all_chats = len(db.get_all_birthdays_for_all_chats())
    total_users = len(set(chat_id for chat_id, in db.get_all_chat_ids()))

    current_month = datetime.now().month
    birthdays_this_month = []

    for birthday in db.get_all_birthdays(chat_id):
        date_str = birthday.split(", ")[0]
        try:
            date = datetime.strptime(date_str, "%d %B %Y")
        except ValueError:
            date = datetime.strptime(date_str, "%d %B")

        if date.month == current_month:
            birthdays_this_month.append(birthday)

    total_birthdays_this_month = len(birthdays_this_month)

    stats_message = (
        f"📊 *Statistics:*\n\n"
        f"Total Birthdays in this Month: {total_birthdays_this_month}\n"
        f"Total Birthdays in this Chat: {total_birthdays_for_this_chat}\n"
        f"Total Birthdays in all Chats: {total_birthdays_for_all_chats}\n"
        f"Total Users: {total_users}\n"
    )

    bot.send_message(
        chat_id,
        stats_message,
        parse_mode="Markdown",
    )

    user_states[chat_id] = TUserState.Default


def handle_start(message):
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
🎉 *Welcome to Birthday Reminder Bot!* 🎂

Never forget a birthday again! This bot helps you keep track of birthdays and sends you timely reminders.

*What can this bot do?*
• Store birthdays of your friends and family
• Send reminders before upcoming birthdays
• Create regular backups of your birthday list
• Customize when you want to receive reminders

*How to use:*
1. Click "🎉 Register Birthday" to add a new birthday
2. Set up reminder preferences below
3. Optionally, set up automatic backups

*Available Commands:*
{commands_msg}

{backup_ping_msg}
*Contribute to the project:*
[GitHub](https://github.com/Nikfilk2030/birthday_reminder_bot)
""",
        reply_markup=get_reply_markup(message),
        parse_mode="Markdown",
    )
    logging.debug(f"Sent welcome message to Chat ID {message.chat.id}")

    bot.send_message(
        message.chat.id,
        "Configure when you want to receive birthday reminders:\n\n"
        "*Example: '1 days' means you'll receive a reminder 1 day before the birthday.*",
        reply_markup=get_reminder_settings_keyboard(message.chat.id),
        parse_mode="Markdown",
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

    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=get_reminder_settings_keyboard(chat_id),
    )

    bot.answer_callback_query(
        call.id,
        f"{'Enabled' if days in current_settings else 'Disabled'} {days}-day reminders",
    )

    user_states[call.message.chat.id] = TUserState.Default


def get_all_birthdays_formatted(chat_id: int, need_id: bool = False) -> str:
    all_birthdays = get_all_birthdays(chat_id, need_id)

    if not all_birthdays:
        return "You have no saved birthdays."

    birthdays_by_month = {}
    for line in all_birthdays.split("\n"):
        date_str, name, *rest = line.split(", ")
        date = datetime.strptime(
            date_str, "%d %B %Y" if "Current age" in line else "%d %B"
        )
        month = date.strftime("%B")
        if month not in birthdays_by_month:
            birthdays_by_month[month] = []
        birthdays_by_month[month].append(line)

    markdown_message = "*Your Birthdays:*\n\n"
    for month, birthdays in birthdays_by_month.items():
        markdown_message += f"*{month}*\n"
        for birthday in birthdays:
            markdown_message += f"- {birthday}\n"
        markdown_message += "\n"

    user_states[chat_id] = TUserState.Default

    return markdown_message


def get_all_birthdays_for_share(chat_id: int) -> str:
    all_birthdays = get_all_birthdays(chat_id)

    if not all_birthdays:
        return "Nothing found"

    formatted_birthdays = []
    for line in all_birthdays.split("\n"):
        date_str, name, *rest = line.split(", ")
        date = datetime.strptime(
            date_str, "%d %B %Y" if "Current age" in line else "%d %B"
        )
        if date.year != utils.DEFAULT_BD_YEAR:
            formatted_date = date.strftime("%d.%m.%Y")
        else:
            formatted_date = date.strftime("%d.%m")
        formatted_birthdays.append(name)
        formatted_birthdays.append(formatted_date)

    return "\n".join(formatted_birthdays)


def send_backup(message):
    all_birthdays = get_all_birthdays_formatted(message.chat.id)
    birthdays_messages = utils.split_message(all_birthdays)

    for birthday_message in birthdays_messages:
        bot.send_message(
            message.chat.id,
            birthday_message,
            parse_mode="Markdown",
        )

    user_states[message.chat.id] = TUserState.Default


def process_birthday_pings():
    while True:
        minutes = 5
        time.sleep(minutes * 60)

        if not utils.is_daytime():
            continue

        try:
            for days in REMINDED_DAYS:
                upcoming_birthdays = db.get_upcoming_birthdays(days)

                for id, chat_id, name, birthday_str, has_year in upcoming_birthdays:
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
                        age_text = ""
                        if has_year:
                            age = current_year - birthday.year
                            age_text = f" (turns {age})"

                        if days_until == 0:
                            bot.send_message(chat_id, "🎂")
                            reminder_text = (
                                f"📆🎂Today is {name}'s birthday!{age_text} 🎂"
                            )
                        else:
                            reminder_text = (
                                f"📆In {days_until} days {name}'s birthday!{age_text}"
                            )

                        bot.send_message(chat_id, reminder_text)

                        db.mark_birthday_reminder_sent(id, days_until)

        except Exception as e:
            logging.error(f"Error during birthday ping processing: {e}")
            utils.log_exception(e)


def send_share_message(message):
    all_birthdays = get_all_birthdays_for_share(message.chat.id)
    birthdays_messages = utils.split_message(all_birthdays)

    for birthday_message in birthdays_messages:
        bot.send_message(message.chat.id, birthday_message, parse_mode="Markdown")


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
            "- day.month.year  (5.06.2001) - use full 4-digit year\n"
            "- day.month (5.06)\n"
            "- day.month age (5.06 19)\n"
            "\n"
            "*Note:* You can add multiple birthdays by separating them with a new line.\n"
            "*Note:* Dates must must be written in full 4-digit format (e.g., 1994 not 94)\n"
            "\n"
            "*Example:*\n"
            "John Doe\n"
            "15.05.1990\n"
            "Jane Doe\n"
            "10.06.1991\n"
        ),
        parse_mode="Markdown",
    )

    user_states[chat_id] = TUserState.AwaitingBirthday


def process_backup_pings():
    while True:
        minutes = 5
        time.sleep(minutes * 60)
        try:
            all_chat_ids = db.get_all_chat_ids()
            if all_chat_ids is None:
                logging.error("Failed to retrieve chat IDs")
                continue

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

                all_birthdays = get_all_birthdays_formatted(chat_id)
                bot.send_message(
                    chat_id,
                    f"Here's your latest backup:\n{all_birthdays}",
                    parse_mode="Markdown",
                )

        except Exception as e:
            logging.error(f"Error during backup ping processing: {e}")
            utils.log_exception(e)
            time.sleep(60)


def register_backup(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        "Please enter the interval at which to send backup (1 month, 1year, 1год, etc).",
        parse_mode="Markdown",
    )

    user_states[chat_id] = TUserState.AwaitingInterval


def unregister_backup(message):
    chat_id = message.chat.id
    db.unregister_backup_ping(chat_id)
    bot.send_message(
        chat_id,
        "Auto-backup unregistered.",
        parse_mode="Markdown",
    )

    user_states[chat_id] = TUserState.Default


def handle_deletion(message):
    chat_id = message.chat.id
    all_birthdays = get_all_birthdays_formatted(message.chat.id, need_id=True)
    birthdays_messages = utils.split_message(all_birthdays)

    bot.send_message(
        chat_id,
        "Enter the IDs of the birthdays you want to delete, separated by commas",
        parse_mode="Markdown",
    )
    for birthday_message in birthdays_messages:
        bot.send_message(chat_id, birthday_message, parse_mode="Markdown")

    user_states[chat_id] = TUserState.AwaitingDeletion


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data in button_to_command:
        command = button_to_command[call.data]
        message = call.message
        if command == TCommand.Start:
            handle_start(message)
        elif command == TCommand.Backup:
            send_backup(message)
        elif command == TCommand.RegisterBirthday:
            register_birthday(message)
        elif command == TCommand.RegisterBackup:
            register_backup(message)
        elif command == TCommand.UnregisterBackup:
            unregister_backup(message)
        elif command == TCommand.DeleteBirthday:
            handle_deletion(message)
        elif command == TCommand.Stats:
            handle_stats(message)
        elif command == TCommand.Share:
            send_share_message(message)
        else:
            bot.answer_callback_query(call.id, "Unknown command")
    else:
        bot.answer_callback_query(call.id, "Invalid action")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_message = message.text.strip()

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
            case TCommand.Stats:
                handle_stats(message)
                return
            case TCommand.Share:
                send_share_message(message)
                return
            case _:
                raise ValueError("Unknown command")

    match user_states.get(chat_id):
        case TUserState.AwaitingInterval:
            try:
                if not utils.is_timestamp_valid(user_message):
                    raise ValueError(f"Invalid format, user_message: {user_message}")

                interval_in_minutes = utils.get_time(user_message)

                db.register_backup_ping(chat_id, interval_in_minutes)

                bot.send_message(
                    chat_id,
                    f"Auto-backup registered! You'll receive backups every {interval_in_minutes} minute(s).",
                    parse_mode="Markdown",
                )

                user_states[chat_id] = TUserState.Default

            except Exception as e:
                logging.error(
                    f"Error processing interval input for Chat ID {chat_id}: {e}"
                )
                bot.send_message(
                    chat_id,
                    "Invalid interval format. Please try again using a format like '1 month'.",
                    parse_mode="Markdown",
                )
        case TUserState.AwaitingDeletion:
            try:
                birthday_ids = [
                    int(id_str.strip()) for id_str in user_message.split(",")
                ]
                deleted_ids = []
                not_found_ids = []

                for birthday_id in birthday_ids:
                    deleted_rows = db.delete_birthday(chat_id, birthday_id)
                    if deleted_rows > 0:
                        deleted_ids.append(birthday_id)
                    else:
                        not_found_ids.append(birthday_id)

                if deleted_ids:
                    bot.send_message(
                        chat_id,
                        f"Successfully deleted birthdays with IDs: {', '.join(map(str, deleted_ids))}.",
                        parse_mode="Markdown",
                    )

                if not_found_ids:
                    bot.send_message(
                        chat_id,
                        f"Could not find birthdays with IDs: {', '.join(map(str, not_found_ids))}.",
                        parse_mode="Markdown",
                    )
                    logging.warning(
                        f"Could not find birthdays for Chat ID {chat_id}: {not_found_ids}"
                    )

                user_states[chat_id] = TUserState.Default

            except ValueError:
                bot.send_message(
                    chat_id,
                    "Invalid input. Please enter numerical IDs separated by commas.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logging.error(f"Error deleting birthdays for Chat ID {chat_id}: {e}")

        case TUserState.AwaitingBirthday:
            try:
                success, error_message = utils.validate_birthday_input(user_message)
                if not success:
                    bot.send_message(
                        chat_id,
                        error_message,
                        parse_mode="Markdown",
                    )
                    return

                success, parsed_birthdays = utils.parse_dates(user_message)
                for name, parsed_date, has_year in parsed_birthdays:
                    db.register_birthday(chat_id, name, parsed_date, has_year)

                birthday_msg = ""
                for name, parsed_date, has_year in parsed_birthdays:
                    if has_year:
                        birthday_msg += (
                            f"- {name}: {parsed_date.strftime('%d %B %Y')}\n"
                        )
                    else:
                        birthday_msg += f"- {name}: {parsed_date.strftime('%d %B')}\n"

                bot.send_message(
                    chat_id,
                    f"Birthdays registered successfully!\n{birthday_msg}",
                    parse_mode="Markdown",
                )

                user_states[chat_id] = TUserState.Default

            except Exception:
                bot.send_message(
                    chat_id,
                    "Invalid name format. Please try again.",
                    parse_mode="Markdown",
                )
        case _:
            pass


def log_cleaner():
    """Thread function to periodically clean up old log files."""
    while True:
        try:
            utils.cleanup_old_logs()
            time.sleep(24 * 60 * 60)
        except Exception as e:
            logging.error(f"Error in log cleaner thread: {e}")
            utils.log_exception(e)
            time.sleep(60 * 60)


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

        logging.info("Starting log cleaner thread...")
        log_cleaner_thread = threading.Thread(target=log_cleaner, daemon=True)
        log_cleaner_thread.start()

        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)

    except KeyboardInterrupt:
        logging.info("Shutting down bot gracefully...")

        backup_thread.join(timeout=2)
        birthday_thread.join(timeout=2)
        log_cleaner_thread.join(timeout=2)

    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
        utils.log_exception(e)
